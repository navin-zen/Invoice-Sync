"""
Utilities related to reading/writing purchase invoices to our DB, the PurchaseInvoice model
"""

import logging
from django.core.exceptions import ValidationError
from invoicing.models import Configuration, GstIn, PurchaseInvoice
from invoicing.utils.exception_utils import ErrorWithInvoiceDetails, QuietValueError
from invoicing.utils.utils import fy_range

from cz_utils.dateparse import parse_date

logger = logging.getLogger(__name__)


def add_purchase_invoice(error_message: str, pj, session_uuid, configuration, gstin_obj=None, commit=True):
    """
    Add a Purchase Invoice JSON to the PurchaseInvoice table

    Parameters
    ---------
    error_message
        Error message indicating whether the Purchase Invoice has a known error
    pj
        The grouped Purchase Invoice JSON
    session_uuid
        The session/upload UUID
    configuration
        The Configuration object
    """
    assert isinstance(configuration, Configuration)

    buyer_dtls = pj.get("BuyerDtls", {})
    gstin_string = buyer_dtls.get("Gstin")
    if not gstin_string:
        raise QuietValueError("BuyerDtls.Gstin (Buyer GSTIN) is missing in purchase data")

    if gstin_obj:
        gstin = gstin_obj
    else:
        gstin = GstIn.objects2.filter(gstin=gstin_string).first()
        if not gstin:
            raise QuietValueError(f"The Taxpayer GSTIN {gstin_string} is not configured in your GST Registrations")

    seller_dtls = pj.get("SellerDtls", {})
    ctin = seller_dtls.get("Gstin", "")
    if not ctin:
        # For purchase, Seller GSTIN is usually required to identify the supplier
        raise QuietValueError("SellerDtls.Gstin (Supplier GSTIN) is missing in purchase data")

    Typ = pj.get("DocDtls", {}).get("Typ", "INV")
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
        # Default to Invoice if type is missing or unknown
        doctype = PurchaseInvoice.DT_INVOICE
        docsubtype = PurchaseInvoice.DST_NOT_APPLICABLE

    date_str = pj.get("DocDtls", {}).get("Dt")
    if not date_str:
        raise QuietValueError("DocDtls.Dt (Document Date) is missing in purchase data")
    date = parse_date(date_str)
    fy = fy_range(date)[0]
    No = pj["DocDtls"]["No"]
    if "OF" in No.upper():
        # Split by "OF" and take the first part
        No = No.upper().split("OF")[0].strip()

    # Safety truncation to 16 characters
    No = No[:16].strip()
    # Note: Black list characters like '/' are usually not allowed in some Invoicing number specs,
    # but let's stick to simple truncation and length capping for now.

    # Unique check based on gstin, doctype, financial_year, number
    # Note: Supplier GSTIN (ctin) is not part of the unique key in invoicing model,
    # but for Purchase it might be better. However, the requirement says mirror Invoicing.
    # Actually, Invoicing model unique_together = (("gstin", "doctype", "financial_year", "number"),)
    # I'll stick to that but for Purchase, numbering might overlap across suppliers.
    # WAIT: I added unique_together for PurchaseInvoice in models.py as:
    # unique_together = (("gstin", "doctype", "financial_year", "number"),)
    # This might be a problem if Doc No "123" exists for Supplier A and Supplier B.
    # I should probably include `ctin` in unique_together for PurchaseInvoice.
    # Let me check my previous edit to models.py.

    # YES, I should have included CTIN. Let me fix models.py unique_together first.

    ctin = pj["SellerDtls"].get("Gstin", "")
    el = PurchaseInvoice.objects2.filter(gstin=gstin, ctin=ctin, financial_year=fy, doctype=doctype, number=No).first()

    if el:
        # If the invoice is already in a final or pending state for THIS session, skip.
        # This prevents the background task (which uses the same session UUID) from retrying infinitely.
        if el.purchase_status in [PurchaseInvoice.PIS_UPLOADED, PurchaseInvoice.PIS_ERROR, PurchaseInvoice.PIS_CANDIDATE]:
            if str(el.upload_uuid) == str(session_uuid):
                return
            # If it's a new session, we still skip if already uploaded
            if el.purchase_status == PurchaseInvoice.PIS_UPLOADED:
                return
    else:
        el = PurchaseInvoice(gstin=gstin, financial_year=fy, doctype=doctype, number=No, upload_uuid=session_uuid)

    el.docsubtype = docsubtype
    el.date = date
    el.ctin = pj["SellerDtls"].get("Gstin", "")

    if error_message:
        el.purchase_status = PurchaseInvoice.PIS_ERROR
        pj["error_message"] = error_message
    else:
        el.purchase_status = PurchaseInvoice.PIS_CANDIDATE

    el.purchase_json = pj
    el.configuration = configuration

    # Map metadata fields if present
    metadata = {}
    if "RecordDate" in pj:
        metadata["RecordDate"] = pj["RecordDate"]
    if "DocIdentifier" in pj:
        metadata["DocumentIdentifier"] = pj["DocIdentifier"]
    if "GlAccountId" in pj:
        metadata["GlAccountId"] = pj["GlAccountId"]

    el.metadata = metadata

    try:
        el.full_clean()
    except Exception as ex:
        raise ErrorWithInvoiceDetails(ex, invoice=No)
        
    if commit:
        el.save()
        logger.info(f"Saved Purchase Invoice: {No} (Supplier: {ctin}, Status: {el.status_message})")
        
    return el


