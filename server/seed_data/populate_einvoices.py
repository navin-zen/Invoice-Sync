import datetime
import random

import click
import django

if __name__ == "__main__":
    django.setup()

from einvoicing.models import ElectronicInvoice, GstIn
from einvoicing.utils.gstin import random_gstin
from einvoicing.utils.utils import fy_range

from taxmaster.models import State

COMPANIES = [
    "Adani Ports Ltd.",
    "Asian Paints Ltd.",
    "Axis Bank",
    "Bajaj Auto Ltd",
    "Bharti Airtel Ltd",
    "Cipla Ltd",
    "Coal India Ltd",
    "Dr. Reddy's Laboratories Ltd",
    "GAIL Ltd",
    "HDFC Ltd.",
    "HDFC Bank",
    "Hero Motocorp Ltd.",
    "Hindustan Unilever Limited",
    "ICICI Bank",
    "Infosys",
    "ITC Ltd",
    "Larsen & Toubro Ltd.",
    "Mahindra & Mahindra Ltd.",
    "Maruti Suzuki Ltd.",
    "NTPC Ltd",
    "Oil and Natural Gas Corporation Ltd",
    "Power Grid Corporation of India",
    "Reliance Industries Ltd",
    "State Bank of India",
    "Sun Pharmaceutical Industries Ltd",
    "Tata Motors Ltd",
    "Tata Steel Ltd",
    "Tata Consultancy Services Ltd",
    "Wipro Ltd",
]


def randomized_einvoice(seller_gstin, seller_name, invoice_number, invoice_date, buyer_gstin, buyer_name):
    return {
        "BuyerDtls": {
            "Gstin": buyer_gstin,
            "Pin": 144009,
            "Stcd": int(buyer_gstin[:2]),
            "TrdNm": buyer_name,
        },
        "DocDtls": {"Dt": invoice_date.isoformat(), "No": invoice_number, "Typ": "INV"},
        "ItemList": [
            {
                "AssAmt": 12945.6,
                "Barcde": "",
                "CesNonAdval": 0,
                "CesRt": 0,
                "CgstRt": 0,
                "Discount": 0,
                "FreeQty": 0,
                "HsnCd": "99871900",
                "IgstRt": 18,
                "OthChrg": 0,
                "PrdDesc": "Charges for November19 MR1",
                "PrdNm": "Charges for November19 MR1",
                "Qty": 1,
                "SgstRt": 0,
                "StateCes": 0,
                "TotAmt": 12945.6,
                "TotItemVal": 15275.81,
                "Unit": "NOS",
                "UnitPrice": 12945.6,
            }
        ],
        "SellerDtls": {
            "Bnm": "",
            "Bno": "",
            "Dst": "",
            "Em": "",
            "Flno": "",
            "Gstin": seller_gstin,
            "Loc": "",
            "Ph": "",
            "Pin": 641021,
            "Stcd": int(seller_gstin[:2]),
            "TrdNm": seller_name,
        },
        "TaxSch": "GST",
        "TranDtls": {"Catg": "B2B", "EcmTrn": "N", "RegRev": "RG", "Typ": "REG"},
        "ValDtls": {
            "AssVal": 12945.6,
            "CesNonAdVal": 0,
            "CesVal": 0,
            "CgstVal": 0,
            "Disc": 0,
            "IgstVal": 2330.208,
            "OthChrg": 0,
            "SgstVal": 0,
            "StCesVal": 0,
            "TotInvVal": 15275.81,
        },
        "Version": "1.00",
    }


def populate_einvoices(gstin_string):
    gstin = GstIn.objects2.get(gstin=gstin_string)
    (seller_gstin, seller_name) = (gstin.gstin, gstin.name)
    counterparies = [(c, random_gstin(state=State.objects2.real().order_by("?").first())) for c in COMPANIES]
    num_invoices = 100
    invoice_dates = sorted(
        (datetime.date.today() - datetime.timedelta(days=random.randint(0, 60))) for i in range(num_invoices)
    )
    for i, invoice_date in enumerate(invoice_dates, start=1):
        invoice_number = f"INV/{i}"
        (buyer_name, buyer_gstin) = random.choice(counterparies)
        einvoice_json = randomized_einvoice(
            seller_gstin, seller_name, invoice_number, invoice_date, buyer_gstin, buyer_name
        )
        ei = ElectronicInvoice(
            gstin=gstin,
            doctype=ElectronicInvoice.DT_INVOICE,
            docsubtype=ElectronicInvoice.DST_NOT_APPLICABLE,
            financial_year=fy_range(invoice_date)[0],
            date=invoice_date,
            number=invoice_number,
            is_exim=False,
            ctin=buyer_gstin,
            einvoice_status=ElectronicInvoice.EIS_CANDIDATE,
            einvoice_json=einvoice_json,
        )
        ei.full_clean()
        ei.save()
        print("Created invoice", ei)


@click.command()
@click.option("--gstin", required=True, help="The GSTIN to create invoices for")
def main(gstin):
    populate_einvoices(gstin)


if __name__ == "__main__":
    main()
