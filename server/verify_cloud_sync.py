
import os
import django
import sys
from unittest.mock import patch, MagicMock

# Add the current directory to sys.path to ensure imports work
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from einvoicing.models import GstIn, PurchaseInvoice
from einvoicing.utils.purchase_json_to_db import PurchaseUploader
from einvoicing.utils.purchase_gstzen_cloud import post_purchase_to_gstzen

def verify_cloud_sync():
    print("Starting Cloud Sync verification (Mocked)...")

    # Get a GSTIN to use for testing
    gstin = GstIn.objects2.all().first()
    if not gstin:
        print("Error: No GSTIN found in database.")
        return

    # Create a candidate invoice
    pj = {"DocDtls": {"No": "TEST-SYNC-001", "Dt": "09/03/2026", "Typ": "INV"}, "BuyerDtls": {"Gstin": gstin.gstin}, "SellerDtls": {"Gstin": "1234"}}
    invoice = PurchaseUploader.create_or_update_purchase_invoice(gstin, pj)
    invoice.purchase_status = PurchaseInvoice.PIS_CANDIDATE
    invoice.save()

    print(f"Created candidate invoice: {invoice.number}")

    # Mock success response
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": 1, "message": "Success", "uuid": str(invoice.uuid)}
        mock_post.return_value = mock_response

        print("Testing successful post...")
        post_purchase_to_gstzen(invoice)

        invoice.refresh_from_db()
        assert invoice.purchase_status == PurchaseInvoice.PIS_UPLOADED
        print("Success status verification passed.")

    # Mock error response
    invoice.purchase_status = PurchaseInvoice.PIS_CANDIDATE
    invoice.save()

    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"status": 0, "message": "Invalid GSTIN"}
        mock_post.return_value = mock_response

        print("Testing error post...")
        post_purchase_to_gstzen(invoice)

        invoice.refresh_from_db()
        assert invoice.purchase_status == PurchaseInvoice.PIS_ERROR
        assert invoice.purchase_response.get("message") == "Invalid GSTIN"
        print("Error status verification passed.")

    # Cleanup
    invoice.delete()
    print("Cloud Sync verification SUCCESSFUL.")

if __name__ == "__main__":
    verify_cloud_sync()
