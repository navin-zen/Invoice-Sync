"""
Our custom GSTN Client

Logs requests and responses to the database
"""

import os

from django.conf import settings
from pygstn.clients import (
    CygnetProductionClient as CygnetProductionClientBase,
    CygnetSandboxClient as CygnetSandboxClientBase,
    EInvoiceSandboxClient as EInvoiceSandboxClientBase,
    EInvoiceTestClient as EInvoiceTestClientBase,
    GovernmentEinvoiceProductionClient as GovernmentEinvoiceProductionClientBase,
    GstnSandboxClient as GstnSandboxClientBase,
    GstnTestClient as GstnTestClientBase,
    VayanaEinvoiceProductionClient as VayanaEinvoiceProductionClientBase,
)

from ..models import TransactionLog

MOCK_APP_KEY = b"0123456789ABCDEF0123456789ABCDEF"


class LogTransactionMixin:
    """
    Mixin that logs request and responses to the DB

    Refer to the Gstn*Client classes for documentation of the arguments to
    the methods defined below.
    """

    def log_request(self, method, api_base_path, version, path, action, data, headers={}, url=None):
        super().log_request(
            method,
            api_base_path,
            version,
            path,
            action,
            data,
            headers,
            url=url,
        )
        url = self.make_url(api_base_path, version, path)
        transactionlog = TransactionLog(
            schema_name="unused",  # Needed for testing
            transaction_identifier=headers.get("txn", ""),
            url=url,
            headers=headers,
            payload=data,
        )
        transactionlog.save()
        return transactionlog

    def log_response(self, logobj, response, response_data=None):
        super().log_response(logobj, response, response_data)
        transactionlog = logobj
        transactionlog.status_code = response.status_code
        if response_data is not None:
            transactionlog.response = response_data
        else:
            transactionlog.raw_response = response.content
        transactionlog.elapsed = response.elapsed
        transactionlog.save(
            update_fields=[
                "response",
                "elapsed",
                "raw_response",
                "status_code",
            ]
        )


class GstnTestClient(LogTransactionMixin, GstnTestClientBase):
    pass


class EInvoiceTestClient(LogTransactionMixin, EInvoiceTestClientBase):
    pass


class GstnSandboxClient(LogTransactionMixin, GstnSandboxClientBase):
    pass


class CygnetProductionClient(LogTransactionMixin, CygnetProductionClientBase):
    pass


class CygnetSandboxClient(LogTransactionMixin, CygnetSandboxClientBase):
    pass


class EInvoiceSandboxClient(LogTransactionMixin, EInvoiceSandboxClientBase):
    pass


class VayanaEinvoiceProductionClient(LogTransactionMixin, VayanaEinvoiceProductionClientBase):
    pass


class GovernmentEinvoiceProductionClient(LogTransactionMixin, GovernmentEinvoiceProductionClientBase):
    pass


class MockGstnClient(LogTransactionMixin, GstnTestClientBase):
    """
    Connects to our mock server that returns dummy responses.

    The URL is https://my.gstzen.in/mockgstn/ or http://localhost:port/mockgstn/

    It should be set in the environment variable
    """

    HOSTNAME = DOWNLOAD_HOSTNAME = os.environ.get("GST_MOCKGSTN_SERVER_URL", "https://www.example.com")


class MockEInvoiceClient(LogTransactionMixin, EInvoiceSandboxClientBase):
    HOSTNAME = DOWNLOAD_HOSTNAME = os.environ.get("GST_MOCKGSTN_SERVER_URL", "https://www.example.com")


CLIENT_CLASSES = {
    "": GstnTestClient,
    "sandbox": GstnSandboxClient,
    "cygnet-sandbox": CygnetSandboxClient,
    "production": CygnetProductionClient,
}

EINVOICE_CLIENT_CLASSES = {
    "": EInvoiceTestClient,
    "sandbox": EInvoiceSandboxClient,
    "production": EInvoiceSandboxClient,
    "vayana-production": VayanaEinvoiceProductionClient,
    "direct": GovernmentEinvoiceProductionClient,
}


def get_client_class(client_type=None):
    if client_type:
        return CLIENT_CLASSES[client_type]
    else:
        return CLIENT_CLASSES[os.environ.get("GSTN_ENVIRONMENT", "")]


def get_einvoice_client_class(client_type=None):
    if client_type:
        return EINVOICE_CLIENT_CLASSES[client_type]
    else:
        return EINVOICE_CLIENT_CLASSES[os.environ.get("GSTN_ENVIRONMENT", "")]


def get_gstnclient():
    """
    Returns an appropriate client based on the environment variable
    """
    return get_client_class()(settings.GSTN_CLIENT_ID, settings.GSTN_CLIENT_SECRET, verbosity=2)


def get_einvoiceclient(client_id, client_secret, client_type=None):
    """
    Returns an appropriate client based on the environment variable
    """
    return get_einvoice_client_class(client_type=client_type)(client_id, client_secret, verbosity=2)


MOCK_GSTINS = [
    "29AAFCC9980MZZT",
    "29AAFCC9980MYZU",
    "27AAFCC9980MZZX",
    "36AAFCC9980MZZY",
    "33AAFCC9980MZZ4",
    "07AAFCC9980MZZZ",
    "06AAFCC9980MZZ1",
    "19AAFCC9980MZZU",
]


def get_gstnclient_or_mock(gstin_string):
    """
    Get a real GSTN client or one that talks to our mock server
    """
    if gstin_string.strip().upper() in MOCK_GSTINS:
        return MockGstnClient("MOCK_ID", "MOCK_SECRET", verbosity=2)
    else:
        return get_gstnclient()


def get_einvoiceclient_or_mock(gstin_string, client_id, client_secret, client_type=None):
    """
    Get a real E-Invoice client or one that talks to our mock server

    Each GSTIN has its own client_id and client_secret.
    """
    if gstin_string.strip().upper() in MOCK_GSTINS:
        return MockEInvoiceClient("MOCK_ID", "MOCK_SECRET", verbosity=2)
    else:
        if os.environ.get("GSTN_ENVIRONMENT", "") == "direct":
            client_type = "direct"
        elif client_id.strip().upper() == "PRODUCTION":
            client_type = "vayana-production"
        else:
            client_type = client_type
        return get_einvoiceclient(client_id, client_secret, client_type=client_type)


def app_key_or_mock(gstin_string):
    """
    Get an app_key to establish a GSTN session.

    The default value is None in which case, pygstn will create a random
    app key. However, when we are mocking GSTN responses for demo purposes,
    we want to use a fixed app_key.
    """
    if gstin_string.strip().upper() in MOCK_GSTINS:
        return MOCK_APP_KEY
    else:
        return None
