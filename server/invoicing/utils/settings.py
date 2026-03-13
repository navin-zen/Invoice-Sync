"""
Utilities related to the settings
"""

import logging

from django.db import transaction
from invoicing.models import Configuration, GlobalConfiguration
from invoicing.utils.datamapper.purchase_fields_spec import PURCHASE_SCHEMA_SPEC as invoicing_SCHEMA_SPEC
from invoicing.utils.datasource.databases import (
    check_connection,
    check_microsoft_dynamics_connection,
    check_oracle_ebs_paths,
    checkCsvFile,
    checkExcelFile,
    create_engine,
    create_engine_for_microsoft_dynamics,
    database_connection_kwargs,
    get_column_names,
    get_example_row,
    get_excel_filepath_for_glob,
    get_table_names,
    microsoft_dynamics_connection_kwargs,
)
from invoicing.utils.jsonschemas.datamapping import ColumnMappingValidator
from pygstn.utils import json
from pygstn.utils.crypto import hmac_sha256
from pygstn.utils.utils import b64decode, b64encode, to_bytes, to_unicode
from utils.importer import CustomCsv, CustomXls

logger = logging.getLogger(__name__)


class SettingsInfo:
    HMAC_KEY = b"0" * 32

    def __init__(self, globalconfiguration):
        assert globalconfiguration is not None
        self.globalconfiguration = globalconfiguration or GlobalConfiguration.get_solo()

    @property
    def metadata(self):
        return self.globalconfiguration.metadata or {}

    @property
    def settings_export(self):
        """
        Export settings in JSON format
        """
        config_details = [
            {
                "site_name": config.site_name,
                "metadata": config.metadata,
            }
            for config in Configuration.objects2.all()
        ]
        data = b64encode(json.dumps(config_details).encode("utf-8"))
        return {
            "data": to_unicode(data),
            "hmac": to_unicode(hmac_sha256(data, self.HMAC_KEY)),
        }

    @transaction.atomic
    def import_settings(self, s):
        """
        Import settings in JSON format
        """
        try:
            contents = json.loads(s)
        except ValueError:
            raise ValueError("Invalid JSON while importing settings")
        data = contents.get("data") or ""
        hmac = contents.get("hmac") or ""
        if not data or not hmac:
            raise ValueError("Could not find data or hmac in settings details")
        if hmac_sha256(to_bytes(data), self.HMAC_KEY) != to_bytes(hmac):
            raise ValueError("Data integrity error while importing settings.")
        try:
            configurations = json.loads(b64decode(data))
        except ValueError:
            raise ValueError("Could not decode data while importing settings")

        # delete the exisiting configurations before restoring
        Configuration.objects2.all().delete()
        for i, config in enumerate(configurations, start=1):
            obj = Configuration(
                site_name=config.get("site_name") or f"Configuration{i}",
                metadata=config.get("metadata", {}),
            )
            obj.full_clean()
            obj.save()
        return True

    @property
    def datasource_settings(self):
        return self.metadata.get("datasource") or {}

    @property
    def datamapping_settings(self):
        return self.metadata.get("datamapping") or {}

    @property
    def notification_settings(self):
        return self.metadata.get("notifications") or {}

    @property
    def autosync_settings(self):
        return self.metadata.get("auto_sync_configuration") or {}

    @property
    def datasource_status(self):
        """
        Returns status of the datasource settings

        Returns True if everything is set and proper, False if there is an
        error when we tried to access the datasource, None if the setting
        is not available.
        """
        ds = self.datasource_settings
        if ds and ds.get("type") and ds.get("config") and ds.get("status"):
            if ds["status"].get("status"):
                return True
            else:
                return False
        return None

    @property
    def datamapping_status(self):
        """
        Returns status of columns mapped
        """
        ds = self.datamapping_settings
        return ds and ds.get("complete")

    @property
    def datamapping_errors(self):
        ds = self.datamapping_settings
        return (ds and ds.get("errors")) or []

    def get_datasource_config(self, type_):
        """
        Get the existing config that is entered for a particular type of
        datasource
        """
        ds = self.datasource_settings
        return (ds and (ds.get("type") == type_) and ds.get("config")) or {}

    def get_notification_emails(self):
        """
        Get all the configured email ids
        """
        ns = self.notification_settings.get("email_details")
        if ns is None:
            return []
        else:
            return ns.get("emails") or []

    def set_notification_emails(self, emails, from_email, auth_user, auth_password, host, port, if_ssl):
        """
        Set all the configured email ids
        """
        self.globalconfiguration.metadata["notifications"] = {
            "email_details": {
                "emails": emails,
                "from_email": from_email,
                "auth_user": auth_user,
                "auth_password": auth_password,
                "host": host,
                "port": port,
                "if_ssl": if_ssl,
            }
        }
        self.globalconfiguration.save()

    def set_autosync_configuration(self, minutes, start_hour, end_hour, weekdays):
        """
        Set all the auto sync settings
        """
        self.globalconfiguration.metadata["auto_sync_configuration"] = {
            "minutes": minutes,
            "start_hour": start_hour,
            "end_hour": end_hour,
            "weekdays": weekdays,
        }
        self.globalconfiguration.save()

    def set_datasource_config(self, type_, config):
        """
        Set the datasource configuration for a particular type of
        datasource.
        """
        self.globalconfiguration.metadata["datasource"] = {
            "type": type_,
            "config": config,
            "status": {},
        }
        if (self.globalconfiguration.metadata.get("datamapping") or {}).get("type") != type_:
            self.globalconfiguration.metadata["datamapping"] = {}
        self.globalconfiguration.save()

    def check_datasource_connection(self):
        """
        Check the datasource connection and save it back to the
        GlobalConfiguration object
        """
        ds = self.datasource_settings
        config = (ds and ds.get("config")) or {}
        if not config:
            raise ValueError("Unable to find datasource config")
        if (ds.get("type") or "").startswith("db:"):
            kwargs = database_connection_kwargs(ds)
            status = check_connection(**kwargs)
            logger.info(f"check_connection: status: {status}")
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        elif (ds.get("type") or "") == "file:excel":
            kwargs = database_connection_kwargs(ds)
            status = checkExcelFile(**kwargs)
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        elif (ds.get("type") or "") == "file:csv":
            kwargs = database_connection_kwargs(ds)
            status = checkCsvFile(**kwargs)
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        elif (ds.get("type") or "") == "erp:oracleebs":
            kwargs = database_connection_kwargs(ds)
            status = check_oracle_ebs_paths(**kwargs)
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        elif (ds.get("type") or "").startswith("erp:"):
            kwargs = microsoft_dynamics_connection_kwargs(ds)
            status = check_microsoft_dynamics_connection(**kwargs)
            logger.info(f"check_connection: status: {status}")
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        elif (ds.get("type") or "").startswith("odbc"):
            kwargs = database_connection_kwargs(ds)
            status = check_connection(**kwargs)
            logger.info(f"check_connection: status: {status}")
            self.globalconfiguration.metadata["datasource"]["status"] = status
            self.globalconfiguration.save()
        else:
            raise NotImplementedError("Unsupported datasource type")

    def get_database_table_names(self):
        """
        Get the database table and view names
        """
        ds = self.datasource_settings
        config = (ds and ds.get("config")) or {}
        if not config:
            raise ValueError("Unable to find datasource config")
        if (ds.get("type") or "").startswith("db:"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_table_names(engine)
        elif (ds.get("type") or "").startswith("erp:"):
            kwargs = microsoft_dynamics_connection_kwargs(ds)
            engine = create_engine_for_microsoft_dynamics(**kwargs)
            return get_table_names(engine)
        elif (ds.get("type") or "").startswith("odbc"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_table_names(engine)
        else:
            raise NotImplementedError("Unsupported datasource type")

    def get_table_column_names(self, table_name):
        """
        Get the database table and view names
        """
        ds = self.datasource_settings
        config = (ds and ds.get("config")) or {}
        if not config:
            raise ValueError("Unable to find datasource config")
        if (ds.get("type") or "").startswith("db:"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_column_names(engine, table_name)
        elif (ds.get("type") or "").startswith("erp:"):
            kwargs = microsoft_dynamics_connection_kwargs(ds)
            engine = create_engine_for_microsoft_dynamics(**kwargs)
            return get_column_names(engine, table_name)
        elif (ds.get("type") or "").startswith("odbc"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_column_names(engine, table_name)
        else:
            raise NotImplementedError("Unsupported datasource type")

    def get_table_example_data(self, table_name):
        ds = self.datasource_settings
        config = (ds and ds.get("config")) or {}
        if not config:
            raise ValueError("Unable to find datasource config")
        if (ds.get("type") or "").startswith("db:"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_example_row(engine, table_name)
        elif (ds.get("type") or "").startswith("erp:"):
            kwargs = microsoft_dynamics_connection_kwargs(ds)
            engine = create_engine_for_microsoft_dynamics(**kwargs)
            return get_example_row(engine, table_name)
        elif (ds.get("type") or "").startswith("odbc"):
            kwargs = database_connection_kwargs(ds)
            engine = create_engine(**kwargs)
            return get_example_row(engine, table_name)
        else:
            raise NotImplementedError("Unsupported datasource type")

    @classmethod
    def calculate_datamapping_errors(cls, mapping_details):
        """
        Whether datamapping details provided by the user is complete.

        We check whether we have values for all the required fields.
        """
        DISPLAY_NAMES = {
            field["name"]: field["displayName"]
            for section in invoicing_SCHEMA_SPEC["sections"]
            for field in section["fields"]
        }
        errors = []
        for section in invoicing_SCHEMA_SPEC["sections"]:
            for field in section["fields"]:
                if not field["required"]:
                    continue
                if field["name"] not in mapping_details:
                    errors.append("Field '{}' is not mapped".format(field["displayName"]))
                    continue
                field_details = mapping_details[field["name"]]
                if field_details["type"] == "column" and not field_details["column"]:
                    errors.append("Column name of Field '{}' is not provided".format(field["displayName"]))
        for this, that in invoicing_SCHEMA_SPEC["exclusive_or"]:
            if (this not in mapping_details) and (that not in mapping_details):
                errors.append(f"Either '{DISPLAY_NAMES[this]}' or '{DISPLAY_NAMES[that]}' is required")
            if (this in mapping_details) and (that in mapping_details):
                errors.append(f"Only '{DISPLAY_NAMES[this]}' or '{DISPLAY_NAMES[that]}' should be mapped, not both")
        for fields in invoicing_SCHEMA_SPEC["all_or_none"]:
            if any((f in mapping_details) for f in fields):
                if not all((f in mapping_details) for f in fields):
                    errors.append(
                        "All fields in {} should be mapped".format(", ".join(f"'{DISPLAY_NAMES[f]}'" for f in fields))
                    )
        return errors

    def set_datamapping(self, data):
        """
        Save details of column mapping provided by the user.
        """
        type_ = (self.globalconfiguration.metadata["datasource"] or {}).get("type")
        if not type_:
            raise ValueError(*"Data source type is not available")
        table = data.get("table") or ""
        if not table:
            raise ValueError("Missing table name while setting data mapping")
        mapping_details = data.get("details")
        ColumnMappingValidator(mapping_details)
        errors = self.calculate_datamapping_errors(mapping_details)
        self.globalconfiguration.metadata["datamapping"] = {
            "complete": not errors,
            "errors": errors,
            "type": type_,
            "details": mapping_details,
            "table": table,
        }
        self.globalconfiguration.save()

    @property
    def mapping_details_display(self):
        """
        Mapping details suitable for display in HTML template
        """
        mapping_details = self.datamapping_settings.get("details") or {}
        mapping_details_for_display = []
        for section in invoicing_SCHEMA_SPEC["sections"]:
            for field in section["fields"]:
                if field["name"] not in mapping_details:
                    continue
                mapping_details_for_display.append(
                    {
                        "section": section["name"],
                        "name": field["displayName"],
                        "source": mapping_details[field["name"]],
                    }
                )
        return mapping_details_for_display

    def get_excel_stream_from_settings(self, file_type=None):
        ds = self.datasource_settings
        pattern = ds["config"]["path"]
        path = get_excel_filepath_for_glob(pattern)
        if file_type == "csv":
            return open(path)
        return open(path, "rb")

    def get_excel_worksheet_names(self):
        xls_stream = self.get_excel_stream_from_settings()
        return CustomXls.get_worksheets_wrapper(xls_stream)

    def get_excel_headers(self, sheet_name):
        xls_stream = self.get_excel_stream_from_settings()
        return CustomXls.get_header_row_from_dataset_wrapper(xls_stream, sheet_name=sheet_name)

    def get_csv_headers(self):
        in_stream = self.get_excel_stream_from_settings(file_type="csv")
        return CustomCsv.get_header_row(in_stream)

    def get_excel_example_data(self):
        in_stream = self.get_excel_stream_from_settings()
        return CustomXls.create_example_row(in_stream)

    def get_csv_example_data(self):
        in_stream = self.get_excel_stream_from_settings(file_type="csv")
        return CustomCsv.create_example_row(in_stream)


