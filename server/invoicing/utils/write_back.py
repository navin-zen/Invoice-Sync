"""
Utility to write sync status details back to the customer's database
"""

import abc
import datetime
import logging

import sqlalchemy
from invoicing.models import Configuration, PurchaseInvoice
from invoicing.utils.datasource.databases import create_engine, database_connection_kwargs
from invoicing.utils.settings import SettingsInfo

from cz_utils.dateparse import parse_date

logger = logging.getLogger(__name__)


class WriteBack(metaclass=abc.ABCMeta):
    def __init__(self, configuration):
        assert isinstance(configuration, Configuration)
        self.configuration = configuration

    @abc.abstractmethod
    def do_all(self, purchase_invoice):
        pass

    @classmethod
    def lookup_config_and_do_all(cls, purchase_invoice):
        assert isinstance(purchase_invoice, PurchaseInvoice)
        if not purchase_invoice.configuration:
            logger.info(f"Configuration not found for Purchase Invoice {purchase_invoice} {purchase_invoice.uuid}")
            return
        si = SettingsInfo(purchase_invoice.configuration)
        ds_type = si.datasource_settings.get("type", "")
        if ds_type.startswith("db:"):
            wb_cls = DatabaseWriteBack
        else:
            # We don't support write-back for file-based datasources (Excel/CSV)
            wb_cls = None
        
        if wb_cls:
            try:
                wb_cls(purchase_invoice.configuration).do_all(purchase_invoice)
            except Exception as e:
                logger.exception(f"Failed to perform write-back for invoice {purchase_invoice.number}")


class DatabaseWriteBack(WriteBack):
    FIELD_TYPES = [
        (
            "Timestamp",
            sqlalchemy.types.TIMESTAMP(timezone=True),
            lambda pi: sqlalchemy.sql.functions.current_timestamp(),
        ),
        (
            "SyncStatus",
            sqlalchemy.types.VARCHAR(),
            lambda pi: pi.get_purchase_status_display(),
        ),
        (
            "SyncMessage",
            sqlalchemy.types.VARCHAR(),
            lambda pi: (pi.status_message or "")[:2000],
        ),
    ]

    SUPPORTED_TYPES = {
        "date": (parse_date, sqlalchemy.types.DATE()),
        "str": (str, sqlalchemy.types.VARCHAR()),
        "int": (int, sqlalchemy.types.INTEGER()),
        "": (str, sqlalchemy.types.VARCHAR()),
        None: (str, sqlalchemy.types.VARCHAR()),
    }

    def do_all(self, purchase_invoice):
        """
        Write back sync status to the customer database.
        
        Extracts WriteBackInfo from purchase_invoice.purchase_json.
        """
        wbinfo = (purchase_invoice.purchase_json or {}).get("WriteBackInfo")
        if not wbinfo:
            logger.debug(f"Writeback info missing in invoice {purchase_invoice.number}")
            return
            
        table_name = wbinfo.get("TableName")
        if not table_name:
            logger.warning(f"Writeback table name is missing for invoice {purchase_invoice.number}")
            return

        si = SettingsInfo(self.configuration)
        kwargs = database_connection_kwargs(si.datasource_settings)
        engine = create_engine(**kwargs)
        metadata = sqlalchemy.MetaData(bind=engine)
        
        fields_mapping = wbinfo.get("Fields") or {}
        columns = []
        values = {}
        
        # 1. Prepare result fields (Status, Message, Timestamp)
        for fieldname, fieldtype, lookupfn in self.FIELD_TYPES:
            col_name = fields_mapping.get(fieldname)
            if col_name:
                columns.append(sqlalchemy.Column(col_name, fieldtype))
                values[col_name] = lookupfn(purchase_invoice)
        
        # 2. Prepare Foreign Keys (for identifying the record)
        fks = wbinfo.get("Fk") or {}
        fk_where_checks = {}
        for idx, info in fks.items():
            field_name = info.get("Field")
            field_value = info.get("Value")
            if not field_name or field_value is None:
                continue
                
            field_type = info.get("Type")
            if field_type not in self.SUPPORTED_TYPES:
                field_type = ""
                
            (convert_fn, db_type) = self.SUPPORTED_TYPES[field_type]
            columns.append(sqlalchemy.Column(field_name, db_type))
            
            # Convert value to correct type
            final_value = convert_fn(field_value)
            values[field_name] = final_value
            fk_where_checks[field_name] = final_value

        if not columns:
            logger.warning(f"No columns found for writeback of invoice {purchase_invoice.number}")
            return

        # 3. Execute Write-Back
        # We follow the reference pattern: Delete existing status row and Insert a new one
        status_table = sqlalchemy.Table(table_name, metadata, *columns)
        
        fk_where_clauses = [(status_table.c[k] == v) for (k, v) in fk_where_checks.items()]
        delete_stmt = status_table.delete().where(sqlalchemy.and_(*fk_where_clauses))
        
        insert_stmt = status_table.insert().values(**values)
        
        with engine.begin() as conn:
            conn.execute(delete_stmt)
            conn.execute(insert_stmt)
            
        logger.info(f"Successfully performed write-back for invoice {purchase_invoice.number} to table {table_name}")


def write_back(purchase_invoice):
    """
    Write back details of the Purchase Invoice to the database
    """
    return WriteBack.lookup_config_and_do_all(purchase_invoice)
