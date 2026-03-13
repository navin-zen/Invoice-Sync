import json

import django

django.setup()

from einvoicing.utils.api.common import get_or_create_gstin  # NOQA
from einvoicing.utils.einvoice.einvoice_json_to_db import EinvoiceUploader  # NOQA
from einvoicing.utils.gstnutils_einvoice import authenticate_and_generate_einvoice  # NOQA

from cz_utils.json_utils import JSONEncoder  # NOQA

sample_json = {
    "ValDtls": {
        "AssVal": 14840.99,
        "CgstVal": 14840.99,
        "SgstVal": 14840.99,
        "IgstVal": 14840,
        "CesVal": 14840,
        "StCesVal": 14840,
        "RndOffAmt": 14,
        "TotInvVal": 14840,
        "TotInvValFc": 14840,
    },
    "DocDtls": {
        "Dt": "15/05/2020",
        "No": "19330372145",
        "Typ": "INV",
    },
    "Version": "1.01",
    "ItemList": [
        {
            "IsServc": "Y",
            "PrdNm": "License",
            "GstRt": 12,
            "PrdDesc": "License",
            "HsnCd": "998341",
            "AssAmt": 4567,
            "Qty": "12.000",
            "OthChrg": 0,
            "Discount": 0,
            "CesRt": 0,
            "FreeQty": "0",
            "SlNo": "1",
            "TotAmt": 4567,
            "UnitPrice": 380.583,
            "Unit": "NOS",
            "TotItemVal": 5115.04,
        },
        {
            "IsServc": "Y",
            "PrdNm": "License",
            "GstRt": 12,
            "PrdDesc": "License",
            "HsnCd": "998341",
            "AssAmt": 4567,
            "Qty": "12.000",
            "OthChrg": 0,
            "Discount": 0,
            "CesRt": 0,
            "FreeQty": "0",
            "SlNo": "1",
            "TotAmt": 4567,
            "UnitPrice": 380.583,
            "Unit": "NOS",
            "TotItemVal": 5115.04,
        },
    ],
    "TranDtls": {"SupTyp": "B2B", "TaxSch": "GST", "RegRev": "N", "EcmGstin": "36AAXFR4027R1Z7"},
    "BuyerDtls": {
        "Loc": "Malumichampatti",
        "TrdNm": "Gilbarco Veeder Root India Pvt Ltd - Tamil Nadu",
        "Pin": "560077",
        "LglNm": "GILBARCO VEEDER ROOT INDIA PRIVATE LIMITED",
        "Pos": "39",
        "State": "Karnataka",
        "Addr1": "abc",
        "Gstin": "36AAXFR4027R1Z7",
        "Em": "sakthivelan.g@gilbarco.com",
        "Ph": "9865599555",
    },
    "SellerDtls": {
        "Em": "sakthivelan.g@gilbarco.com",
        "Loc": "Malumichampatti",
        "TrdNm": "Gilbarco Veeder Root India Pvt Ltd - Tamil Nadu",
        "Pin": "641021",
        "Dst": "Coimbatore",
        "LglNm": "GILBARCO VEEDER ROOT INDIA PRIVATE LIMITED",
        "Flno": "Ind. Estate Post",
        "State": "Unknown",
        "Bno": "SF No 627/2 628/2, sector W-4",
        "Bnm": "  PDP Coimbatore Campus",
        "Addr1": "Unknown",
        "Gstin": "33AADCG4992P1Z0",
        "Ph": "9865599555",
    },
    "RefDtls": {
        "InvRm": "abcde",
        "InvStDt": "13/05/2020",
        "InvEndDt": "15/05/2020",
        "PreDocDtls": {
            "PreDocument": [
                {
                    "InvNo": "",
                    "InvDt": "",
                    "OthRefNo": "",
                },
            ]
        },
        "ContrDtls": {
            "Contract": [
                {
                    "RecAdvRefr": "",
                    "RecAdvDt": "",
                    "TendRefr": "",
                    "ContrRefr": "",
                    "ExtRefr": "",
                    "ProjRefr": "",
                    "PORefDt": "",
                },
            ],
        },
    },
}


def create_inv():
    """
    Create Invoice from Json data
    @params:
    gstin: Which GSTIN have to Create Invoice and Entries
    td: Json Data
    """
    gstin = get_or_create_gstin("33AADCG4992P1Z0", "NIC")
    invoice = EinvoiceUploader.create_invoice(gstin, sample_json)
    return invoice


def generate_invoice():
    invoice = create_inv()
    sample_json.update({"Uuid": invoice.uuid, "Url": invoice.get_absolute_url()})
    print(json.dumps(sample_json, cls=JSONEncoder))
    authenticate_and_generate_einvoice(invoice_uuid=str(invoice.uuid))
