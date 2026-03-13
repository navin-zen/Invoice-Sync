import datetime
import operator
from decimal import Decimal
from itertools import groupby

import sqlalchemy
from einvoicing.utils.utils import fy_range
from pygstn.utils import json
from sqlalchemy import literal, literal_column

from cz_utils.decimal_utils import cz_round2
from cz_utils.itertools_utils import unflatten_dict
from cz_utils.json_utils import JSONEncoder


def add_computed_amounts(einvoice, lineitem, buyerdtls, docdtls):
    """
    Add compute tax rate and amounts to an E-Invoice's line item
    """
    is_igst = is_intra_state(buyerdtls["Gstin"], False, docdtls["Typ"], lineitem["PlaceOfSupply"])
    lineitem.update(tax_rate_and_amounts(lineitem["AssAmt"], lineitem["GstRt"], is_igst))
    lineitem.pop("GstRt")
    return lineitem


def add_fy(row):
    fy = fy_range(row["DocDtls.Dt"])[0]
    row["fy"] = fy
    return row


def fetch_invoices(engine):
    metadata = sqlalchemy.MetaData(bind=engine)
    table = sqlalchemy.Table("VW_TEST_INVOICE", metadata, autoload=True, autoload_with=engine)
    query = sqlalchemy.select(
        [
            table.c["Receipient_Name"].label("BuyerDtls.TrdNm"),
            table.c["Receipient_GSTIN"].label("BuyerDtls.Gstin"),
            table.c["Receipient_State_code"].label("BuyerDtls.Stcd"),
            table.c["Consignee_Name"].label("SellerDtls.TrdNm"),
            table.c["Consignee_GSTIN"].label("SellerDtls.Gstin"),
            table.c["Consignee_State_code"].label("SellerDtls.Stcd"),
            table.c["Consignee_Address"].label("SellerDtls.Loc"),
            table.c["Invoice_No"].label("DocDtls.No"),
            table.c["Invoice_Date"].label("DocDtls.Dt"),
            table.c["Item_Alias"].label("LineItem.PrdNm"),
            table.c["Item_Description"].label("LineItem.PrdDesc"),
            table.c["HSNCODE"].label("LineItem.HsnCd"),
            table.c["Unit"].label("LineItem.Unit"),
            table.c["Quantity"].label("LineItem.Qty"),
            table.c["Unit_Rate"].label("LineItem.UnitPrice"),
            table.c["Trade_Discount"].label("LineItem.Discount"),
            literal_column("18").label("LineItem.GstRt"),
            literal_column("0").label("LineItem.CessNonAdval"),
            literal_column("0").label("LineItem.AssAmt"),
            literal_column("0").label("LineItem.TotAmt"),
            literal_column("0").label("LineItem.StateCes"),
            literal_column("0").label("LineItem.OthChrg"),
            literal_column("0").label("LineItem.FreeQty"),
            literal("INV").label("DocDtls.Typ"),
            table.c["Receipient_State_code"].label("LineItem.PlaceOfSupply"),
        ]
    )
    rows = [dict(row) for row in engine.execute(query)]
    transformed_rows = [add_fy(transform_row(r)) for r in rows]

    einvoices = []
    for key, group in groupby(
        transformed_rows, operator.itemgetter("SellerDtls.Gstin", "fy", "DocDtls.Typ", "DocDtls.No")
    ):
        group = list(group)
        nested_group = [unflatten_dict(r) for r in group]
        einvoice = nested_group[0]
        einvoice["ItemList"] = [
            add_computed_amounts(einvoice, i["LineItem"], i["BuyerDtls"], i["DocDtls"]) for i in nested_group
        ]
        del einvoice["LineItem"]
        del einvoice["fy"]
        einvoices.append(einvoice)

    for row in einvoices:
        pass

    print(json.dumps(einvoices, cls=JSONEncoder))


class Transformations:
    @classmethod
    def excelstr2date(cls, v):
        return datetime.date(1900, 1, 1) + datetime.timedelta(days=int(v))

    @classmethod
    def str2int(cls, v):
        return int(v)

    @classmethod
    def totamt(cls, unitprice, qty):
        return unitprice * qty

    @classmethod
    def assamt(cls, unitprice, qty, discount, othchrg):
        return (unitprice * qty) - discount + othchrg


def is_intra_state(supplier_gstin, is_exim, invoice_type, pos):
    if is_exim:
        return False
    if invoice_type.upper() in ["SEWP", "SEWOP"]:
        return False
    return int(supplier_gstin[:2]) == int(pos)


def tax_rate_and_amounts(taxable_value, gst_rate, is_igst):
    if is_igst:
        (IgstRt, CgstRt, SgstRt) = (gst_rate, 0, 0)
    else:
        IgstRt = 0
        CgstRt = SgstRt = gst_rate / Decimal(2)
    return {
        "IgstRt": IgstRt,
        "CgstRt": CgstRt,
        "SgstRt": SgstRt,
        "IgstAmt": cz_round2((taxable_value * IgstRt) / Decimal(100)),
        "CgstAmt": cz_round2((taxable_value * CgstRt) / Decimal(100)),
        "SgstAmt": cz_round2((taxable_value * SgstRt) / Decimal(100)),
    }


def transform_row(r):
    r.update(
        {
            "DocDtls.Dt": Transformations.excelstr2date(r["DocDtls.Dt"]),
            "BuyerDtls.Stcd": Transformations.str2int(r["BuyerDtls.Stcd"]),
            "SellerDtls.Stcd": Transformations.str2int(r["SellerDtls.Stcd"]),
            "LineItem.PlaceOfSupply": Transformations.str2int(r["LineItem.PlaceOfSupply"]),
            "LineItem.TotAmt": Transformations.totamt(r["LineItem.UnitPrice"], r["LineItem.Qty"]),
            "LineItem.AssAmt": Transformations.assamt(
                r["LineItem.UnitPrice"], r["LineItem.Qty"], r["LineItem.Discount"], r["LineItem.OthChrg"]
            ),
        }
    )
    return r


# fetch_invoices(engine)
