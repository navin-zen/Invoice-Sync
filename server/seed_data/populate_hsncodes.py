#!/usr/bin/env python


"""
Populate the State model
"""

import csv
import datetime
import logging
from decimal import Decimal

import click

if __name__ == "__main__":
    import django

    django.setup()

from cz_utils.decorators import constructor
from taxmaster.models import HsnCode

logger = logging.getLogger(__name__)


@constructor("import_date", "csv_file")
class PopulateHsnCodes:
    HEADERS = [
        "Number",
        "Name",
        "Goods / Service",
        "CGST Rate",
        "SGCT Rate",
        "IGST Rate",
        "Cess Rate",
    ]

    def do_all(self):
        (year, month, day) = self.import_date
        import_date = datetime.date(year, month, day)
        data = self.parse_csv(self.csv_file)
        self.populate_hsndata(data, import_date)

    @classmethod
    def is_goods(cls, goods_or_service):
        if goods_or_service == "G":
            return True
        elif goods_or_service == "S":
            return False
        else:
            raise ValueError(f"Unexpected value `{goods_or_service}` for Goods/Service")

    @classmethod
    def parse_csv(cls, filename):
        """
        Parse the CSV containing HSN data.
        """
        data = []
        with open(filename) as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0:
                    assert row == cls.HEADERS, "Headers don't match"
                    continue
                (
                    number,
                    name,
                    goods_or_service,
                    tax_rate_cgst,
                    tax_rate_sgst,
                    tax_rate_igst,
                    tax_rate_cess,
                ) = row
                datum = [
                    name.strip(),
                    number.strip(),
                    cls.is_goods(goods_or_service),
                    Decimal(str(tax_rate_cgst)),
                    Decimal(str(tax_rate_sgst)),
                    Decimal(str(tax_rate_igst)),
                    Decimal(str(tax_rate_cess)),
                ]
                data.append(datum)
        return data

    @classmethod
    def populate_hsndata(self, data, import_date):
        """
        Populate the HSN data into our database
        """
        for item in data:
            (name, number, is_goods, cgst_rate, sgst_rate, igst_rate, cess_rate) = item
            hsncode = (
                HsnCode.objects2.alive_on(import_date).filter(number=number, is_goods=is_goods).get_the_one_result()
            )
            if not hsncode:
                hsncode = HsnCode(number=number, is_goods=is_goods)
            hsncode.name = name
            hsncode.number = number
            hsncode.is_goods = is_goods
            hsncode.tax_rate_cgst = cgst_rate
            hsncode.tax_rate_igst = igst_rate
            hsncode.tax_rate_sgst = sgst_rate
            hsncode.tax_rate_cess = cess_rate
            hsncode.save(change_date=import_date)
            logger.info(f"Saving HSN Code {hsncode}")


@click.command()
@click.option(
    "--import-date",
    required=True,
    nargs=3,
    type=(int, int, int),
    help="The date on which the codes/rates are released (YYYY MM DD)",
)
@click.option("--csv-file", required=True, help="The file containing the HSN/SAC codes data")
def run(import_date, csv_file):
    PopulateHsnCodes(import_date, csv_file).do_all()


if __name__ == "__main__":
    run()
