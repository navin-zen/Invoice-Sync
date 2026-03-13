"""
Construct the Integration like Tally,SAP JSON data as Invoicing JSON as per Specification
"""

from datetime import datetime

from invoicing.utils.utils import to_decimal_round2


class InvoicingJsonConstructor:
    """
    Construct the Invoicing JSON

    This is the base of Tally / SAP integrations
    """

    @classmethod
    def get_lineitems_from_json(cls, data):
        """
        :params: data - Post data from the Integrations
        """
        return data.get("lineitems", {}).get("lineitem", [])

    @classmethod
    def get_invoice_metadata(cls, dt, field, gstin_string):
        data = {
            "TrdNm": dt.get(field, {}).get("TrdNm", ""),
            "Bno": dt.get(field, {}).get("Bno", ""),
            "Bnm": dt.get(field, {}).get("Bnm", ""),
            "Flno": dt.get(field, {}).get("Flno", ""),
            "Loc": dt.get(field, {}).get("Loc", ""),
            "Dst": dt.get(field, {}).get("Dst", ""),
            "Pin": dt.get(field, {}).get("Pin", ""),
            "Stcd": dt.get(field, {}).get("Stcd", ""),
            "Ph": dt.get(field, {}).get("Ph", ""),
            "Em": dt.get(field, {}).get("Em", ""),
        }
        data.update({"Gstin": dt.get(gstin_string)})
        return data

    @classmethod
    def invoiceentry_to_json(cls, idx, ie):
        # For our ready reference, we have copied the fields from the
        # schema along with type and description
        return {
            "SlNo": str(idx),
            "GstRt": ie.get("RT"),
            "Barcde": ie.get("Barcde"),
            "HsnCd": ie.get("HSNSAC"),
            "PrdDesc": ie.get("DESC"),
            "TotAmt": ie.get("TXVAL"),
            "AssAmt": ie.get("TXVAL"),
            "CsAmt": ie.get("CSAMT"),
            "Unit": ie.get("UQC"),
            "Qty": ie.get("QTY"),
            "FreeQty": to_decimal_round2(ie.get("FreeQty", 0)) or 0,
            "BatchDtls": {
                "Nm": ie.get("BchDtls", {}).get("Nm", ""),
                "ExpDt": ie.get("BchDtls", {}).get("ExpDt", ""),
                "WrDt": ie.get("BchDtls", {}).get("WrDt", ""),
            },
        }

    @classmethod
    def as_json(cls, data):
        """
        Convert Tally/SAP JSON into Invoicing JSON format

        :params: data - Tally/SAP data from the post url
        """
        DispatchDtls = data.get("DispatchDtls", {})
        ShipDtls = data.get("ShipDtls", {})
        lineitems = cls.get_lineitems_from_json(data)
        ItemList = [cls.invoiceentry_to_json(idx, ie) for (idx, ie) in enumerate(lineitems)]
        data = {
            "TranDtls": {"RegRev": data.get("RCHRG")},
            "DocDtls": {
                "Typ": data.get("Inv_Type", "INV"),
                "No": data.get("INUM"),
                "Dt": datetime.strptime(data.get("IDT").split()[0], "%m/%d/%Y").strftime("%d/%m/%Y"),
                "Rchrg": data.get("RCHRG"),
            },
            "SellerDtls": cls.get_invoice_metadata(data, field="SellerDtls", gstin_string="GSTIN"),
            "BuyerDtls": cls.get_invoice_metadata(data, field="BuyerDtls", gstin_string="CTIN"),
            "DispatchDtls": DispatchDtls,
            "ShipDtls": ShipDtls,
            "ItemList": ItemList,
        }
        return data
