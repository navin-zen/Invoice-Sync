"""
Views related to settings/configuration
"""

import json
import re
import traceback

import pyodbc
from crispy_forms.layout import Layout
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.forms.widgets import TextInput
from django.http import Http404, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, FormView, ListView, View
from invoicing import breadcrumbs
from invoicing.models import Configuration, GlobalConfiguration
from invoicing.utils.datamapper.purchase_fields_spec import PURCHASE_SCHEMA_SPEC as invoicing_SCHEMA_SPEC
from invoicing.utils.jsonschemas.datamapping import DbChooseColumnsEntrypointArgValidator, MappingSpecValidator
from invoicing.utils.settings import SettingsInfo

from cz_utils.breadcrumbs import breadcrumbify
from cz_utils.common_forms import FormTemplateMixin
from cz_utils.crispy_forms_utils import (
    Colsm4 as C4,
    Colsm6 as C6,
    Colsm12 as C12,
    CreateUpdateFormHelper,
    DummyForm,
    DummyFormHelper,
    Row as R,
    single_field_form_helper,
)
from cz_utils.decorators import instance_from_get_object, instance_from_url_uuid
from cz_utils.django.forms.fields import CzChoiceField, CzTypedMultipleChoiceField
from cz_utils.django.views.generic.detail import UuidDetailView, UuidUpdateView
from cz_utils.json_utils import validate_json
from gstnapi.models import ScheduledTask

__all__ = (
    "SettingsExport",
    "SettingsImport",
    "SettingsJsonDisplay",
    "DataSourceChoices",
    "ConfigureMicrosoftSqlServer",
    "ConfigureOracle",
    "ConfigurePostgresql",
    "DataMappingChooseTable",
    "DataMappingChooseColumns",
    "SetDataMapping",
    "ExcelImport",
    "CsvImport",
    "OracleEbsImport",
    "ConfigureOracleDatabase",
    "ConfigureMySql",
    "DataMappingChooseWorksheet",
    "DataMappingChooseHeaders",
    "DataMappingChooseCsvHeaders",
    "ErrorConfigurationUpdate",
    "ConfigureMicrosoftDynamicsNavision",
    "ConfigurationDetail",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationList",
    "ConfigureOdbc",
    "AutoSyncConfiguration",
    "DeleteScheduledTasks",
)


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class ConfigurationDetail(UuidDetailView):
    model = Configuration
    template_name = "invoicing/settings/configuration_detail.html"

    @cached_property
    def settings_info(self):
        return SettingsInfo(self.configuration)


class ConfigurationFormHelper(CreateUpdateFormHelper):
    layout = Layout(R(C4("site_name"), C4("enable_autosync")))


class ConfigurationFormMixin(FormTemplateMixin):
    model = Configuration
    form_helper = ConfigurationFormHelper()
    fields = ("site_name", "enable_autosync")


@breadcrumbify(breadcrumbs)
class ConfigurationCreate(ConfigurationFormMixin, CreateView):
    pass


@breadcrumbify(breadcrumbs, "configuration")
@instance_from_get_object("configuration")
class ConfigurationUpdate(ConfigurationFormMixin, UuidUpdateView):
    cz_submit_button_class = "btn btn-primary"


@breadcrumbify(breadcrumbs)
class ConfigurationList(ListView):
    template_name = "invoicing/settings/configuration_list.html"
    model = Configuration

    @cached_property
    def settings_info(self):
        return SettingsInfo(GlobalConfiguration.get_solo())

    @cached_property
    def scheduled_tasks_status(self):
        qs = ScheduledTask.objects2.all()
        return {
            "running": qs.currently_running().count(),
            "to_be_run": qs.to_be_run().count(),
            "completed": qs.filter(status=ScheduledTask.S_COMPLETE).count(),
            "failed": qs.filter(status=ScheduledTask.S_FAILED).count(),
        }


@instance_from_url_uuid(Configuration)
class SettingsExport(View):
    """
    Download settings as JSON file.
    """

    def get(self, request, *args, **kwargs):
        response = JsonResponse(SettingsInfo(self.configuration).settings_export)
        response["Content-Disposition"] = 'attachment; filename="GSTZEN-settings-{}.json"'.format(
            int(timezone.now().timestamp())
        )
        return response


class SettingsImportForm(forms.Form):
    settings_file = forms.FileField()


