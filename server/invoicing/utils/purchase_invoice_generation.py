"""
Utilities for generating Purchase Invoice data from the database
"""

import contextlib
import copy
import hashlib
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
from pygstn.utils.marshall import sha256
from pygstn.utils.utils import to_bytes

from invoicing.utils.datamapper.purchase_fields_spec import base36encode

from cz_utils.dateparse import parse_date
from django.utils.timezone import now as timezone_now
from gstnapi.utils.task_utils import scheduled_task
from invoicing.utils.exception_utils import ErrorGrouper
from cz_utils.itertools_utils import unflatten_dict
from cz_utils.decimal_utils import cz_round2
from invoicing.models import CachedData, Configuration, PurchaseInvoice
from invoicing.utils.api.common import typecast_and_get_state
from invoicing.utils.datamapper.purchase_fields_spec import PURCHASE_SCHEMA_SPEC
from invoicing.utils.datasource.databases import (
    create_engine,
    create_engine_for_microsoft_dynamics,
    database_connection_kwargs,
    get_excel_filepath_for_glob,
    microsoft_dynamics_connection_kwargs,
)
from invoicing.utils.settings import SettingsInfo
from invoicing.utils.sqlalchemy_invoice_generation import (
    COLUMN_MAPPING_DEFAULTS,
    FIELD_TO_HUMAN_NAME_MAPPING,
    USER_TRANSFORMS,
    FetchInvoices,
    get_data_from_db,
    get_data_from_excel,
    get_data_from_csv,
    rewrite_complex_objects,
    cleanup_attr_list_sections,
    remove_empty_sections,
    remove_incomplete_sections,
    remove_empty_optional_fields,
    convert2integer,
    to_decimal_round2,
    qty_to_decimal_round3,
    parse_half_tax_rate,
    identity,
    blank_errors,
    ErrorWithInvoiceDetails,
    REQUIRED,
    NO_DEFAULT,
)
from invoicing.utils.utils import ALLOWED_TAX_RATES, fy_range, parse_tax_rate
from taxmaster.models import State

logger = logging.getLogger(__name__)


def clean_purchase_inv_number(s):
    if s is None:
        return ""
    s = str(s).upper().strip()
    if "OF" in s:
        s = s.split("OF")[0].strip()
    return s[:16].strip()

# Re-define specs for Purchase
PURCHASE_GROUPING_TRANS_SPEC = [
    ("BuyerDtls.Gstin", identity, REQUIRED),
    ("SellerDtls.Gstin", identity, REQUIRED),
    ("DocDtls.No", clean_purchase_inv_number, REQUIRED),
    ("DocDtls.Dt", parse_date, REQUIRED),
    ("DocDtls.Typ", identity, NO_DEFAULT),
]

PURCHASE_INVOICE_LEVEL_TRANS_SPEC = [
    ("DocDtls.Typ", identity, NO_DEFAULT),
    ("DocDtls.Dt", parse_date, REQUIRED),
    ("DocDtls.No", clean_purchase_inv_number, REQUIRED),
    ("TranDtls.SupTyp", identity, NO_DEFAULT),
    ("TranDtls.RegRev", identity, NO_DEFAULT),
    ("TranDtls.IgstOnIntra", identity, NO_DEFAULT),
    ("BuyerDtls.Gstin", identity, REQUIRED),
    ("BuyerDtls.LglNm", identity, NO_DEFAULT),
    ("BuyerDtls.Addr1", identity, NO_DEFAULT),
    ("BuyerDtls.Loc", identity, NO_DEFAULT),
    ("BuyerDtls.Pin", convert2integer, NO_DEFAULT),
    ("SellerDtls.Gstin", identity, REQUIRED),
    ("SellerDtls.LglNm", identity, NO_DEFAULT),
    ("SellerDtls.TrdNm", identity, NO_DEFAULT),
    ("SellerDtls.Addr1", identity, NO_DEFAULT),
    ("SellerDtls.Addr2", identity, NO_DEFAULT),
    ("SellerDtls.Loc", identity, NO_DEFAULT),
    ("SellerDtls.Pin", convert2integer, NO_DEFAULT),
    ("BuyerDtls.Pos", typecast_and_get_state, NO_DEFAULT),
    ("Department", identity, NO_DEFAULT),
    ("RecordDate", parse_date, NO_DEFAULT),
    ("DocIdentifier", identity, NO_DEFAULT),
    ("GlAccountId", identity, NO_DEFAULT),
    ("RefDtls.InvRm", identity, NO_DEFAULT),
]

