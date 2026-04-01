from cz_utils.url_utils import CZ_UUID, cz_url

from . import views

app_name = "invoicing"
urlpatterns = [
    cz_url(r"^$", views.Home),
    cz_url(r"^invoice-list/$", views.InvoiceList),
    cz_url(r"^check-db-connection/$", views.CheckDatabaseConnection),
    cz_url(r"^delete-scheduled-tasks/$", views.DeleteScheduledTasks),
    cz_url(rf"^gstins/{CZ_UUID}/$", views.GstInDetail),
    cz_url(rf"^gstins/{CZ_UUID}/invoices/$", views.GstInInvoiceList),
    cz_url(rf"^pans/{CZ_UUID}/$", views.PermanentAccountNumberDetail),
    cz_url(rf"^pans/{CZ_UUID}/invoices/$", views.PanInvoiceList),
    cz_url(r"^invoices/$", views.InvoiceList),
    cz_url(rf"^invoices-detail/{CZ_UUID}/$", views.PurchaseInvoiceDetail),
    cz_url(rf"^invoices-detail/{CZ_UUID}/.json/$", views.PurchaseInvoiceJson),
    cz_url(
        rf"^invoices-detail/{CZ_UUID}/response/.json/$",
        views.PurchaseInvoiceResponseJson,
    ),
    cz_url(rf"^invoices-detail/{CZ_UUID}/.html/$", views.PurchaseInvoiceHtml),
    cz_url(rf"^invoices-detail/{CZ_UUID}/.pdf2/$", views.PurchaseInvoicePdf),
    cz_url(rf"^gstins/{CZ_UUID}/irp-login/$", views.PurchaseSyncEstablishLoginSession),
    cz_url(r"^sync-session-summary/$", views.SyncSessionStatus),
    cz_url(r"^invoice-count/$", views.InvoiceCountStatus),
    cz_url(rf"^settings/export/.json/{CZ_UUID}/$", views.SettingsExport),
    cz_url(rf"^settings/import/{CZ_UUID}/$", views.SettingsImport),
    cz_url(rf"^settings/json-display/.json/{CZ_UUID}/$", views.SettingsJsonDisplay),
    cz_url(
        rf"^settings/datamapping/choose-table/{CZ_UUID}/$", views.DataMappingChooseTable
    ),
    cz_url(
        rf"^settings/datamapping/choose-worksheet/{CZ_UUID}/$",
        views.DataMappingChooseWorksheet,
    ),
    cz_url(
        rf"^settings/datamapping/choose-columns/{CZ_UUID}/$",
        views.DataMappingChooseColumns,
    ),
    cz_url(
        rf"^settings/datamapping/choose-headers/{CZ_UUID}/$",
        views.DataMappingChooseHeaders,
    ),
    cz_url(
        rf"^settings/datamapping/choose-csv-headers/{CZ_UUID}/$",
        views.DataMappingChooseCsvHeaders,
    ),
    cz_url(rf"^settings/datamapping/set-mapping/{CZ_UUID}/$", views.SetDataMapping),
    cz_url(rf"^settings/datasource/choices/{CZ_UUID}/$", views.DataSourceChoices),
    cz_url(
        rf"^settings/datasource/configure/db/mssql/{CZ_UUID}/$",
        views.ConfigureMicrosoftSqlServer,
    ),
    cz_url(
        rf"^settings/datasource/configure/db/mysql/{CZ_UUID}/$", views.ConfigureMySql
    ),
    cz_url(
        rf"^settings/datasource/configure/db/oracle/{CZ_UUID}/$",
        views.ConfigureOracleDatabase,
    ),
    cz_url(
        rf"^settings/datasource/configure/db/oracle/{CZ_UUID}/$", views.ConfigureOracle
    ),
    cz_url(
        rf"^settings/datasource/configure/db/postgresql/{CZ_UUID}/$",
        views.ConfigurePostgresql,
    ),
    cz_url(
        rf"^settings/datasource/configure/erp/microsoft/{CZ_UUID}/$",
        views.ConfigureMicrosoftDynamicsNavision,
    ),
    cz_url(r"^gstins/create-simple/$", views.GstInCreateSimple),
    cz_url(rf"^settings/datasource/excel/{CZ_UUID}/$", views.ExcelImport),
    cz_url(rf"^settings/datasource/csv/{CZ_UUID}/$", views.CsvImport),
    cz_url(rf"^settings/datasource/oracleebs/{CZ_UUID}/$", views.OracleEbsImport),
    cz_url(rf"^settings/emails/{CZ_UUID}/$", views.ErrorConfigurationUpdate),
    cz_url(rf"^configuration-detail/{CZ_UUID}/$", views.ConfigurationDetail),
    cz_url(rf"^configuration-detail/{CZ_UUID}/update/$", views.ConfigurationUpdate),
    cz_url(r"^configuration-create/$", views.ConfigurationCreate),
    cz_url(r"^configuration-list/$", views.ConfigurationList),
    cz_url(r"^settings/datasource/odbc/$", views.ConfigureOdbc),
    cz_url(r"^settings/auto-sync/$", views.AutoSyncConfiguration),
    cz_url(r"^sync-purchase-invoices/start/$", views.SyncPurchaseInvoicesStartSession),
    cz_url(rf"^sync-purchase-invoices/{CZ_UUID}/$", views.SyncPurchaseInvoices),
    cz_url(
        rf"^sync-purchase-invoices/{CZ_UUID}/status/.json/$",
        views.SyncPurchaseInvoicesStatus,
    ),
    cz_url(r"^post-purchase-data/purchase-json/$", views.PurchaseJsonPost),
    cz_url(r"^invoices/export/xlsx/$", views.ExportInvoicesXlsx),
]
