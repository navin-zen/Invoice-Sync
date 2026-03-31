"""
Specification of Purchase invoice fields needed for DB column mapper
"""

import itertools

from invoicing.utils.utils import ALLOWED_TAX_RATES

from cz_utils.text_utils import squeeze_space


def base36encode(number, alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError("number must be an integer")

    base36 = ""
    sign = ""

    if number < 0:
        sign = "-"
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def base36decode(number):
    return int(number, 36)


def section(name, description, fields):
    return {
        "name": name,
        "description": description,
        "fields": fields,
    }


def field(name, displayName, helpText=None, required=False):
    return {
        "name": name,
        "displayName": displayName,
        "help": helpText,
        "required": required,
    }


NUM_ITEM_ATTRIBUTES = 10

NUM_INVOICE_ATTRIBUTES = 24

NUM_FK_FIELDS = 5

PURCHASE_SCHEMA_SPEC = {
    "sections": [
        section(
            "Document Details",
            "Details at the level of an Invoice, Credit Note, or Debit Note.",
            [
                field(
                    "DocDtls.Typ",
                    "Document Type",
                    helpText=squeeze_space(
                        "The type of Document: INV for Invoice, CRN for Credit Note, and DBN for Debit Note. "
                        "If not provided, the document will be considered as an Invoice."
                    ),
                ),
                field("DocDtls.Dt", "Document Date", "", required=True),
                field("DocDtls.No", "Document Number", "", required=True),
                field(
                    "TranDtls.SupTyp",
                    "Nature of Transaction",
                    helpText="The nature of the transaction. R or B2B for Regular, etc.",
                ),
                field(
                    "TranDtls.RegRev",
                    "Reverse Charge",
                    helpText="Whether purchase is made under Reverse Charge (Y/N). The default value is N.",
                ),
                field(
                    "TranDtls.IgstOnIntra",
                    "IGST on Intra-State",
                    helpText=squeeze_space(
                        "Indicates the supply is intra state but chargeable to IGST (Y/N).The default value is N."
                    ),
                ),
                field(
                    "BuyerDtls.Pos",
                    "Place of Supply",
                    helpText=squeeze_space(
                        "The Place of Supply of this Document. "
                        "If not provided, the Gateway GSTIN State will be used."
                    ),
                ),
            ],
        ),
        section(
            "Supplier Details",
            "Supplier Details",
            [
                field(
                    "SellerDtls.Gstin",
                    "Supplier GSTIN",
                    "The GSTIN of the Supplier",
                    required=True,
                ),
                field(
                    "SellerDtls.LglNm",
                    "Supplier Legal Name",
                    "Legal Name of the Supplier",
                ),
                field(
                    "SellerDtls.TrdNm",
                    "Supplier Trade Name",
                    "Trade Name of the Supplier",
                ),
                field("SellerDtls.Addr1", "Supplier Address (Line 1)", ""),
                field("SellerDtls.Addr2", "Supplier Address (Line 2)", ""),
                field(
                    "SellerDtls.Loc",
                    "Supplier Locality",
                    "Usually the city or district of the Supplier",
                ),
                field(
                    "SellerDtls.Pin",
                    "Supplier Pincode",
                    "Pincode of the Supplier",
                ),
            ],
        ),
        section(
            "Gateway GSTIN Details (Buyer)",
            "Buyer Details (The Portal GSTIN)",
            [
                field(
                    "BuyerDtls.Gstin",
                    "Portal GSTIN",
                    "The GSTIN of the Portal/Recipient",
                    required=True,
                ),
                field(
                    "BuyerDtls.LglNm",
                    "Portal Legal Name",
                    "Legal Name of the Recipient",
                ),
                field("BuyerDtls.Addr1", "Portal Address (Line 1)", ""),
                field(
                    "BuyerDtls.Loc",
                    "Portal Locality",
                    "Usually the city or district of the Recipient",
                ),
                field(
                    "BuyerDtls.Pin",
                    "Portal Pincode",
                    "Pincode of the Recipient",
                ),
            ],
        ),
        section(
            "Line Items (Important details)",
            "Line Items",
            [
                field(
                    "LineItem.HsnCd",
                    "HSN/SAC",
                    required=True,
                ),
                field(
                    "LineItem.PrdDesc",
                    "Item Description",
                    required=True,
                ),
                field("LineItem.Qty", "Quantity", ""),
                field(
                    "LineItem.Unit",
                    "Unit / UQC",
                ),
                field(
                    "LineItem.UnitPrice",
                    "Unit Price",
                ),
                field(
                    "LineItem.TotAmt",
                    "Gross Amount",
                ),
                field(
                    "LineItem.AssAmt",
                    "Taxable Value",
                    required=True,
                ),
                field(
                    "LineItem.GstRt",
                    "GST Rate (%)",
                    squeeze_space(
                        "The GST Rate (%) applicable to this item. Valid rates are {}".format(
                            ", ".join(map(str, ALLOWED_TAX_RATES))
                        )
                    ),
                    required=True,
                ),
                field(
                    "LineItem.IgstAmt",
                    "IGST Amount",
                ),
                field(
                    "LineItem.CgstAmt",
                    "CGST Amount",
                ),
                field(
                    "LineItem.SgstAmt",
                    "SGST Amount",
                ),
                field(
                    "LineItem.CesAmt",
                    "Cess Amount",
                ),
                field(
                    "LineItem.CesNonAdvlAmt",
                    "Cess (Non-Advol) Amount",
                ),
            ],
        ),
        section(
            "Metadata and References",
            "Additional Information for internal Use",
            [
                field("RecordDate", "Record Date", "Date on which record was created in local system"),
                field("DocIdentifier", "Document Identifier", "Internal Identifier for the document"),
                field("GlAccountId", "GL Account ID", "General Ledger Account Identifier"),
                field("Department", "Department", "The Department or Profit Center to help organize your invoices"),
                field(
                    "RefDtls.InvRm",
                    "Remarks/Note",
                    "",
                ),
            ],
        ),
        section(
            "Invoice Totals (Optional)",
            "If not provided, GSTZen will calculate the totals from the item details",
            [
                field("ValDtls.AssVal", "Taxable Amount (Total)", ""),
                field("ValDtls.IgstVal", "IGST Amount (Total)", ""),
                field("ValDtls.CgstVal", "CGST Amount (Total)", ""),
                field("ValDtls.SgstVal", "SGST Amount (Total)", ""),
                field("ValDtls.CesVal", "Cess Amount (Total)", ""),
                field("ValDtls.TotInvVal", "Invoice Total", ""),
            ],
        ),
        section(
            "Status Write Back Specification",
            "For database backend only, details of how to write back the Sync Status and other details back to the database",
            [
                field(
                    "WriteBackInfo.TableName",
                    "Database Table Name",
                    "The name of the database table to write sync status information",
                ),
                field(
                    "WriteBackInfo.Fields.Timestamp",
                    "Timestamp field name",
                    "The name of the field containing the timestamp of the record",
                ),
                field(
                    "WriteBackInfo.Fields.SyncStatus",
                    "Sync Status field name",
                    "The name of the field containing the Sync Status (Uploaded/Error) of the Invoice",
                ),
                field(
                    "WriteBackInfo.Fields.SyncMessage",
                    "Sync Message field name",
                    "The name of the field containing the success or error message from the sync process",
                ),
            ]
            + list(
                itertools.chain.from_iterable(
                    (
                        field(
                            f"WriteBackInfo.Fk.{i}.Field",
                            f"Foreign Key to Invoice Table (Field {i + 1})",
                            "The name of the field that contains the Foreign Key to the invoices table",
                        ),
                        field(
                            f"WriteBackInfo.Fk.{i}.Type",
                            f"Foreign Key to Invoice Table (Type {i + 1})",
                            "The type of the Foreign Key field: date, str, etc.",
                        ),
                        field(
                            f"WriteBackInfo.Fk.{i}.Value",
                            f"Foreign Key to Invoice Table (Value {i + 1})",
                            "The internal path to the value of the Foreign Key (e.g., DocDtls.No)",
                        ),
                    )
                    for i in range(NUM_FK_FIELDS)
                )
            ),
        ),
    ],
    "exclusive_or": [],
    "all_or_none": [],
}

COLUMN_MAPPING_DEFAULTS = {
    "LineItem.Unit": {"type": "fixed", "value": "OTH"},
    "LineItem.Qty": {"type": "fixed", "value": "1"},
}

def get_field_to_human_name_mapping():
    mapping = {}
    for section in PURCHASE_SCHEMA_SPEC["sections"]:
        for field in section["fields"]:
            mapping[field["name"]] = field["displayName"]
    return mapping

FIELD_TO_HUMAN_NAME_MAPPING = get_field_to_human_name_mapping()


