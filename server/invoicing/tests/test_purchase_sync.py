import json
import uuid
from datetime import datetime
from unittest import mock

import responses
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from invoicing.models import CachedData, Configuration, GstIn, PurchaseInvoice
from invoicing.utils.api.common import get_or_create_gstin
from seed_data import populate_states

PURCHASE_SAMPLE_DATA = [
    {
        "DocDtls": {
            "Typ": "INV",
            "No": "PUR/23-24/001",
            "Dt": "01-10-2023"
        },
        "BuyerDtls": {
            "Gstin": "29AAFCC9980MZZT",
            "LglNm": "Buying Entity",
            "Addr1": "Bangalore",
            "Loc": "Bangalore",
            "Pin": 560001,
            "Stcd": "29"
        },
        "SellerDtls": {
            "Gstin": "27AAACC4309B1ZC",
            "LglNm": "Supplying Entity",
            "Addr1": "Mumbai",
            "Loc": "Mumbai",
            "Pin": 400001,
            "Stcd": "27"
        },
        "ItemList": [
            {
                "SlNo": "1",
                "PrdDesc": "Consultancy Services",
                "HsnCd": "9983",
                "Qty": 1,
                "Unit": "NOS",
                "UnitPrice": 1000,
                "TotAmt": 1000,
                "AssAmt": 1000,
                "GstRt": 18,
                "IgstAmt": 180
            }
        ],
        "ValDtls": {
            "AssVal": 1000,
            "IgstVal": 180,
            "CgstVal": 0,
            "SgstVal": 0,
            "CesVal": 0,
            "TotInvVal": 1180
        }
    }
]

class PurchaseSyncTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        populate_states.run()
        cls.gstin = get_or_create_gstin("29AAFCC9980MZZT", "Test Entity")

        cls.config = Configuration.objects2.create(site_name="Test Config")
        cls.config.metadata = {
            "datasource": {
                "type": "db:mssql",
                "config": {
                    "hostname": "localhost",
                    "database": "test_db",
                    "username": "sa",
                    "password": "password"
                }
            },
            "datamapping": {
                "table_name": "purchases",
                "details": {}
            }
        }
        cls.config.save()

    def test_sync_purchase_start_session(self):
        url = reverse("invoicing:sync_purchase_invoices_start_session")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_uuid", data)
        self.assertTrue(CachedData.objects.filter(uuid=data["session_uuid"], datatype=CachedData.DT_PURCHASE_SESSION_MARKER).exists())

    def test_purchase_json_post(self):
        url = reverse("invoicing:purchase_json_post")
        payload = PURCHASE_SAMPLE_DATA[0]

        response = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], 1)
        self.assertIn("uuid", data)

        # Verify it exists in local DB
        pi = PurchaseInvoice.objects.get(uuid=data["uuid"])
        self.assertEqual(pi.number, "PUR/23-24/001")
        self.assertEqual(pi.purchase_status, PurchaseInvoice.PIS_CANDIDATE)

    @responses.activate
    def test_sync_purchase_in_progress(self):
        # 1. Start Session
        start_url = reverse("invoicing:sync_purchase_invoices_start_session")
        session_uuid = self.client.post(start_url).json()["session_uuid"]

        # 2. Mock DB Data for Fetcher
        with mock.patch("invoicing.utils.purchase_invoice_generation.get_data_from_db") as mock_get_db:
            # Flattened structure usually expected by fetcher
            mock_get_db.return_value = [
                {
                    "BuyerDtls.Gstin": "29AAFCC9980MZZT",
                    "SellerDtls.Gstin": "27AAACC4309B1ZC",
                    "DocDtls.No": "PUR-002",
                    "DocDtls.Dt": "2023-11-01",
                    "DocDtls.Typ": "INV",
                    "LineItem.HsnCd": "9983",
                    "LineItem.PrdDesc": "Test Service",
                    "LineItem.AssAmt": 5000,
                    "LineItem.GstRt": 18
                }
            ]

            # 3. Mock Cloud API Response
            responses.add(
                responses.POST,
                "http://localhost:8000/~gstzen/a/post-purchase-data/purchase-json/",
                json={"status": 1, "message": "Uploaded successfully"},
                status=200
            )

            # 4. Trigger Sync
            sync_url = reverse("invoicing:sync_purchase_invoices", args=[session_uuid])
            response = self.client.post(sync_url)
            self.assertEqual(response.status_code, 200)

            # 5. Verify local database updates
            pi = PurchaseInvoice.objects.get(number="PUR-002")
            self.assertEqual(pi.purchase_status, PurchaseInvoice.PIS_UPLOADED)

            # 6. Check Status View
            status_url = reverse("invoicing:sync_purchase_invoices_status", args=[session_uuid])
            status_response = self.client.get(status_url)
            self.assertEqual(status_response.json()["completed"], True)

    def test_purchase_sync_error_handling(self):
        # Test what happens when cloud returns an error
        pi = PurchaseInvoice.objects.create(
            gstin=self.gstin,
            number="ERR-001",
            date=timezone.now().date(),
            financial_year=timezone.now().date(),
            doctype=PurchaseInvoice.DT_INVOICE,
            docsubtype=PurchaseInvoice.DST_NOT_APPLICABLE,
            purchase_status=PurchaseInvoice.PIS_CANDIDATE,
            ctin="27AAACC4309B1ZC",
            purchase_json={"DocDtls": {"No": "ERR-001"}}
        )

        from invoicing.utils.purchase_gstzen_cloud import post_purchase_to_gstzen

        with responses.RequestsMock() as rsps:
            rsps.add(
                responses.POST,
                "http://localhost:8000/~gstzen/a/post-purchase-data/purchase-json/",
                json={"status": 0, "message": "Invalid GSTIN"},
                status=400
            )

            post_purchase_to_gstzen(pi)

            pi.refresh_from_db()
            self.assertEqual(pi.purchase_status, PurchaseInvoice.PIS_ERROR)
            self.assertEqual(pi.purchase_response["message"], "Invalid GSTIN")

    def test_sync_purchase_missing_gstin(self):
        # Simulate an invoice in the source that belongs to a GSTIN NOT in our system
        start_url = reverse("invoicing:sync_purchase_invoices_start_session")
        session_uuid = self.client.post(start_url).json()["session_uuid"]

        with mock.patch("invoicing.utils.purchase_invoice_generation.get_data_from_db") as mock_get_db:
            mock_get_db.return_value = [
                {
                    "BuyerDtls.Gstin": "99ABCDE1234F1ZA", # NOT in setUpTestData
                    "SellerDtls.Gstin": "27AAACC4309B1ZC",
                    "DocDtls.No": "MISSING-GSTIN-001",
                    "DocDtls.Dt": "2023-11-01",
                    "DocDtls.Typ": "INV",
                    "LineItem.HsnCd": "9983",
                    "LineItem.PrdDesc": "Test",
                    "LineItem.AssAmt": 100,
                    "LineItem.GstRt": 18
                }
            ]

            sync_url = reverse("invoicing:sync_purchase_invoices", args=[session_uuid])
            response = self.client.post(sync_url)
            self.assertEqual(response.status_code, 200)

            # Verify error was captured
            status_url = reverse("invoicing:sync_purchase_invoices_status", args=[session_uuid])
            status_response = self.client.get(status_url)
            errors = status_response.json()["errors"]
            self.assertTrue(any("not configured in GSTZen" in str(e) for e in errors))


