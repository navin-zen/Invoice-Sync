#!/usr/bin/env python


"""
Populate HsnCodes Goods list from TXT file
"""

import codecs
import datetime
import logging
import os

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import HsnCode

logger = logging.getLogger(__name__)


class PopulateHsnCodes:
    IMPORT_DATE = datetime.date(2017, 1, 1)
    FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goods.txt")
    IS_GOODS = True

    def do_all(self):
        data = self.parse_data(self.FILENAME)
        self.populate_hsndata(data, self.IMPORT_DATE)

    def parse_data(self, filename):
        """
        Parse the TXT containing HSN data.
        """
        data = []
        with codecs.open(self.FILENAME, "r", "utf-8") as f:
            for line in f:
                words = line.strip().split(" ")
                (chapter, code, name) = words[0], words[1], " ".join(words[2:])
                data.append((chapter, code, name))
        return data

    def populate_hsndata(self, data, import_date):
        """
        Populate the HSN data into our database
        """
        is_goods = self.IS_GOODS
        existing_codes = HsnCode.objects2.filter(is_goods=is_goods).value("number").as_set()
        new_data = [(_, number, name) for (_, number, name) in data if (number not in existing_codes)]
        objects = [
            HsnCode(number=number, name=name, is_goods=is_goods, birthdate=import_date, deathdate=None)
            for (_, number, name) in new_data
        ]
        for h in objects:
            h.full_clean()
            break  # Full clean just one object (to save upload time)
        HsnCode.objects2.bulk_create(objects)
        logger.info(f"Saving {len(objects)} HSN Codes")


def run():
    PopulateHsnCodes().do_all()


if __name__ == "__main__":
    run()
