import abc
import contextlib
import copy
import datetime
import itertools
import logging
import operator
import os
import shutil
from decimal import Decimal

import sqlalchemy
from django.conf import settings
from django.core import mail
from django.template.loader import render_to_string
from invoicing.models import CachedData, Configuration
from invoicing.utils.api.common import typecast_and_get_state
from invoicing.utils.datamapper.purchase_fields_spec import (
    COLUMN_MAPPING_DEFAULTS,
    FIELD_TO_HUMAN_NAME_MAPPING,
    NUM_FK_FIELDS,
    NUM_INVOICE_ATTRIBUTES,
    NUM_ITEM_ATTRIBUTES,
    base36encode,
)
from invoicing.utils.datasource.databases import (
    create_engine,
    create_engine_for_microsoft_dynamics,
    database_connection_kwargs,
    get_excel_filepath_for_glob,
    microsoft_dynamics_connection_kwargs,
)
from invoicing.utils.exception_utils import ErrorGrouper, ErrorWithInvoiceDetails
from invoicing.utils.settings import SettingsInfo
from invoicing.utils.utils import fy_range, parse_half_tax_rate, parse_tax_rate, to_decimal_round2
from invoicing.utils.validate_fields import (
    USER_TRANSFORMS,
    blank_errors,
    convert2integer,
    qty_to_decimal_round3,
    validate_date,
    validate_invoicing_gstin,
    validate_invoicing_optional_gstin,
    validate_invoicing_optional_transin,
    validate_emailid,
    validate_hsncode,
    validate_invnumber,
    validate_invnumber_autocorrect,
    validate_invtype,
    validate_optional_date,
    validate_phno,
    validate_pincode,
    validate_revchrg_and_isexp,
    validate_str,
    validate_transaction_type,
    validate_transport_mode,
    validate_unit,
)
from sqlalchemy import literal
from utils.importer import CustomCsv, CustomXls

from cz_utils.dateparse import parse_date
from cz_utils.decimal_utils import cz_round2
from cz_utils.exceptions import ValueErrorWithCode
from cz_utils.itertools_utils import unflatten_dict

logger = logging.getLogger(__name__)


def identity(x):
    return x


NO_DEFAULT = object()
"""
Indicate that we should not set the field to a default if the data provided
by the user does not contain a field.
"""


REQUIRED = object()
"""
Indicates that we expect this field to be present in the column mapping and
input data. This is another layer of check.
"""


IRN_TRANS_SPEC = [
    ("SellerDtls.Gstin", validate_invoicing_gstin, REQUIRED),
    ("DocDtls.Typ", validate_invtype, REQUIRED),
    ("DocDtls.No", validate_invnumber, REQUIRED),
    ("DocDtls.Dt", validate_date, REQUIRED),
]


def rewrite_complex_objects(ej):
    """
    Rewrite complex objects in the JSON
    """
    if isinstance(ej, datetime.date):
        return ej.strftime("%d/%m/%Y")
    elif isinstance(ej, list):
        return [rewrite_complex_objects(i) for i in ej]
    elif isinstance(ej, dict):
        return {k: rewrite_complex_objects(v) for (k, v) in ej.items()}
    else:
        return ej


def get_select_arg_for_field_config(table, fieldname, fieldconfig):
    if fieldconfig.get("type") == "column":
        column_name = fieldconfig.get("column")
        if column_name:
            return table.c[column_name].label(fieldname)
    elif fieldconfig.get("type") == "constant":
        return literal(fieldconfig.get("value") or "").label(fieldname)
    return None


def get_data_from_db(engine, table_name, columnmapping):
    if not table_name:
        raise ValueError("Database table name not provided")
    combined_column_mapping = {**COLUMN_MAPPING_DEFAULTS, **columnmapping}
    metadata = sqlalchemy.MetaData(bind=engine)
    table = sqlalchemy.Table(table_name, metadata, autoload=True, autoload_with=engine)
    select_args = [
        get_select_arg_for_field_config(table, fieldname, fieldconfig)
        for (fieldname, fieldconfig) in combined_column_mapping.items()
    ]
    query = sqlalchemy.select([a for a in select_args if (a is not None)])
    return engine.execute(query)


