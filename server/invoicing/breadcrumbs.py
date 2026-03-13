from django.urls import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from cz_utils.breadcrumbs import BreadCrumb, DetailBreadCrumb, DetailFollowerBreadCrumb


class HomeBC(BreadCrumb):
    prev = None
    data = (reverse_lazy("invoicing:home"), mark_safe('<i class="ml-1 fa-solid fa-house"></i>'))


class PermanentAccountNumberDetailBC(DetailBreadCrumb):
    prev = HomeBC


class GstInDetailBC(DetailBreadCrumb):
    prev = HomeBC


class InvoiceListBC(BreadCrumb):
    prev = HomeBC
    data = (reverse_lazy("invoicing:invoice_list"), "Purchase Invoices")


class PurchaseInvoiceDetailBC(DetailBreadCrumb):
    prev = InvoiceListBC


class GstInInvoiceListBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = GstInDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:gst_in_invoice_list", args=[self.obj.uuid])
        return (url, "Invoices")


class PanInvoiceListBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = PermanentAccountNumberDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:pan_invoice_list", args=[self.obj.uuid])
        return (url, "Invoices")


class PurchaseSyncEstablishLoginSessionBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = GstInDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:purchase_sync_establish_login_session", args=[self.obj.uuid])
        return (url, mark_safe('Purchase Sync Login <i class="ml-1 fa fa-unlock-alt"></i>'))


class SettingsHomeBC(BreadCrumb):
    prev = HomeBC
    data = (
        reverse_lazy("invoicing:configuration_list"),
        mark_safe('Settings <i class="ml-1 fa fa-wrench"></i>'),
    )


class ConfigurationListBC(BreadCrumb):
    prev = HomeBC
    data = (
        reverse_lazy("invoicing:configuration_list"),
        mark_safe('Settings <i class="ml-1 fa fa-wrench"></i>'),
    )


class ConfigurationDetailBC(DetailBreadCrumb):
    prev = ConfigurationListBC

    @cached_property
    def data(self):
        url = reverse("invoicing:configuration_detail", args=[self.obj.uuid])
        return (url, mark_safe(self.obj.site_name))


class ConfigurationUpdateBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    data = ("", "Update")


class ConfigurationCreateBC(BreadCrumb):
    prev = ConfigurationListBC
    data = (reverse_lazy("invoicing:configuration_list"), mark_safe("Settings List"))


class SettingsImportBC(BreadCrumb):
    prev = SettingsHomeBC
    data = ("", "Import Settings from Backup")


class DataSourceChoicesBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_source_choices", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Data Source"))


class DataMappingChooseTableBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_mapping_choose_table", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Table"))


class DataMappingChooseWorksheetBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_mapping_choose_worksheet", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Worksheet"))


class DataMappingChooseHeadersBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_mapping_choose_headers", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Headers"))


class DataMappingChooseCsvHeadersBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_mapping_choose_csv_headers", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Headers"))


class DataMappingChooseColumnsBC(DetailFollowerBreadCrumb):
    detail_breadcrumb_class = ConfigurationDetailBC

    @cached_property
    def data(self):
        url = reverse("invoicing:data_mapping_choose_columns", args=[self.obj.uuid])
        return (url, mark_safe("Choose your Columns"))


class ConfigureMicrosoftSqlServerBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Microsoft SQL Server Details")


class ConfigureMySqlBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "MySQL DB Details")


class ConfigureOracleDatabaseBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Oracle DB Details")


class ConfigureOracleBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Oracle DB Details")


class ConfigurePostgresqlBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Postgresql DB Details")


class ConfigureMicrosoftDynamicsNavisionBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Microsoft Dynamics Navision Details")


class GstInCreateSimpleBC(BreadCrumb):
    prev = HomeBC

    @cached_property
    def data(self):
        url = reverse(
            "invoicing:configuration_list",
        )
        return (url, "Create GSTIN")


class ConfigureOdbcBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:settings_home"), "ODBC Details")


class ExcelImportBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Excel File Details")


class CsvImportBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "CSV File Details")


class OracleEbsImportBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Oracle EBS Configuration")


class ErrorConfigurationUpdateBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Email Configuration")


class AutoSyncConfigurationBC(BreadCrumb):
    prev = SettingsHomeBC
    data = (reverse_lazy("invoicing:configuration_list"), "Auto-Sync Configuration")


class DeleteScheduledTasksBC(BreadCrumb):
    prev = ConfigurationListBC
    data = ("", "Delete Scheduled Tasks")


