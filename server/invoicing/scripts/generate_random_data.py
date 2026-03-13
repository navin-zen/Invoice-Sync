"""
Invoke random data utility
"""

if __name__ == "__main__":
    import django

    django.setup()

from invoicing.utils.randomized_data import Samplinvoicing
from pygstn.utils import json


def run():
    e = Samplinvoicing.randomized_invoicing("29AAFCC9980M000", "CloudZen Software Labs Pvt Ltd", "GSTZen", "570023")
    print(json.dumps(e))


if __name__ == "__main__":
    run()


