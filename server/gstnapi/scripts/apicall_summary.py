"""
Summary of API calls by schema name
"""

import csv
import sys

if __name__ == "__main__":
    import django

    django.setup()

from django.db.models import Count

from gstnapi.models import TransactionLog


def run():
    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
    writer.writerow(["Schema", "Count"])
    for schema_name, count in TransactionLog.objects2.order_by().values_list("schema_name").annotate(Count("pk")):
        writer.writerow([schema_name, count])


if __name__ == "__main__":
    run()
