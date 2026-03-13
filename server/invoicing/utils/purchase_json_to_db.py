"""
Save Purchase JSON data into our database
"""

import uuid
import logging
from django.db import transaction
from django.http.response import JsonResponse
from invoicing.models import PurchaseInvoice, GstIn
from invoicing.utils.utils import financial_year, fy_range
from invoicing.utils.validate_fields import validate_invnumber
from pygstn.utils import json

from cz_utils.dateparse import parse_date
from cz_utils.utils import merge_dicts

logger = logging.getLogger(__name__)

class PurchaseAlreadyUploaded(ValueError):
    pass

class PurchaseUploader:
    INVOICE_NUMBER_STRING = "No"
    INVOICE_DATE_STRING = "Dt"
    DATE_FORMATS = None

    @classmethod
    def get_purchase_invoice_from_json(cls, purchase_json):
        """
        Get the Full Purchase Invoice details from JSON Data
        """
        return purchase_json

    @classmethod
    def get_docdtls_from_json(cls, purchase_json):
        """
        Get the Document Level details from the Purchase JSON Data
        """
        return purchase_json.get("DocDtls", {})

    @classmethod
    def gstin_string_from_payload(cls, purchase_json):
        """
        Get the Buyer GSTIN Number (Portal GSTIN) from the payload
        """
        return purchase_json.get("BuyerDtls", {}).get("Gstin", "")

    @classmethod
    def gstin_obj_for_request(cls, purchase_json):
        gstin_string = cls.gstin_string_from_payload(purchase_json)
        gstin = GstIn.objects2.filter(gstin=gstin_string).first()
        return gstin

    @classmethod
    def lookup_existing_invoice(cls, gstin, pj):
        """
        Lookup existing purchase invoice in our DB
        """
        doc_dtls = cls.get_docdtls_from_json(pj)
        invoice_number = doc_dtls.get(cls.INVOICE_NUMBER_STRING, "")
        if "OF" in invoice_number.upper():
            invoice_number = invoice_number.upper().split("OF")[0].strip()
        invoice_number = invoice_number[:16].strip()
        invoice_number = validate_invnumber(invoice_number)
        invoice_date = parse_date(doc_dtls.get(cls.INVOICE_DATE_STRING).split()[0], formats=cls.DATE_FORMATS)
        (fy, _) = financial_year(invoice_date)

        # Purchase invoices are unique across (gstin, ctin, doctype, financial_year, number)
        # However, for uploader, we use the same doc type logic
        (doctype, _) = cls.parse_doctype_subtype(doc_dtls)
        ctin = pj.get("SellerDtls", {}).get("Gstin", "")

        invoice = PurchaseInvoice.objects2.filter(
            gstin=gstin,
            ctin=ctin,
            financial_year=fy,
            doctype=doctype,
            number=invoice_number
        ).first()

        if not invoice:
            return None
        return invoice

    @classmethod
    def parse_doctype_subtype(cls, DocDtls):
        """
        Parse and return (doctype, docsubtype) 2-tuple from JSON's DocDtls.
        """
        Typ = DocDtls.get("Typ")
        if Typ == "INV":
            doctype = PurchaseInvoice.DT_INVOICE
            docsubtype = PurchaseInvoice.DST_NOT_APPLICABLE
        elif Typ in ["CRN", "DBN"]:
            doctype = PurchaseInvoice.DT_NOTE
            if Typ == "CRN":
                docsubtype = PurchaseInvoice.DST_CREDIT_NOTE
            elif Typ == "DBN":
                docsubtype = PurchaseInvoice.DST_DEBIT_NOTE
        else:
            # Default to Invoice
            doctype = PurchaseInvoice.DT_INVOICE
            docsubtype = PurchaseInvoice.DST_NOT_APPLICABLE
        return (doctype, docsubtype)

    @classmethod
    def create_or_update_purchase_invoice(cls, gstin, pj):
        """
        Create or Update PurchaseInvoice record
        """
        if not gstin:
            raise ValueError("Taxpayer GSTIN is not found in GSTZen")

        existing_invoice = cls.lookup_existing_invoice(gstin, pj)

        doc_dtls = cls.get_docdtls_from_json(pj)
        invoice_date = parse_date(doc_dtls.get(cls.INVOICE_DATE_STRING))
        (doctype, docsubtype) = cls.parse_doctype_subtype(doc_dtls)
        invoice_number = doc_dtls.get(cls.INVOICE_NUMBER_STRING, "")
        if "OF" in invoice_number.upper():
            invoice_number = invoice_number.upper().split("OF")[0].strip()
        invoice_number = invoice_number[:16].strip()

        invoice_number = validate_invnumber(invoice_number)

        if existing_invoice:
            invoice = existing_invoice
        else:
            invoice = PurchaseInvoice(
                gstin=gstin,
                doctype=doctype,
                financial_year=fy_range(invoice_date)[0],
                number=invoice_number,
                upload_uuid=uuid.uuid4()
            )

        invoice.docsubtype = docsubtype
        invoice.date = invoice_date
        invoice.ctin = pj.get("SellerDtls", {}).get("Gstin", "")
        invoice.purchase_status = PurchaseInvoice.PIS_CANDIDATE
        invoice.purchase_json = pj

        # Add metadata if present (Department, GL Account, etc.)
        metadata = invoice.metadata or {}
        if "DocIdentifier" in pj:
            metadata["DocumentIdentifier"] = pj["DocIdentifier"]
        if "GlAccountId" in pj:
            metadata["GlAccountId"] = pj["GlAccountId"]
        if "Department" in pj:
            metadata["Department"] = pj["Department"]
        invoice.metadata = metadata

        invoice.full_clean()
        invoice.save()
        return invoice

    @classmethod
    def handle_dispatch(cls, view, request, *args, **kwargs):
        """
        Handle the dispatch() method of the view
        """
        try:
            view.purchase_data = json.loads(request.body)
        except ValueError:
            return JsonResponse({"status": 0, "message": "Invalid JSON input"}, status=400)

        view.gstin = cls.gstin_obj_for_request(view.purchase_data)
        if not view.gstin:
            gstin_string = cls.gstin_string_from_payload(view.purchase_data)
            return JsonResponse(
                {"status": 0, "message": f"The requested GSTIN ({gstin_string}) is not present in your GSTZen account."},
                status=404,
            )
        return None

    @classmethod
    def handle_post(cls, gstin, pj, kwargs):
        try:
            with transaction.atomic():
                invoice = cls.create_or_update_purchase_invoice(gstin, pj)

            return JsonResponse({
                "status": 1,
                "message": "Purchase invoice saved successfully",
                "uuid": str(invoice.uuid)
            })
        except Exception as ex:
            logger.exception("Error in PurchaseUploader.handle_post")
            return JsonResponse({"status": 0, "message": str(ex)}, status=400)


