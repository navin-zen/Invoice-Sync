"""
Import HSN/SAC codes from XLSX public by GSTN as part of new returns
"""

import codecs
import csv
import datetime
import logging

import click

if __name__ == "__main__":
    import django

    django.setup()

from cz_utils.decorators import constructor
from taxmaster.models import HsnCode

logger = logging.getLogger(__name__)


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [s.decode("utf-8") for s in row]

    def __iter__(self):
        return self


@constructor("csv_file")
class PopulateHsnSacCodes:
    HEADERS = ["HSN/SAC Code", "Description"]

    def do_all(self):
        import_date = datetime.date(2017, 7, 1)
        data = self.parse_csv(self.csv_file)
        self.populate_hsndata(data, import_date)

    @classmethod
    def parse_csv(cls, fileobj):
        """
        Parse the CSV containing HSN data.
        """
        data = []
        reader = UnicodeReader(fileobj)
        for i, row in enumerate(reader):
            if i == 0:
                continue
            (number, name) = row
            datum = [number.strip(), name.strip()[:1020]]
            data.append(datum)
        return data

    @classmethod
    def populate_hsndata(self, data, import_date):
        """
        Populate the HSN data into our database
        """
        for item in data:
            (number, name) = item
            is_goods = not number.startswith("99")
            qs = HsnCode.objects2.filter(number=number)
            if qs.exists():
                qs.update(name=name, is_official=True, is_goods=is_goods)
            else:
                hsncode = HsnCode(name=name, number=number, is_goods=is_goods, is_official=True)
                hsncode.full_clean()
                hsncode.save(change_date=import_date)
                logger.info(f"Saving HSN Code {hsncode}")


@click.command()
@click.option(
    "--csv-file",
    type=click.File("rb"),
    required=True,
    help="The file containing the HSN/SAC codes data",
)
def run(csv_file):
    PopulateHsnSacCodes(csv_file).do_all()


if __name__ == "__main__":
    run()
