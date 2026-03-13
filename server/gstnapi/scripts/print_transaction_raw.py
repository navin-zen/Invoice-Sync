"""
Print transaction's JSON
"""

import sys

import click
from pygstn.utils import json

if __name__ == "__main__":
    import django

    django.setup()

from cz_utils.decorators import constructor
from gstnapi.models import TransactionLog


@constructor("transaction_id")
class PrintTransaction:
    def do_all(self):
        try:
            tlog = TransactionLog.objects2.get(transaction_identifier=self.transaction_id)
        except TransactionLog.DoesNotExist:
            print("Transaction not found", file=sys.stderr)
            return
        data = json.loads(
            json.dumps(
                {
                    "payload": tlog.payload,
                    "response": tlog.response,
                }
            )
        )
        print(json.dumps(data, indent=2))


@click.command()
@click.option("--transaction-id", required=True, help="The ID of the Transaction")
def run(transaction_id):
    PrintTransaction(transaction_id).do_all()


if __name__ == "__main__":
    run()
