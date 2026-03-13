#!/usr/bin/env python


"""
Populate the database with demo data
"""

import datetime
from decimal import Decimal as D

if __name__ == "__main__":
    import django

    django.setup()


from gstcomply.customizations.django_tenants.utils import schema_context

from taxmaster.models import Unit
from taxpayer.models import GstIn, Invoice, LegalPerson
from taxpayer.utils.api.common import (
    ExportInvoiceUpdaterFromPaperData,
    OutgoingInvoiceUpdaterFromPaperData,
    get_or_create_gstin,
    get_or_create_legalperson,
)

CUSTOMERS = [
    ("CloudZen.TN.1", "33GSPTN1541G1ZF"),
    ("CloudZen.MH.1", "27GSPMH1541G1ZS"),
]
OUR_TIN = "33GSPTN1542G1ZE"


class LegalPersonGenerator:
    @classmethod
    def do_all(cls, gstin):
        for name, gstin_string in CUSTOMERS:
            lp = get_or_create_legalperson(gstin_string, name, permanentaccountnumber=gstin.permanentaccountnumber)
            lp.save()


class InvoiceGenerator:
    @classmethod
    def do_all(cls):
        cls.add_invoices()

    @classmethod
    def new_outgoing_invoices(cls, gstin):
        UNIT_NOS = Unit.objects2.filter(name="NOS").first()
        UNIT_KGS = Unit.objects2.filter(name="KGS").first()
        WE = LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=gstin.gstin).first()
        BUYER_INTRASTATE = LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=CUSTOMERS[0][1]).first()
        BUYER_INTERSTATE = LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=CUSTOMERS[1][1]).first()

        # 1st invoice (B2B intrastate)
        # txval: 320020, cgst: 21601.80, sgst: 21601.80
        buyer = BUYER_INTRASTATE
        invoice_number = "16-17/TN1/TN2/01"
        invoice_date = datetime.date(2016, 4, 1)
        order_number = "12345"
        order_date = datetime.date(2016, 3, 21)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "39252000",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 9,
                    "srt": 9,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 200,
                    "unit": UNIT_NOS,
                    "unit_rate": D("400.1"),  # 400.1 can't be represented correctly as a float
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "94036000",
                    "ty": True,
                    "tax_rate": 12,
                    "crt": 6,
                    "srt": 6,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 200,
                    "unit": UNIT_NOS,
                    "unit_rate": 1200,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "R",
            "idt": invoice_date,
            "pos": buyer.state,
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 2nd invoice (B2B interstate)
        # txval: 610000, igst: 5490
        buyer = BUYER_INTERSTATE
        invoice_number = "16-17/TN1/MH1/01"
        invoice_date = datetime.date(2016, 4, 25)
        order_number = "23456"
        order_date = datetime.date(2016, 4, 21)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "72159010",
                    "ty": True,
                    "tax_rate": 12,
                    "crt": 0,
                    "srt": 0,
                    "irt": D("0.9"),
                    "csrt": 0,
                    "qty": 1000,
                    "unit": UNIT_NOS,
                    "unit_rate": 120,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "73042310",
                    "ty": True,
                    "tax_rate": 5,
                    "crt": 0,
                    "srt": 0,
                    "irt": D("0.9"),
                    "csrt": 0,
                    "qty": 5000,
                    "unit": UNIT_NOS,
                    "unit_rate": 98,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "R",
            "idt": invoice_date,
            "pos": buyer.state,
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 3rd invoice (B2C large interstate)
        # txval: 420000, igst: 75600
        buyer = None
        invoice_number = "16-17/TN1/TN2/02"
        invoice_date = datetime.date(2016, 4, 12)
        order_number = "34567"
        order_date = datetime.date(2016, 4, 11)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "09011111",
                    "ty": True,
                    "tax_rate": 28,
                    "crt": 0,
                    "srt": 0,
                    "irt": 18,
                    "csrt": 0,
                    "qty": 100,
                    "unit": UNIT_KGS,
                    "unit_rate": 1800,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "090210",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 0,
                    "srt": 0,
                    "irt": 18,
                    "csrt": 0,
                    "qty": 200,
                    "unit": UNIT_KGS,
                    "unit_rate": 1200,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "",
            "idt": invoice_date,
            "pos": BUYER_INTERSTATE.state,  # This should be inter-state
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 4th invoice (B2C small)
        # txval: 4200, cgst: 468, sgst: 468
        buyer = None
        invoice_number = "16-17/TN1/TN2/03"
        invoice_date = datetime.date(2016, 4, 14)
        order_number = "45678"
        order_date = datetime.date(2016, 4, 12)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "09011111",
                    "ty": True,
                    "tax_rate": 28,
                    "crt": 14,
                    "srt": 14,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 1,
                    "unit": UNIT_KGS,
                    "unit_rate": 1800,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "090210",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 9,
                    "srt": 9,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 2,
                    "unit": UNIT_KGS,
                    "unit_rate": 1200,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "",
            "idt": invoice_date,
            "pos": WE.state,  # intra-state
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 5th invoice (B2C large intrastate)
        # txval: 496000, cgst: 55440, sgst: 55440
        buyer = None
        invoice_number = "16-17/TN1/MH1/02"
        invoice_date = datetime.date(2016, 4, 13)
        order_number = "56789"
        order_date = datetime.date(2016, 4, 12)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "09011111",
                    "ty": True,
                    "tax_rate": 28,
                    "crt": 14,
                    "srt": 14,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 120,
                    "unit": UNIT_KGS,
                    "unit_rate": 1800,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "090210",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 9,
                    "srt": 9,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 200,
                    "unit": UNIT_KGS,
                    "unit_rate": 1400,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "",
            "idt": invoice_date,
            "pos": BUYER_INTRASTATE.state,  # This should be intra-state
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 6th invoice (B2B intrastate -- with reverse charge)
        # txval: 7000000, cgst: 510000, sgst: 510000
        buyer = BUYER_INTRASTATE
        invoice_number = "16-17/TN1/TN2/04"
        invoice_date = datetime.date(2016, 4, 6)
        order_number = "56789"
        order_date = datetime.date(2016, 4, 4)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "01019020",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 9,
                    "srt": 9,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 50,
                    "unit": UNIT_NOS,
                    "unit_rate": 60000,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "01021020",
                    "ty": True,
                    "tax_rate": 12,
                    "crt": 6,
                    "srt": 6,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 100,
                    "unit": UNIT_NOS,
                    "unit_rate": 40000,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "inv_typ": "R",
            "idt": invoice_date,
            "pos": buyer.state,
            "od_num": order_number,
            "od_dt": order_date,
            "rchrg": "Y",
            "prs": "N",
            "itms": entries,
        }
        updater = OutgoingInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 7th invoice (Export With Pay)
        # txval: 1700000, igst: 306000
        buyer = None
        invoice_number = "16-17/TN1/CA/01"
        invoice_date = datetime.date(2016, 4, 18)
        order_number = "67890"
        order_date = datetime.date(2016, 4, 2)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "09011111",
                    "ty": True,
                    "tax_rate": 28,
                    "crt": 0,
                    "srt": 0,
                    "irt": 18,
                    "csrt": 0,
                    "qty": 800,
                    "unit": UNIT_KGS,
                    "unit_rate": 1500,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "090210",
                    "ty": True,
                    "tax_rate": 18,
                    "crt": 0,
                    "srt": 0,
                    "irt": 18,
                    "csrt": 0,
                    "qty": 500,
                    "unit": UNIT_KGS,
                    "unit_rate": 1000,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "idt": invoice_date,
            "is_exim": True,
            "exp_typ": Invoice.EXPORT_WITH_PAY,
            "pos": "",
            "od_num": order_number,
            "od_dt": order_date,
            "sbpcode": "INACH1",
            "sbnum": 1,
            "sbdt": invoice_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = ExportInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)
        # 8th invoice (Export Without Pay)
        # txval: 700000
        buyer = None
        invoice_number = "16-17/TN1/CA/02"
        invoice_date = datetime.date(2016, 4, 19)
        order_number = "78901"
        order_date = datetime.date(2016, 4, 3)
        entries = [
            {
                "num": 1,
                "itm_det": {
                    "hsn_sc": "01019020",
                    "ty": True,
                    "tax_rate": 12,
                    "crt": 0,
                    "srt": 0,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 200,
                    "unit": UNIT_NOS,
                    "unit_rate": 2000,
                },
            },
            {
                "num": 2,
                "itm_det": {
                    "hsn_sc": "01021020",
                    "ty": True,
                    "tax_rate": 12,
                    "crt": 0,
                    "srt": 0,
                    "irt": 0,
                    "csrt": 0,
                    "qty": 100,
                    "unit": UNIT_NOS,
                    "unit_rate": 3000,
                },
            },
        ]
        invoice_data = {
            "inum": invoice_number,
            "idt": invoice_date,
            "is_exim": True,
            "exp_typ": Invoice.EXPORT_WITHOUT_PAY,
            "pos": "",
            "od_num": order_number,
            "od_dt": order_date,
            "sbpcode": "INIXA4",
            "sbnum": 1,
            "sbdt": invoice_date,
            "rchrg": "N",
            "prs": "N",
            "itms": entries,
        }
        updater = ExportInvoiceUpdaterFromPaperData()
        invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
        updater.update_invoice_entries(invoice, invoice_data)

    @classmethod
    def add_invoices(cls):
        gstin = GstIn.objects2.filter(gstin=OUR_TIN).first()
        cls.new_outgoing_invoices(gstin)


class GstInGenerator:
    @classmethod
    def do_all(cls):
        gstin_string = OUR_TIN
        name = "CloudZen.TN.2"
        gstin, _ = get_or_create_gstin(gstin_string, name)
        return gstin


def run():
    with schema_context("sandbox"):
        gstin = GstInGenerator.do_all()
        LegalPersonGenerator.do_all(gstin)
        InvoiceGenerator.do_all()


if __name__ == "__main__":
    run()