def get_column_value(row, fieldname, fieldconfig):
    if fieldconfig.get("type") == "column":
        column_name = fieldconfig.get("column")
        if column_name and (column_name in row):
            return {fieldname: row[column_name]}
    elif fieldconfig.get("type") == "constant":
        if "value" in fieldconfig:
            return {fieldname: fieldconfig["value"]}
    return {}


def get_data_from_excel(columnmapping, path):
    combined_column_mapping = {**COLUMN_MAPPING_DEFAULTS, **columnmapping}
    with open(path, "rb") as in_stream:
        dset = CustomXls.create_dataset(in_stream)[0]
        invoice_list = []
        for row in dset.dict:
            data = {}
            for fieldname, fieldconfig in combined_column_mapping.items():
                data.update(get_column_value(row, fieldname, fieldconfig))
            invoice_list.append(data)
        return invoice_list


def get_data_from_csv(columnmapping, path):
    combined_column_mapping = {**COLUMN_MAPPING_DEFAULTS, **columnmapping}
    with open(path) as in_stream:
        dset = CustomCsv.create_dataset(in_stream)
        invoice_list = []
        for row in dset.dict:
            data = {}
            for fieldname, fieldconfig in combined_column_mapping.items():
                data.update(get_column_value(row, fieldname, fieldconfig))
            invoice_list.append(data)
        return invoice_list


def remove_empty_sections(invoicing, section):
    if section not in invoicing:
        return invoicing
    if all(((v is None) or (v == "")) for v in invoicing[section].values()):
        del invoicing[section]
    return invoicing


def remove_incomplete_sections(invoicing, section, fields):
    if section not in invoicing:
        return invoicing
    section_dict = invoicing[section]
    if any(((f not in section_dict) or (section_dict[f] is None) or (section_dict[f] == "")) for f in fields):
        del invoicing[section]
    return invoicing


def remove_empty_optional_fields(d, f):
    if (f in d) and not d[f]:
        del d[f]


def cleanup_attr_list_sections(d, section_name, itemcount, fields=None):
    if section_name not in d:
        return
    attr_list_section = {}
    for i in range(itemcount):
        idx = base36encode(i)
        remove_empty_sections(d[section_name], idx)
        if fields:
            remove_incomplete_sections(d[section_name], idx, fields)
        if idx in d[section_name]:
            attr_list_section[idx] = d[section_name][idx]
    values = [v for (k, v) in sorted(attr_list_section.items())]
    if values:
        d[section_name] = values
    else:
        del d[section_name]


