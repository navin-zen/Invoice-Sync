#!/usr/bin/env python


"""
Populate the Unit model
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import Unit

logger = logging.getLogger(__name__)

UNITS = [
    ("BAG", "BAGS"),
    ("BAL", "BALE"),
    ("BDL", "BUNDLES"),
    ("BKL", "BUCKLES"),
    ("BOU", "BILLIONS OF UNITS"),
    ("BOX", "BOX"),
    ("BTL", "BOTTLES"),
    ("BUN", "BUNCHES"),
    ("CAN", "CANS"),
    ("CBM", "CUBIC METER"),
    ("CCM", "CUBIC CENTIMETER"),
    ("CMS", "CENTIMETER"),
    ("CTN", "CARTONS"),
    ("DOZ", "DOZEN"),
    ("DRM", "DRUM"),
    ("GGK", "GREAT GROSS"),
    ("GMS", "GRAMS"),
    ("GRS", "GROSS"),
    ("GYD", "GROSS YARDS"),
    ("KGS", "KILOGRAMS"),
    ("KLR", "KILOLITER"),
    ("KME", "KILOMETERS"),
    ("MLT", "MILLILITER"),
    ("MTR", "METER"),
    ("MTS", "METRIC TON"),
    ("NOS", "NUMBER"),
    ("PAC", "PACKS"),
    ("PCS", "PIECES"),
    ("PRS", "PAIRS"),
    ("QTL", "QUINTAL"),
    ("ROL", "ROLLS"),
    ("SET", "SETS"),
    ("SQF", "SQUARE FEET"),
    ("SQM", "SQUARE METER"),
    ("SQY", "SQUARE YARDS"),
    ("TBS", "TABLETS"),
    ("TGM", "TEN GRAMS"),
    ("THD", "THOUSANDS"),
    ("TON", "GREAT BRITAIN TON"),
    ("TUB", "TUBES"),
    ("UGS", "US GALLONS"),
    ("UNT", "UNITS"),
    ("YDS", "YARDS"),
    ("OTH", "OTHERS"),
]


def run():
    """
    Import Unit database
    """
    numnew = 0
    for name, long_name in UNITS:
        (_, created) = Unit.objects2.update_or_create(
            defaults={"long_name": long_name, "name_for_gstn": name}, name=name
        )
        if created:
            numnew += 1
    logger.info(f"Created {numnew} new Unit(s)")


if __name__ == "__main__":
    run()
