#!/usr/bin/env python


"""
Populate the database with demo data
"""

import datetime
import random

if __name__ == "__main__":
    import django

    django.setup()

from einvoicing.utils.utils import ALLOWED_TAX_RATES
from gstcomply.customizations.django_tenants.utils import schema_context

from taxmaster.models import HsnCode, Unit
from taxpayer.models import GstIn, Invoice, LegalPerson
from taxpayer.utils.api.common import (
    ExportInvoiceUpdaterFromPaperData,
    OutgoingInvoiceUpdaterFromPaperData,
    get_or_create_gstin,
    get_or_create_legalperson,
)

CUSTOMERS = [
    ("CloudZen.TN.2", "33GSPTN1542G1ZE"),
    ("CloudZen.MH.1", "27GSPMH1541G1ZS"),
]


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
    def random_invoice_date(cls, prd):
        return prd + datetime.timedelta(days=random.randint(0, 29))

    @classmethod
    def get_applicable_tax_rates(cls, seller, buyer, hsncode):
        """
        Get the applicable rates for the item.

        Returns 3-tuple (cgst, sgst, igst)
        """
        tax_rate = random.choice(ALLOWED_TAX_RATES)
        if seller.state == buyer.state:
            return (tax_rate / 2, tax_rate / 2, 0)
        else:
            return (0, 0, tax_rate)

    @classmethod
    def new_invoice_entry_details(cls, seller, buyer, is_exim):
        hsncode = HsnCode.objects2.order_by("?").filter(number__iregex=r"^\d*[02468]$").first()
        if is_exim:
            (tax_rate_cgst, tax_rate_sgst, tax_rate_igst) = (0, 0, 0)
        else:
            (tax_rate_cgst, tax_rate_sgst, tax_rate_igst) = cls.get_applicable_tax_rates(seller, buyer, hsncode)
        quantity = random.randint(1, 10)
        unit = Unit.objects2.order_by("?").first()
        unit_rate = random.randint(100, 2000)
        return {
            "hsn_sc": hsncode.number,
            "ty": hsncode.is_goods,
            "tax_rate": (tax_rate_cgst + tax_rate_sgst + tax_rate_igst),
            "crt": tax_rate_cgst,
            "srt": tax_rate_sgst,
            "irt": tax_rate_igst,
            "csrt": 0,
            "qty": quantity,
            "unit": unit,
            "unit_rate": unit_rate,
        }

    @classmethod
    def new_invoice_entry(cls, seller, buyer, serial_number, is_exim=False):
        return {
            "num": serial_number,
            "itm_det": cls.new_invoice_entry_details(seller, buyer, is_exim),
        }

    @classmethod
    def new_outgoing_invoices(cls, gstin):
        tax_prd = datetime.date(2016, 4, 1)
        GSTIN = GstIn.objects2.get(gstin=GstInGenerator.gstin_string)
        WE = LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=GSTIN.gstin).first()
        BUYER_INTRASTATE = (
            LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=CUSTOMERS[0][1]).portal_gstin(GSTIN).first()
        )
        BUYER_INTERSTATE = (
            LegalPerson.objects2.filter(legalpersoncachedinfo__gstin=CUSTOMERS[1][1]).portal_gstin(GSTIN).first()
        )

        # 1000 B2B intrastate invoices
        num_invoices = 1000
        invoice_dates = sorted([cls.random_invoice_date(tax_prd) for i in range(num_invoices)])
        for serial_number, invoice_date in enumerate(invoice_dates, start=1):
            buyer = BUYER_INTRASTATE
            invoice_number = f"1617/TN/TN2/{serial_number}"
            entries = [cls.new_invoice_entry(WE, buyer, i) for i in range(1, random.randint(2, 10))]
            invoice_data = {
                "inum": invoice_number,
                "inv_typ": "R",
                "idt": invoice_date,
                "pos": buyer.state,
                "rchrg": "N",
                "prs": "N",
                "itms": entries,
            }
            updater = OutgoingInvoiceUpdaterFromPaperData()
            invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
            updater.update_invoice_entries(invoice, invoice_data)

        # 1000 B2B interstate invoices
        num_invoices = 1000
        invoice_dates = sorted([cls.random_invoice_date(tax_prd) for i in range(num_invoices)])
        for serial_number, invoice_date in enumerate(invoice_dates, start=1):
            buyer = BUYER_INTERSTATE
            invoice_number = f"1617/TN/MH1/{serial_number}"
            entries = [cls.new_invoice_entry(WE, buyer, i) for i in range(1, random.randint(2, 10))]
            invoice_data = {
                "inum": invoice_number,
                "inv_typ": "R",
                "idt": invoice_date,
                "pos": buyer.state,
                "rchrg": "N",
                "prs": "N",
                "itms": entries,
            }
            updater = OutgoingInvoiceUpdaterFromPaperData()
            invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
            updater.update_invoice_entries(invoice, invoice_data)

        # 1000 B2C
        num_invoices = 1000
        invoice_dates = sorted([cls.random_invoice_date(tax_prd) for i in range(num_invoices)])
        for serial_number, invoice_date in enumerate(invoice_dates, start=1001):
            # Temporarily setting `buyer` to generate invoice entries.
            # We'll set it to None after that.
            buyer = BUYER_INTERSTATE
            invoice_number = f"1617/TN/MH1/{serial_number}"
            entries = [cls.new_invoice_entry(WE, buyer, i) for i in range(1, random.randint(2, 10))]
            buyer = None
            invoice_data = {
                "inum": invoice_number,
                "inv_typ": "R",
                "idt": invoice_date,
                "pos": BUYER_INTERSTATE.state,  # This should be inter-state
                "rchrg": "N",
                "prs": "N",
                "itms": entries,
            }
            updater = OutgoingInvoiceUpdaterFromPaperData()
            invoice = updater.update_invoice_metadata(gstin, invoice_data, WE, buyer)
            updater.update_invoice_entries(invoice, invoice_data)

        # 500 Export
        num_invoices = 500
        invoice_dates = sorted([cls.random_invoice_date(tax_prd) for i in range(num_invoices)])
        for serial_number, invoice_date in enumerate(invoice_dates, start=1):
            # Temporarily setting `buyer` to generate invoice entries.
            # We'll set it to None after that.
            buyer = BUYER_INTERSTATE
            invoice_number = f"1617/TN/CA1/{serial_number}"
            entries = [cls.new_invoice_entry(WE, buyer, i, is_exim=True) for i in range(1, random.randint(2, 10))]
            buyer = None
            invoice_data = {
                "inum": invoice_number,
                "idt": invoice_date,
                "is_exim": True,
                "exp_typ": Invoice.EXPORT_WITH_PAY,
                "pos": "",
                "sbpcode": "INACH1",
                "sbnum": serial_number,
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
        gstin = GstIn.objects2.get(gstin=GstInGenerator.gstin_string)
        cls.new_outgoing_invoices(gstin)


class GstInGenerator:
    gstin_string = "27GSPMH1542G1ZR"
    name = "CloudZen.MH.2"

    @classmethod
    def do_all(cls):
        gstin, _ = get_or_create_gstin(cls.gstin_string, cls.name)
        return gstin


def run():
    with schema_context("sandbox"):
        gstin = GstInGenerator.do_all()
        LegalPersonGenerator.do_all(gstin)
        InvoiceGenerator.do_all()


if __name__ == "__main__":
    run()