@instance_from_url_uuid(Configuration)
@breadcrumbify(breadcrumbs)
class SettingsImport(FormTemplateMixin, FormView):
    """
    Import settings from file saved by the user.
    """

    model = None
    form_class = SettingsImportForm
    form_helper = single_field_form_helper("settings_file")()
    cz_form_button_text = "Restore Settings from Backup"
    success_url = reverse_lazy("invoicing:configuration_list")

    def form_valid(self, form):
        content = self.request.FILES["settings_file"].read()
        try:
            imported = SettingsInfo(self.configuration).import_settings(content)
        except Exception as ex:
            traceback.print_exc()
            messages.error(self.request, f"Error while importing settings: {str(ex)}")
            return super().form_valid(form)
        if imported:
            messages.success(self.request, "Imported settings")
        else:
            messages.error(self.request, "Error while importing settings")
        return super().form_valid(form)


@instance_from_url_uuid(Configuration)
class SettingsJsonDisplay(View):
    def get(self, request, *args, **kwargs):
        return JsonResponse(SettingsInfo(self.configuration).metadata, json_dumps_params={"indent": 4})


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataSourceChoices(UuidDetailView):
    model = Configuration
    template_name = "invoicing/settings/datasource-choices-template.html"


def get_database_driver_choices():
    return [
        ("", "(Choose a Database Driver)"),
    ] + [(c, c) for c in pyodbc.drivers()]


class DatabaseForm(forms.Form):
    hostname = forms.CharField(label="Host Name", required=True, help_text="Provide your db hostname")
    port = forms.CharField(label="Port", help_text="Provide your port number (optional)", required=False)
    username = forms.CharField(
        label="Username",
        required=False,
    )
    password = forms.CharField(label="Password", required=False, widget=forms.PasswordInput(render_value=True))
    database = forms.CharField(label="Database Name", required=True)


class OdbcForm(forms.Form):
    hostname = forms.CharField(label="Host Name", required=False, help_text="Provide your db hostname")
    dsn = forms.CharField(label="DSN", required=True, help_text="Provide your System/User DSN")


class ConfigureMicrosoftDynamicsNavisionForm(forms.Form):
    backend_driver = CzChoiceField(label="Database Driver", required=True, choices=get_database_driver_choices)
    hostname = forms.CharField(label="Host Name", required=True, help_text="Provide your db hostname")
    database = forms.CharField(label="Database Name", required=True)


class MicrosoftSqlServerForm(DatabaseForm):
    backend_driver = CzChoiceField(label="Database Driver", required=True, choices=get_database_driver_choices)


class DatabaseFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C4("hostname"), C4("port"), C4("database")),
        R(C6("username"), C6("password")),
    )


class MicrosoftDynamicsNavisionFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C12("backend_driver")),
        R(C4("hostname"), C4("port"), C4("database")),
    )


class MicrosoftSqlServerFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C12("backend_driver")),
        R(C4("hostname"), C4("port"), C4("database")),
        R(C6("username"), C6("password")),
    )


@instance_from_url_uuid(Configuration)
class ConfigureDatabaseMixin(FormTemplateMixin, FormView):
    model = None
    cz_form_button_text = "Save changes and Test Connection"

    def get_initial(self):
        existing_config = SettingsInfo(self.configuration).get_datasource_config(self.DATA_SOURCE_CONFIG_TYPE)
        fields = self.form_class.base_fields.keys()
        existing = {f: existing_config.get(f) for f in fields}
        existing = {k: v for (k, v) in existing.items() if v}
        existing.update(super().get_initial())
        return existing

    def form_valid(self, form):
        fields = self.form_class.base_fields.keys()
        config = {f: form.cleaned_data[f] for f in fields}
        si = SettingsInfo(self.configuration)
        si.set_datasource_config(self.DATA_SOURCE_CONFIG_TYPE, config)
        si.check_datasource_connection()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoicing:configuration_detail", args=[self.configuration.uuid])