PURCHASE_LINEITEM_LEVEL_TRANS_SPEC = [
    ("LineItem.HsnCd", identity, REQUIRED),
    ("LineItem.PrdDesc", identity, REQUIRED),
    ("LineItem.Qty", qty_to_decimal_round3, NO_DEFAULT),
    ("LineItem.Unit", identity, NO_DEFAULT),
    ("LineItem.UnitPrice", to_decimal_round2, NO_DEFAULT),
    ("LineItem.TotAmt", to_decimal_round2, NO_DEFAULT),
    ("LineItem.AssAmt", to_decimal_round2, REQUIRED),
    ("LineItem.GstRt", parse_tax_rate, REQUIRED),
    ("LineItem.IgstAmt", to_decimal_round2, NO_DEFAULT),
    ("LineItem.CgstAmt", to_decimal_round2, NO_DEFAULT),
    ("LineItem.SgstAmt", to_decimal_round2, NO_DEFAULT),
    ("LineItem.CesAmt", to_decimal_round2, NO_DEFAULT),
    ("LineItem.CesNonAdvlAmt", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.AssVal", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.IgstVal", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.CgstVal", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.SgstVal", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.CesVal", to_decimal_round2, NO_DEFAULT),
    ("ValDtls.TotInvVal", to_decimal_round2, NO_DEFAULT),
    ("WriteBackInfo.TableName", identity, NO_DEFAULT),
    ("WriteBackInfo.Fields.Timestamp", identity, NO_DEFAULT),
    ("WriteBackInfo.Fields.SyncStatus", identity, NO_DEFAULT),
    ("WriteBackInfo.Fields.SyncMessage", identity, NO_DEFAULT),
] + [
    (f"WriteBackInfo.Fk.{i}.Field", identity, NO_DEFAULT) for i in range(5)
] + [
    (f"WriteBackInfo.Fk.{i}.Type", identity, NO_DEFAULT) for i in range(5)
] + [
    (f"WriteBackInfo.Fk.{i}.Value", identity, NO_DEFAULT) for i in range(5)
]


class FetchPurchaseInvoices(FetchInvoices):
    """
    Utility class to fetch Purchase Invoices from datasource
    """

    def do_all(self):
        with ErrorGrouper(raise_errors=False) as eg:
            with eg.wrapper():
                rows = self.get_lineitem_rows(eg)
                logger.info(f"Fetched {len(rows)} raw rows from datasource for {self.configuration}")
                purchase_invoices = self.validate_items_and_group_purchase_invoices(
                    rows, eg, columnmapping=self.datamapping.get("details", {})
                )
                logger.info(f"Grouped {len(purchase_invoices)} purchase invoices for {self.configuration}")
                # Unpack and rewrite
                purchase_invoices = list(
                    zip(
                        [error_message for (error_message, pj) in purchase_invoices],
                        rewrite_complex_objects([pj for (error_message, pj) in purchase_invoices]),
                    )
                )
                if not eg.errors or self.ALLOW_PARTIAL_SAVE:
                    logger.info(f"Saving {len(purchase_invoices)} purchase invoices to local DB")
                    self.save_purchase_invoices_in_our_db(purchase_invoices, self.configuration, self.session.uuid, eg)
        # Handle emails and errors
        errors = [str(e) for e in eg.errors]

        if errors:
            # Include details for the first 10 invoice errors
            detailed_errors = []
            error_count = 0
            for msg, pj in purchase_invoices:
                if msg:
                    doc_no = pj.get('DocDtls', {}).get('No', 'Unknown')
                    detailed_errors.append(f"Invoice {doc_no}: {msg}")
                    error_count += 1
                if error_count >= 10:
                    break
            
            # Combine general errors with detailed invoice errors
            all_errors_to_send = errors + detailed_errors
            
            # Fetch invoices for this session to include in the Excel attachment
            invoices_to_attach = PurchaseInvoice.objects2.filter(
                configuration=self.configuration, 
                upload_uuid=self.session.uuid
            ).order_by("-date")
            
            self.send_emails(
                all_errors_to_send, 
                self.notification, 
                success=False, 
                subject="while fetch the errors are below",
                invoices=invoices_to_attach,
                file_prefix="fetch_error"
            )
        with contextlib.suppress(Exception):
            self.write_error_file([str(e) for e in eg.errors])
        if not eg.errors or self.ALLOW_PARTIAL_SAVE:
            self.move_file()
        return [str(e) for e in eg.errors]

    def get_lineitem_rows(self, eg):
        rows = self.get_unvalidated_lineitems()
        rows_with_key = []
        for r in rows:
            with eg.wrapper():
                rows_with_key.append(self.add_purchase_grouping_key(r))
        return rows_with_key

    @classmethod
    def add_purchase_grouping_key(cls, r):
        """
        Add a unique key to group line items of a purchase invoice.
        We group by Supplier GSTIN, Portal GSTIN, Doc No, Doc Date, and Doc Type.
        """
        r = cls.run_transformations(r, PURCHASE_GROUPING_TRANS_SPEC)
        fy = fy_range(r["DocDtls.Dt"])[0]
        r["Zen.fy"] = fy
        # Grouping key
        key_str = "".join([
            r["BuyerDtls.Gstin"],
            r["SellerDtls.Gstin"],
            r.get("DocDtls.Typ", "INV"),
            r["DocDtls.No"],
            fy.isoformat()
        ])
        r["Zen.PurchaseKey"] = hashlib.sha256(to_bytes(key_str)).hexdigest()
        return r

    @classmethod
    def validate_items_and_group_purchase_invoices(cls, rows, eg, *, columnmapping=None):
        combined_column_mapping = {**COLUMN_MAPPING_DEFAULTS, **(columnmapping or {})}
        rows = sorted(rows, key=operator.itemgetter("Zen.PurchaseKey"))
        invoice_groups = [list(group) for (_, group) in itertools.groupby(rows, operator.itemgetter("Zen.PurchaseKey"))]

        purchase_invoices = []
        for group in invoice_groups:
            with eg.wrapper():
                # Invoice-level transformations
                cls.run_transformations(group[0], PURCHASE_INVOICE_LEVEL_TRANS_SPEC, columnmapping=combined_column_mapping)
                transformed_lineitems = []
                with ErrorGrouper() as eg1:
                    for lineitem in group:
                        with eg1.wrapper():
                            transformed_lineitems.append(
                                cls.run_transformations(lineitem, PURCHASE_LINEITEM_LEVEL_TRANS_SPEC, columnmapping=combined_column_mapping)
                            )

                nested_group = [unflatten_dict(r) for r in transformed_lineitems]
                pj = nested_group[0]
                pj["ItemList"] = [i["LineItem"] for i in nested_group]
                if "ValDtls" not in pj:
                    pj["ValDtls"] = {}

                # Fill in missing fields or recalculate if needed
                vd = pj["ValDtls"]
                if "AssVal" not in vd or not vd["AssVal"]:
                    vd["AssVal"] = sum(item.get("AssAmt", 0) for item in pj["ItemList"])
                if "IgstVal" not in vd or not vd["IgstVal"]:
                    vd["IgstVal"] = sum(item.get("IgstAmt", 0) for item in pj["ItemList"])
                if "CgstVal" not in vd or not vd["CgstVal"]:
                    vd["CgstVal"] = sum(item.get("CgstAmt", 0) for item in pj["ItemList"])
                if "SgstVal" not in vd or not vd["SgstVal"]:
                    vd["SgstVal"] = sum(item.get("SgstAmt", 0) for item in pj["ItemList"])
                if "CesVal" not in vd or not vd["CesVal"]:
                    vd["CesVal"] = sum(item.get("CesAmt", 0) + item.get("CesNonAdvlAmt", 0) for item in pj["ItemList"])

                if "TotInvVal" not in vd or not vd["TotInvVal"]:
                    vd["TotInvVal"] = (
                        vd.get("AssVal", 0) +
                        vd.get("IgstVal", 0) +
                        vd.get("CgstVal", 0) +
                        vd.get("SgstVal", 0) +
                        vd.get("CesVal", 0) +
                        vd.get("StCesVal", 0) +
                        vd.get("OthChrg", 0) +
                        vd.get("RndOffAmt", 0) -
                        vd.get("Discount", 0)
                    )

                # Clean up nested structure
                del pj["LineItem"]
                del pj["Zen"]

                # Add SlNo to ItemList
                for idx, item in enumerate(pj["ItemList"], start=1):
                    item["SlNo"] = str(idx)

                purchase_invoices.append(("", pj))

            if eg.current_errors:
                error_message = "; ".join(str(e) for e in eg.current_errors)
                purchase_invoices.append((error_message, unflatten_dict(group[0])))

        return purchase_invoices

    @classmethod
    def save_purchase_invoices_in_our_db(cls, purchase_invoices, configuration, session_uuid, eg):
        from invoicing.models import GstIn, PurchaseInvoice
        from invoicing.utils.purchase_our_db import add_purchase_invoice
        
        # 1. Pre-fetch all GstIn objects once
        gstin_strings = {pj.get("BuyerDtls", {}).get("Gstin") for (_, pj) in purchase_invoices if pj.get("BuyerDtls", {}).get("Gstin")}
        gstin_cache = {g.gstin: g for g in GstIn.objects2.filter(gstin__in=gstin_strings)}
        
        to_create = []
        to_update = []
        processed_objects = []
        
        # 2. Prepare objects without saving
        for error_message, pj in purchase_invoices:
            with eg.wrapper():
                gstin_string = pj.get("BuyerDtls", {}).get("Gstin")
                gstin_obj = gstin_cache.get(gstin_string)
                
                # add_purchase_invoice with commit=False will return an unsaved instance
                el = add_purchase_invoice(error_message, pj, session_uuid, configuration, gstin_obj=gstin_obj, commit=False)
                if el:
                    processed_objects.append(el)
        
        # 3. Bulk Save
        # Since we use UUIDs and have a unique_together constraint, we can use bulk_create with update_conflicts
        # or separate existing ones. For maximum safety across different DB backends, 
        # let's split into Create vs Update.
        
        for obj in processed_objects:
            if obj._state.adding:
                to_create.append(obj)
            else:
                obj.modify_date = timezone.now()
                to_update.append(obj)
        
        if to_create:
            # batch_size=500 is a safe default
            PurchaseInvoice.objects2.bulk_create(to_create, batch_size=500, ignore_conflicts=True)
            logger.info(f"Bulk created {len(to_create)} purchase invoices")
            
        if to_update:
            # bulk_update requires specifying update_fields
            # Note: modify_date must be explicitly included as bulk_update skips auto_now=True
            update_fields = [
                "docsubtype", "date", "ctin", "purchase_status", 
                "purchase_json", "purchase_response", "metadata", 
                "configuration", "upload_uuid", "modify_date"
            ]
            PurchaseInvoice.objects2.bulk_update(to_update, fields=update_fields, batch_size=500)
            logger.info(f"Bulk updated {len(to_update)} purchase invoices")


class FetchPurchaseInvoicesFromMicrosoftSqlServer(FetchPurchaseInvoices):
    def get_unvalidated_lineitems(self):
        kwargs = database_connection_kwargs(self.datasource)
        engine = create_engine(**kwargs)

        # Initialize Oracle EBS session context (SQLAP) for Multi-Org views
        if "oracle" in str(engine.url.drivername).lower():
            try:
                engine.execute("BEGIN apps.mo_global.init('SQLAP'); END;")
                logger.info(f"Initialized Oracle EBS context for {self.configuration}")
            except Exception as e:
                logger.warning(f"Failed to initialize Oracle EBS context for {self.configuration}: {e}")

        rows = [
            dict(row)
            for row in get_data_from_db(
                engine,
                table_name=self.datamapping.get("table_name") or self.datamapping.get("table"),
                columnmapping=self.datamapping.get("details", {}),
            )
        ]
        db_type = "Oracle" if "oracle" in str(engine.url.drivername).lower() else "SQL Server"
        logger.info(f"Retrieved {len(rows)} raw rows from {db_type} for {self.configuration}")
        return rows


class FetchPurchaseInvoicesFromExcel(FetchPurchaseInvoices):
    ALLOW_PARTIAL_SAVE = False
    FILE_EXTENSION = ".xlsx"

    def complete_init(self):
        config = self.datasource.get("config", {})
        path_pattern = config.get("path")
        try:
            self.filename = get_excel_filepath_for_glob(path_pattern)
            logger.info(f"FetchPurchaseInvoicesFromExcel: Initialized with filename: {self.filename}")
        except Exception as e:
            logger.warning(f"FetchPurchaseInvoicesFromExcel: Failed to find file for pattern {path_pattern}: {e}")

    def get_unvalidated_lineitems(self):
        rows = [
            dict(row)
            for row in get_data_from_excel(columnmapping=self.datamapping.get("details", {}), path=self.filename)
        ]
        logger.info(f"Retrieved {len(rows)} raw rows from Excel file {self.filename} for {self.configuration}")
        return rows


class FetchPurchaseInvoicesFromCsv(FetchPurchaseInvoicesFromExcel):
    FILE_EXTENSION = ".csv"

    def get_unvalidated_lineitems(self):
        return [
            dict(row)
            for row in get_data_from_csv(columnmapping=self.datamapping.get("details", {}), path=self.filename)
        ]


@scheduled_task
def fetch_purchase_invoices_for_session(session_uuid, is_autorun=False, only_config=None):
    from invoicing.utils.purchase_gstzen_cloud import post_all_purchases_to_gstzen
    session = CachedData.objects2.get(uuid=session_uuid)
    all_errors = []
    try:
        CachedData.add_cached_data(
            datatype=CachedData.DT_PURCHASE_SUMMARY,
            data_json={"message": "Connecting with DB"},
            group=session,
        )
        configs = Configuration.objects2.all()
        if not configs.exists():
            all_errors.append("No Configuration is set. Please go to Settings and add a Configuration.")
            return

        for config in configs:
            if only_config and (config != only_config):
                continue
            if is_autorun and not config.enable_autosync:
                logger.info(f"Skipping configuration '{config.site_name}' because autosync is disabled")
                continue

            si = SettingsInfo(config)
            if not si.datasource_settings or not si.datasource_settings.get("config"):
                error_msg = f"Configuration '{config.site_name}' is skipped because datasource is not configured"
                logger.error(error_msg)
                all_errors.append(error_msg)
                continue

            ds_type = si.datasource_settings.get("type")
            # For database sources, we must have a table name configured in datamapping
            if ds_type and not ds_type.startswith("file:") and not si.datamapping_settings.get("table"):
                error_msg = f"Configuration '{config.site_name}' is skipped because datamapping (table name) is not configured"
                logger.info(error_msg)
                all_errors.append(error_msg)
                continue

            logger.info(f"Processing Purchase Sync for configuration '{config.site_name}'")
            # Use appropriate Fetcher based on datasource type
            if ds_type == "file:excel":
                fi_cls = FetchPurchaseInvoicesFromExcel
            elif ds_type == "file:csv":
                fi_cls = FetchPurchaseInvoicesFromCsv
            else:
                fi_cls = FetchPurchaseInvoicesFromMicrosoftSqlServer

            CachedData.add_cached_data(
                datatype=CachedData.DT_PURCHASE_SUMMARY,
                data_json={"message": "Fetching from the DB"},
                group=session,
            )
            errors = fi_cls(
                configuration=config,
                session=session,
                datasource=si.datasource_settings,
                datamapping=si.datamapping_settings,
                notification=si.notification_settings,
            ).do_all()
            all_errors.extend(errors)

        if all_errors:
            distinct_errors = list(dict.fromkeys(all_errors))
            logger.error(f"Errors occurred during purchase sync: {distinct_errors}")
            CachedData.add_cached_data(datatype=CachedData.DT_PURCHASE_ERRORS, data_json=distinct_errors, group=session)

        CachedData.add_cached_data(
            datatype=CachedData.DT_PURCHASE_SUMMARY,
            data_json={"message": "Syncing to CloudZen"},
            group=session,
        )
        # Always trigger cloud sync if we are in this background flow
        post_all_purchases_to_gstzen(session=session)
    finally:
        # Add a finish marker so the UI knows we are done
        CachedData.add_cached_data(
            datatype=CachedData.DT_PURCHASE_FINISH,
            data_json={"status": "finished", "message": "Sync Completed"},
            group=session
        )

    return all_errors


