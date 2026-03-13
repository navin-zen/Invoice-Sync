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
from django.utils import timezone
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

    def send_emails(self, errors, notifications):
        email_details = notifications.get("email_details")
        if email_details is None or not errors:
            return
        recipient_list = email_details.get("emails")
        from_email = email_details.get("from_email")
        auth_user = email_details.get("auth_user")
        auth_password = email_details.get("auth_password")
        host = email_details.get("host")
        port = email_details.get("port")
        if_ssl = (email_details.get("if_ssl", "NO")).upper()
        ssl = if_ssl in ["YES", "Y"]
        tsl = not ssl
        try:
            with mail.get_connection(
                fail_silently=True,
                host=host,
                port=port,
                username=auth_user,
                password=auth_password,
                use_tls=tsl,
                use_ssl=ssl,
            ) as connection:
                mail.EmailMessage("Errors while Syncing", str(errors), from_email, recipient_list, connection=connection).send()
        except Exception as ex:
            return ex

    def write_error_file(self, errors):
        if not errors or not settings.INVOICING_ERROR_PATH or not self.filename:
            return
        filename = os.path.splitext(os.path.basename(self.filename))[0] + "-errors.txt"
        target_path = os.path.join(settings.INVOICING_ERROR_PATH, filename)
        with open(target_path, "w") as f:
            for e in errors:
                print(e, file=f)