@breadcrumbify(breadcrumbs)
class ConfigureMicrosoftSqlServer(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = MicrosoftSqlServerForm
    form_helper = MicrosoftSqlServerFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "db:mssql"


@breadcrumbify(breadcrumbs)
class ConfigureMySql(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = DatabaseForm
    form_helper = DatabaseFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "db:mysql"


@breadcrumbify(breadcrumbs)
class ConfigureOracle(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = DatabaseForm
    form_helper = DatabaseFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "db:oracle"


@breadcrumbify(breadcrumbs)
class ConfigurePostgresql(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = DatabaseForm
    form_helper = DatabaseFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "db:postgresql"


# Adding configuration for Microsoft Dynamics Navision
@breadcrumbify(breadcrumbs)
class ConfigureMicrosoftDynamicsNavision(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = ConfigureMicrosoftDynamicsNavisionForm
    form_helper = MicrosoftDynamicsNavisionFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "erp:microsoft"


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataMappingChooseTable(UuidDetailView):
    template_name = "invoicing/settings/datamapping/choose_table.html"
    model = Configuration

    @cached_property
    def table_names(self):
        return SettingsInfo(self.configuration).get_database_table_names()


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataMappingChooseWorksheet(UuidDetailView):
    template_name = "invoicing/settings/datamapping/choose_worksheet.html"
    model = Configuration

    @cached_property
    def worksheet_names(self):
        return SettingsInfo(self.configuration).get_excel_worksheet_names()


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataMappingChooseHeaders(UuidDetailView):
    template_name = "invoicing/settings/datamapping/choose_columns.html"
    model = Configuration

    @cached_property
    def table_name(self):
        sheet_name = self.request.GET.get("sheet") or ""
        if not sheet_name:
            raise Http404("Could not find any headers")
        return sheet_name

    @cached_property
    def column_details(self):
        sheet_name = self.table_name
        return SettingsInfo(self.configuration).get_excel_headers(sheet_name)

    @cached_property
    @validate_json(MappingSpecValidator)
    def invoicing_spec(self):
        return invoicing_SCHEMA_SPEC

    @cached_property
    def settings_info(self):
        return SettingsInfo(self.configuration)

    @cached_property
    def example_data(self):
        rows = SettingsInfo(self.configuration).get_excel_example_data()
        if not rows:
            return {}
        return rows[0]

    @cached_property
    @validate_json(DbChooseColumnsEntrypointArgValidator)
    def ts_arg(self):
        return {
            "id": "react-app",
            "dbColumns": self.column_details,
            "invoicingSpec": self.invoicing_spec,
            "exampleData": self.example_data,
            "initialColumnMapping": (self.settings_info.datamapping_settings.get("details") or {}),
            "urls": {
                "setDataMapping": reverse("invoicing:set_data_mapping", args=[self.configuration.uuid]),
                "setColumnMapped": reverse("invoicing:configuration_detail", args=[self.configuration.uuid]),
            },
            "table": self.table_name,
        }


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataMappingChooseCsvHeaders(UuidDetailView):
    template_name = "invoicing/settings/datamapping/choose_columns.html"
    model = Configuration

    @cached_property
    def table_name(self):
        return "hello"

    @cached_property
    def column_details(self):
        return SettingsInfo(self.configuration).get_csv_headers()

    @cached_property
    @validate_json(MappingSpecValidator)
    def invoicing_spec(self):
        return invoicing_SCHEMA_SPEC

    @cached_property
    def settings_info(self):
        return SettingsInfo(self.configuration)

    @cached_property
    def example_data(self):
        rows = SettingsInfo(self.configuration).get_csv_example_data()
        if not rows:
            return {}
        return rows[0]

    @cached_property
    @validate_json(DbChooseColumnsEntrypointArgValidator)
    def ts_arg(self):
        return {
            "id": "react-app",
            "dbColumns": self.column_details,
            "invoicingSpec": self.invoicing_spec,
            "exampleData": self.example_data,
            "initialColumnMapping": (self.settings_info.datamapping_settings.get("details") or {}),
            "urls": {
                "setDataMapping": reverse("invoicing:set_data_mapping", args=[self.configuration.uuid]),
                "setColumnMapped": reverse("invoicing:configuration_detail", args=[self.configuration.uuid]),
            },
            "table": self.table_name,
        }


@breadcrumbify(breadcrumbs)
@instance_from_get_object("configuration")
class DataMappingChooseColumns(UuidDetailView):
    template_name = "invoicing/settings/datamapping/choose_columns.html"
    model = Configuration

    @cached_property
    def table_name(self):
        name = self.request.GET.get("table") or ""
        if not name:
            raise Http404("Could not find table name")
        return name

    @cached_property
    @validate_json(MappingSpecValidator)
    def invoicing_spec(self):
        return invoicing_SCHEMA_SPEC

    @cached_property
    def settings_info(self):
        return SettingsInfo(self.configuration)

    @cached_property
    def column_details(self):
        return self.settings_info.get_table_column_names(self.table_name)

    @cached_property
    def example_data(self):
        rows = self.settings_info.get_table_example_data(self.table_name)
        if not rows:
            return {}
        return rows[0]

    @cached_property
    @validate_json(DbChooseColumnsEntrypointArgValidator)
    def ts_arg(self):
        return {
            "id": "react-app",
            "dbColumns": self.column_details,
            "invoicingSpec": self.invoicing_spec,
            "exampleData": self.example_data,
            "initialColumnMapping": (self.settings_info.datamapping_settings.get("details") or {}),
            "urls": {
                "setDataMapping": reverse("invoicing:set_data_mapping", args=[self.configuration.uuid]),
                "setColumnMapped": reverse("invoicing:configuration_detail", args=[self.configuration.uuid]),
            },
            "table": self.table_name,
        }


@instance_from_get_object("configuration")
@method_decorator(csrf_exempt, name="dispatch")
class SetDataMapping(UuidDetailView):
    http_method_names = ["post"]
    model = Configuration

    def post(self, request, *args, **kwargs):
        print("request", request.body)
        try:
            data = json.loads(request.body)
            SettingsInfo(self.configuration).set_datamapping(data)
        except Exception as ex:
            print(ex)
            return JsonResponse(
                {
                    "status": 0,
                    "message": str(ex),
                },
                status=400,
            )
        return JsonResponse({})


class ExcelFolderUploadForm(forms.Form):
    path = forms.CharField(label="Path", required=True, help_text="Provide the path to your excel ")


class CsvFolderUploadForm(forms.Form):
    path = forms.CharField(label="Path", required=True, help_text="Provide the path to your csv file ")


@breadcrumbify(breadcrumbs)
class ExcelImport(ConfigureDatabaseMixin):
    form_class = ExcelFolderUploadForm
    # form_helper = single_field_form_helper("excel_file")()
    cz_form_button_text = "Select the path of your excel file"
    success_url = reverse_lazy("invoicing:configuration_list")
    DATA_SOURCE_CONFIG_TYPE = "file:excel"


@breadcrumbify(breadcrumbs)
class CsvImport(ConfigureDatabaseMixin):
    form_class = CsvFolderUploadForm
    cz_form_button_text = "Select the path of your csv file"
    success_url = reverse_lazy("invoicing:configuration_list")
    DATA_SOURCE_CONFIG_TYPE = "file:csv"


class OracleEbsImportForm(forms.Form):
    input_directory = forms.CharField(
        label="Input Directory",
        required=True,
        help_text="Provide path to folder containing EBS XML outputs",
    )
    output_directory = forms.CharField(
        label="Output Directory",
        required=True,
        help_text="Provide path to write output from Invoicing Portal",
    )


@breadcrumbify(breadcrumbs)
class OracleEbsImport(ConfigureDatabaseMixin):
    form_class = OracleEbsImportForm
    # form_helper = single_field_form_helper("excel_file")()
    cz_form_button_text = "Configure paths to E-Business Suite XMLs"
    success_url = reverse_lazy("invoicing:configuration_list")
    DATA_SOURCE_CONFIG_TYPE = "erp:oracleebs"


class OracleDatabaseForm(DatabaseForm):
    database = forms.CharField(label="Database Name", required=False)
    backend_driver = CzChoiceField(label="Database Driver", required=False, choices=get_database_driver_choices)
    service_name = forms.CharField(label="Service Name", required=False)


class OracleDatabaseFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C12("backend_driver")),
        R(C6("hostname"), C6("port")),
        R(C6("username"), C6("password")),
        R(C6("database"), C6("service_name")),
    )


@breadcrumbify(breadcrumbs)
class ConfigureOracleDatabase(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = OracleDatabaseForm
    form_helper = OracleDatabaseFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "db:oracle"


class ErrorConfigurationForm(forms.Form):
    emails = forms.CharField(
        label="Email-ID of Recipients",
        required=True,
        help_text="Add email-id of the recipients",
        widget=TextInput,
    )
    from_email = forms.CharField(
        label="From Email Address",
        required=True,
        help_text="From Address",
        widget=TextInput,
    )
    auth_user = forms.CharField(
        label="Username",
        required=True,
        help_text="Username to authenticate to SMTP server",
    )
    auth_password = forms.CharField(
        label="Password",
        required=True,
        widget=forms.PasswordInput(render_value=True),
        help_text="Password to authenticate to SMTP server",
    )
    host = forms.CharField(label="Host", required=True, help_text="Email Host")
    port = forms.CharField(label="Port", required=True, help_text="Email Port")
    if_ssl = forms.CharField(
        label="Use SSL",
        required=True,
        help_text="Yes/No. If No, then TLS will be used by default.",
    )

    def clean_emails(self):
        email_uncleaned_list = re.split(r"[,; ]", self.cleaned_data["emails"])
        valid_emails = []
        for e in email_uncleaned_list:
            e = e.strip()
            if e != "":
                try:
                    validate_email(e)
                    valid_emails.append(e)
                except Exception:
                    raise ValidationError(f"Invalid email-id '{e}'")
        return valid_emails


class ErrorConfigurationFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C12("emails")),
        R(C4("from_email"), C4("auth_user"), C4("auth_password")),
        R(C6("host"), C6("port"), C6("if_ssl")),
    )


@instance_from_url_uuid(Configuration)
@breadcrumbify(breadcrumbs)
class ErrorConfigurationUpdate(FormTemplateMixin, FormView):
    view_description = "Error Configuration Emails"
    form_class = ErrorConfigurationForm
    form_helper = ErrorConfigurationFormHelper()
    cz_form_button_text = "Save"
    cz_submit_button_class = "btn btn-success"
    cz_page_title = "Error Configuration Emails"
    cz_form_css_class = ""

    def form_valid(self, form):
        emails = form.cleaned_data["emails"]
        from_email = form.cleaned_data["from_email"]
        auth_user = form.cleaned_data["auth_user"]
        auth_password = form.cleaned_data["auth_password"]
        host = form.cleaned_data["host"]
        port = form.cleaned_data["port"]
        if_ssl = form.cleaned_data["if_ssl"]
        si = SettingsInfo(self.configuration)
        si.set_notification_emails(emails, from_email, auth_user, auth_password, host, port, if_ssl)
        messages.success(self.request, "Emails Configured Successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoicing:configuration_detail", args=[self.configuration.uuid])


class ConfigureOdbcForm(forms.Form):
    DSN = forms.CharField(label="DSN", required=True, help_text="Provide your DSN Name")
    hostname = forms.CharField(label="Host Name", required=True, help_text="Provide your db hostname")


class OdbcFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C12("dsn")),
        R(C4("hostname")),
    )