class FetchInvoices(metaclass=abc.ABCMeta):
    ALLOW_PARTIAL_SAVE = True

    def __init__(self, configuration, session, datasource, datamapping, notification):
        assert isinstance(configuration, Configuration)
        assert isinstance(session, CachedData)
        self.configuration = configuration
        self.session = session
        self.datamapping = datamapping
        self.datasource = datasource
        self.notification = notification
        self.filename = None
        self.complete_init()

    def complete_init(self):
        pass

    @abc.abstractmethod
    def do_all(self):
        pass

    def move_file(self):
        pass

    @abc.abstractmethod
    def get_unvalidated_lineitems(self):
        pass

    @classmethod
    def transform_column(cls, row, fieldname, transFn, userTransFn, default_info):
        try:
            if fieldname not in row:
                if default_info is REQUIRED:
                    raise ValueError("Required column is missing in data")
                elif default_info is NO_DEFAULT:
                    return
                else:
                    value = default_info
            else:
                value = row[fieldname]
            if userTransFn is blank_errors:
                try:
                    transformedValue = transFn(value)
                except Exception:
                    transformedValue = None
            else:
                transformedValue = transFn(value)
            if userTransFn:
                transformedValue = userTransFn(transformedValue)
        except Exception as ex:
            humanFieldName = FIELD_TO_HUMAN_NAME_MAPPING.get(fieldname) or ""
            raise ErrorWithInvoiceDetails(
                ex, invoice=(row.get("DocDtls.No") or None), field=(humanFieldName or fieldname)
            )
        row[fieldname] = transformedValue

    @classmethod
    def run_transformations(cls, r, trans_spec, *, columnmapping=None):
        columnmapping = columnmapping or {}
        with ErrorGrouper() as eg:
            for field, fn, default_info in trans_spec:
                with eg.wrapper():
                    userTransFn = USER_TRANSFORMS.get((columnmapping.get(field) or {}).get("transformation"))
                    cls.transform_column(r, field, fn, userTransFn, default_info)
        return r

    def send_emails(self, errors, notifications, success=False, successes=None, subject=None, invoices=None, file_prefix="report"):
        email_details = notifications.get("email_details")
        if email_details is None:
            return
        
        # If success email requested but no success happened (not applicable usually as we call it explicitly)
        # or if error email requested but no errors
        if not success and not errors:
            return

        recipient_list = email_details.get("emails")
        from_email = email_details.get("from_email")
        auth_user = email_details.get("auth_user")
        auth_password = email_details.get("auth_password")
        host = email_details.get("host")
        port = email_details.get("port")
        if_ssl = (email_details.get("if_ssl", "NO")).upper()
        ssl = if_ssl in ["SSL", "YES", "Y"]
        tls = if_ssl in ["TLS", "STARTTLS"]
        
        # If it was "NO", both remain False. If it was "YES/SSL", ssl is True. If "TLS", tls is True.
        # This prevents forcing TLS when if_ssl is "NO".

        if success:
            subject = subject or "Sync Successful"
            template = "invoicing/emails/sync_success.html"
            context = {"configuration": self.configuration, "successes": successes or []}
        else:
            subject = subject or "Errors while Syncing"
            template = "invoicing/emails/sync_error.html"
            context = {"configuration": self.configuration, "errors": errors}

        html_content = render_to_string(template, context)

        try:
            with mail.get_connection(
                fail_silently=False,
                host=host,
                port=port,
                username=auth_user,
                password=auth_password,
                use_tls=tls,
                use_ssl=ssl,
            ) as connection:
                msg = mail.EmailMessage(
                    subject,
                    html_content,
                    from_email,
                    recipient_list,
                    connection=connection
                )
                msg.content_subtype = "html"
                
                # Attach file if it exists or generate one if invoices are provided
                if self.filename and os.path.exists(self.filename):
                    logger.info(f"Attaching file: {self.filename}")
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(self.filename)
                    if content_type is None:
                        content_type = 'application/octet-stream'
                    
                    file_content = open(self.filename, 'rb').read()
                    logger.info(f"Attachment size: {len(file_content)} bytes")
                    msg.attach(os.path.basename(self.filename), file_content, content_type)
                elif invoices:
                    # Generate Excel on the fly
                    from io import BytesIO
                    from invoicing.views.invoicing import InvoiceExportGenerator
                    output = BytesIO()
                    generator = InvoiceExportGenerator(invoices)
                    generator.write(output)
                    output.seek(0)
                    
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    file_name = f"{file_prefix}_{self.configuration.site_name}_{timestamp}.xlsx"
                    xlsx_data = output.read()
                    msg.attach(file_name, xlsx_data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    
                    try:
                        reports_dir = os.path.join(settings.BASE_DIR, "reports")
                        if not os.path.exists(reports_dir):
                            os.makedirs(reports_dir, exist_ok=True)
                        
                        local_path = os.path.join(reports_dir, file_name)
                        with open(local_path, "wb") as f:
                            f.write(xlsx_data)
                        logger.info(f"Saved local copy of report to: {local_path}")
                    except Exception as e:
                        logger.error(f"Failed to save local copy of report: {e}")

                    logger.info(f"Generated and attached Excel report: {file_name}")
                else:
                    logger.info("No filename provided and no invoices to generate report from")
                
                msg.send()
        except Exception as ex:
            logger.exception("Failed to send email")
            return ex

    def write_error_file(self, errors):
        if not errors or not settings.INVOICING_ERROR_PATH or not self.filename:
            return
        filename = os.path.splitext(os.path.basename(self.filename))[0] + "-errors.txt"
        target_path = os.path.join(settings.INVOICING_ERROR_PATH, filename)
        with open(target_path, "w") as f:
            for e in errors:
                print(e, file=f)


