#!/usr/bin/env python


"""
Populate the State model
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import State

logger = logging.getLogger(__name__)

(STATE, UT, INTERNATIONAL) = (State.STATE, State.UNION_TERRITORY, State.INTERNATIONAL)
INDIA_STATES = [
    ("Jammu and Kashmir", STATE, "01", "JK"),
    ("Himachal Pradesh", STATE, "02", "HP"),
    ("Punjab", STATE, "03", "PB"),
    ("Chandigarh", UT, "04", "CH"),
    ("Uttarakhand", STATE, "05", "UA"),
    ("Haryana", STATE, "06", "HR"),
    ("Delhi", UT, "07", "DL"),
    ("Rajasthan", STATE, "08", "RJ"),
    ("Uttar Pradesh", STATE, "09", "UP"),
    ("Bihar", STATE, "10", "BR"),
    ("Sikkim", STATE, "11", "SK"),
    ("Arunachal Pradesh", STATE, "12", "AR"),
    ("Nagaland", STATE, "13", "NL"),
    ("Manipur", STATE, "14", "MN"),
    ("Mizoram", STATE, "15", "MZ"),
    ("Tripura", STATE, "16", "TR"),
    ("Meghalaya", STATE, "17", "ML"),
    ("Assam", STATE, "18", "AS"),
    ("West Bengal", STATE, "19", "WB"),
    ("Jharkhand", STATE, "20", "JH"),
    ("Odisha", STATE, "21", "OR"),
    ("Chhattisgarh", STATE, "22", "CG"),
    ("Madhya Pradesh", STATE, "23", "MP"),
    ("Gujarat", STATE, "24", "GJ"),
    ("Daman and Diu", UT, "25", "DD"),
    ("Dadra and Nagar Haveli", UT, "26", "DN"),
    ("Maharashtra", STATE, "27", "MH"),
    ("Andhra Pradesh", STATE, "37", "AP"),
    ("Karnataka", STATE, "29", "KA"),
    ("Goa", STATE, "30", "GA"),
    ("Lakshadweep", UT, "31", "LD"),
    ("Kerala", STATE, "32", "KL"),
    ("Tamil Nadu", STATE, "33", "TN"),
    ("Puducherry", UT, "34", "PY"),
    ("Andaman and Nicobar Islands", UT, "35", "AN"),
    ("Telangana", STATE, "36", "TS"),
    ("Other Territory", UT, "97", "OT"),  # This is still in India's economic region
    # The next is not in GSTN. Used internally by GSTZen to denote outside India
    ("International (Outside India)", INTERNATIONAL, "00", "XX"),
]


def run():
    """
    Import States database
    """
    numnewstates = 0
    for name, statetype, code, alphaCode in INDIA_STATES:
        defaults = dict(name=name, statetype=statetype, alphaCode=alphaCode)
        (_, created) = State.objects2.update_or_create(defaults=defaults, code=code)
        if created:
            numnewstates += 1
    logger.info(f"Created {numnewstates} new state(s)")


if __name__ == "__main__":
    run()
