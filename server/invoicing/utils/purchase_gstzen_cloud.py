"""
Utilities for posting purchase data to GSTZen Cloud
"""

import json
import logging
import os

import requests
from invoicing.models import PurchaseInvoice

logger = logging.getLogger(__name__)

# Base URL for GSTZen Cloud. For local testing, use localhost or the WSL host IP.
# The user specified: "All URLs and API calls should use localhost so I can test them locally."
GSTZEN_CLOUD_BASE_URL = os.environ.get("GSTZEN_CLOUD_BASE_URL", "https://my.gstzen.in")
PURCHASE_ENDPOINT = f"{GSTZEN_CLOUD_BASE_URL}/~gstzen/a/post-purchase-data/purchase-json/"


def post_purchase_to_gstzen(purchase_invoice):
    """
    Post a Purchase Invoice object to GSTZen Cloud
    """
    token = os.environ.get("GSTZEN_AUTH_TOKEN", "")
    error_message = None

    try:
        response = requests.post(
            PURCHASE_ENDPOINT,
            headers={"Token": token},
            json=purchase_invoice.purchase_json,
            timeout=30
        )

        if response.headers.get("Content-Type") == "application/json":
            response_data = response.json()
            purchase_invoice.purchase_response = response_data
            if response.status_code == 200 and response_data.get("status") == 1:
                purchase_invoice.purchase_status = PurchaseInvoice.PIS_UPLOADED
            else:
                purchase_invoice.purchase_status = PurchaseInvoice.PIS_ERROR
                error_message = response_data.get("message", "Unknown error from cloud")
        else:
            message = f"Unexpected response from server: {response.status_code}"
            if response.status_code == 403:
                message = "Permission denied (Auth Token might be invalid)"
            elif response.status_code == 404:
                message = "Endpoint not found"

            purchase_invoice.purchase_response = {"message": message}
            purchase_invoice.purchase_status = PurchaseInvoice.PIS_ERROR
            error_message = message

    except Exception as e:
        logger.exception("Error while posting to GSTZen Cloud")
        error_message = str(e)
        purchase_invoice.purchase_response = {"message": error_message}
        purchase_invoice.purchase_status = PurchaseInvoice.PIS_ERROR

    purchase_invoice.save()
    return error_message


def post_all_purchases_to_gstzen(session=None):
    """
    Post all candidate purchase invoices to GSTZen Cloud
    """
    from invoicing.models import CachedData
    candidates = PurchaseInvoice.objects2.filter(purchase_status=PurchaseInvoice.PIS_CANDIDATE)
    if not candidates:
        logger.info("No candidate purchase invoices found to post to GSTZen Cloud.")
        return []

    all_errors = []
    for purchase_invoice in candidates:
        err = post_purchase_to_gstzen(purchase_invoice)
        if err:
            all_errors.append(err)

    if session and all_errors:
        distinct_errors = list(dict.fromkeys(all_errors))
        CachedData.add_cached_data(datatype=CachedData.DT_PURCHASE_ERRORS, data_json=distinct_errors, group=session)

    return all_errors


