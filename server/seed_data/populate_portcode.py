#!/usr/bin/env python


"""
Populate PortCode(s) from TXT file
"""

import codecs
import csv
import logging
import os

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import PortCode

logger = logging.getLogger(__name__)


class PopulatePortCodes:
    FILENAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port-codes.txt")
    CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "port-codes-2.csv")

    def do_all(self):
        seen_codes = set()
        data = self.parse_data(self.FILENAME, seen_codes) + self.parse_data2_csv(self.CSV_FILE, seen_codes)
        self.populate_portcodes(data)

    def parse_data(self, filename, seen_codes):
        """
        Parse the TXT containing HSN data.
        """
        data = []
        with codecs.open(self.FILENAME, "r", "utf-8") as f:
            for line in f:
                (code, name) = line.strip().split("\t")
                if code not in seen_codes:
                    seen_codes.add(code)
                    data.append((code, name))
        return data

    def parse_data2_csv(self, filename, seen_codes):
        """
        Parse the CSV file containing PORTS data
        """
        data = []
        with codecs.open(self.CSV_FILE, "r", "utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 2:
                    (code, name) = (c.strip() for c in row)
                    code = code.upper()
                    if code not in seen_codes:
                        seen_codes.add(code)
                        data.append((code, name))
        return data

    def populate_portcodes(self, data):
        """
        Populate the Port Codes into our database
        """
        existing_codes = PortCode.objects2.value("code").as_set()
        new_data = [(code, name) for (code, name) in data if (code not in existing_codes)]
        objects = [PortCode(code=code, name=name) for (code, name) in new_data]
        for o in objects:
            o.full_clean()
            break  # Full clean just one object (to save upload time)
        PortCode.objects2.bulk_create(objects)
        logger.info(f"Saving {len(objects)} Port Codes")


def run():
    PopulatePortCodes().do_all()


if __name__ == "__main__":
    run()
