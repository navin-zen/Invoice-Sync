"""
Utilities for posting purchase data to GSTZen Cloud
"""

import json
import logging
import os

import requests
from concurrent.futures import ThreadPoolExecutor
from invoicing.models import PurchaseInvoice
from invoicing.utils.settings import SettingsInfo
from invoicing.utils.sqlalchemy_invoice_generation import FetchInvoices

logger = logging.getLogger(__name__)

# Base URL for GSTZen Cloud. For local testing, use localhost or the WSL host IP.
# The user specified: "All URLs and API calls should use localhost so I can test them locally."
GSTZEN_CLOUD_BASE_URL = os.environ.get("GSTZEN_CLOUD_BASE_URL", "https://my.gstzen.in")
PURCHASE_ENDPOINT = f"{GSTZEN_CLOUD_BASE_URL}/~gstzen/a/post-purchase-data/purchase-json/"


def post_purchase_to_gstzen(purchase_invoice, session=None, commit=True):
    """
    Post a Purchase Invoice object to GSTZen Cloud
    """
    token = os.environ.get("GSTZEN_AUTH_TOKEN", "")
    error_message = None

    try:
        post_kwargs = {
            "headers": {"Token": token},
            "json": purchase_invoice.purchase_json,
            "timeout": 30
        }
        if session:
            response = session.post(PURCHASE_ENDPOINT, **post_kwargs)
        else:
            response = requests.post(PURCHASE_ENDPOINT, **post_kwargs)

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
        
    if commit:
        purchase_invoice.save()
    
    # Write back the status to the customer database
    # from invoicing.utils.write_back import write_back
    # write_back(purchase_invoice)
    
    return error_message, purchase_invoice


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
    modified_objects = []
    
    # Use requests.Session to reuse connections
    with requests.Session() as http_session:
        # Use ThreadPoolExecutor to parallelize requests
        # We use a small number of workers (5) to avoid overwhelming the server
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Create a list of futures. Note: commit=False to avoid concurrent writes in SQLite
            futures = [executor.submit(post_purchase_to_gstzen, pi, http_session, commit=False) for pi in candidates]
            
            # Collect results as they complete
            for future in futures:
                try:
                    err, pi = future.result()
                    modified_objects.append(pi)
                    if err:
                        all_errors.append(err)
                except Exception as e:
                    logger.exception("Unexpected error in parallel upload thread")
                    all_errors.append(str(e))

    # Perform a single bulk_update in the main thread to ensure SQLite safety
    if modified_objects:
        # bulk_update skips auto_now=True, so we handle it manually
        from django.utils import timezone
        now = timezone.now()
        for pi in modified_objects:
            pi.modify_date = now
            
        PurchaseInvoice.objects2.bulk_update(
            modified_objects, 
            fields=["purchase_status", "purchase_response", "modify_date"],
            batch_size=500
        )
        logger.info(f"Bulk updated {len(modified_objects)} purchase invoices with cloud sync results")
        config_results = {}
        for pi in modified_objects:
            cfg = pi.configuration
            if cfg.id not in config_results:
                config_results[cfg.id] = {"config": cfg, "successes": [], "errors": [], "success_objects": [], "error_objects": []}
            
            # Extract Invoice Number for reporting
            inv_no = pi.ctin
            if pi.purchase_json and isinstance(pi.purchase_json, dict):
                inv_no = pi.purchase_json.get("DocDtls", {}).get("No", inv_no)

            if pi.purchase_status == PurchaseInvoice.PIS_UPLOADED:
                config_results[cfg.id]["successes"].append(inv_no)
                config_results[cfg.id]["success_objects"].append(pi)
            else:
                err_msg = "Unknown error"
                if pi.purchase_response and isinstance(pi.purchase_response, dict):
                    err_msg = pi.purchase_response.get("message", "Unknown error")
                config_results[cfg.id]["errors"].append(f"Invoice {inv_no}: {err_msg}")
                config_results[cfg.id]["error_objects"].append(pi)

        class CloudSyncEmailer(FetchInvoices):
            def do_all(self): pass
            def get_unvalidated_lineitems(self): pass

            def complete_init(self):
                # Set filename for attachment if it's a file-based source
                from invoicing.utils.datasource.databases import get_excel_filepath_for_glob
                si = SettingsInfo(self.configuration)
                ds_settings = si.datasource_settings
                
                # Fallback to Global Configuration if Site configuration is empty
                if not ds_settings or not ds_settings.get("config"):
                    from invoicing.models import GlobalConfiguration
                    si = SettingsInfo(GlobalConfiguration.get_solo())
                    ds_settings = si.datasource_settings
                
                ds_type = ds_settings.get("type", "")
                if ds_type.startswith("file:"):
                    path_pattern = ds_settings.get("config", {}).get("path")
                    if path_pattern:
                        try:
                            self.filename = get_excel_filepath_for_glob(path_pattern)
                            logger.info(f"CloudSyncEmailer: Found attachment file: {self.filename}")
                        except Exception as e:
                            logger.warning(f"CloudSyncEmailer: Could not find source file for attachment: {path_pattern}. Error: {e}")

        for results in config_results.values():
            cfg = results["config"]
            si = SettingsInfo(cfg)
            notification = si.notification_settings
            
            if not notification or not notification.get("email_details"):
                continue
                
            emailer = CloudSyncEmailer(cfg, session, {}, {}, notification)
            
            if results["successes"]:
                emailer.send_emails(
                    [], 
                    notification, 
                    success=True, 
                    successes=results["successes"], 
                    subject="success response fromthe cloudzen",
                    invoices=results["success_objects"],
                    file_prefix="success"
                )
                logger.info(f"Sent cloud success email for {cfg}")
            
            if results["errors"]:
                emailer.send_emails(
                    results["errors"], 
                    notification, 
                    success=False, 
                    subject="error resposnse from the cloudzen",
                    invoices=results["error_objects"],
                    file_prefix="error"
                )
                logger.info(f"Sent cloud error email for {cfg}")

    if session and all_errors:
        distinct_errors = list(dict.fromkeys(all_errors))
        CachedData.add_cached_data(datatype=CachedData.DT_PURCHASE_ERRORS, data_json=distinct_errors, group=session)

    return all_errors