@breadcrumbify(breadcrumbs)
class ConfigureOdbc(ConfigureDatabaseMixin):
    model = None
    cz_form_button_text = "Save changes and Test Connection"
    form_class = OdbcForm
    form_helper = OdbcFormHelper()
    DATA_SOURCE_CONFIG_TYPE = "odbc"


def get_hours_choices():
    return [(h, str(h)) for h in range(0, 24)]


def get_weekdays_choices():
    return [
        ("Sunday", "Sunday"),
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
    ]


class AutoSyncConfigurationForm(forms.Form):
    minutes = forms.IntegerField(label="Minute(s)", required=True)
    start_hour = CzChoiceField(label="Start Hour", required=True, choices=get_hours_choices)
    end_hour = CzChoiceField(label="End Hour", required=True, choices=get_hours_choices)
    weekdays = CzTypedMultipleChoiceField(label="Weekday(s)", required=True, choices=get_weekdays_choices)

    def clean_minutes(self):
        minutes = self.cleaned_data["minutes"]
        if minutes <= 0:
            raise ValidationError(f"Invalid Value {minutes}")
        return minutes


class AutoSyncConfigurationFormHelper(CreateUpdateFormHelper):
    layout = Layout(R(C4("minutes"), C4("start_hour"), C4("end_hour"), C6("weekdays")))


@breadcrumbify(breadcrumbs)
class AutoSyncConfiguration(FormTemplateMixin, FormView):
    view_description = "Schedule Auto-Sync"
    form_class = AutoSyncConfigurationForm
    form_helper = AutoSyncConfigurationFormHelper()
    cz_form_button_text = "Save"
    cz_submit_button_class = "btn btn-success"
    cz_page_title = "Schedule Auto-Sync"
    cz_form_css_class = ""

    def form_valid(self, form):
        minutes = form.cleaned_data["minutes"]
        start_hour = form.cleaned_data["start_hour"]
        end_hour = form.cleaned_data["end_hour"]
        weekdays = form.cleaned_data["weekdays"]
        si = SettingsInfo(GlobalConfiguration.get_solo())
        si.set_autosync_configuration(minutes, start_hour, end_hour, weekdays)
        messages.success(self.request, "Auto-Sync Configured Successfully")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoicing:configuration_list")


@breadcrumbify(breadcrumbs)
class DeleteScheduledTasks(FormTemplateMixin, FormView):
    view_description = "Delete existing Scheduled Tasks"
    form_class = DummyForm
    form_helper = DummyFormHelper()
    cz_page_title = "Delete Scheduled Tasks"
    cz_form_css_class = ""
    cz_form_button_text = "Yes, delete Scheduled Tasks"
    cz_submit_button_class = "btn btn-danger"

    def cz_form_message_text(self):
        return "Do you want to delete all the Scheduled Tasks?"

    def form_valid(self, form):
        ScheduledTask.objects2.all().delete()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("invoicing:configuration_list")

    @cached_property
    def cz_extra_form_buttons(self):
        return [
            {
                "formmethod": "GET",
                "formaction": self.get_success_url(),
                "text": "No, Go Back",
                "css_class": "btn btn-info ml-3",
            }
        ]


