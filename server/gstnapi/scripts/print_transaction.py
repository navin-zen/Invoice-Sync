"""
Print details of an API call that we made to GSTN
"""

import sys

import click
from pygstn.utils import json
from six.moves import urllib

if __name__ == "__main__":
    import django

    django.setup()

from cz_utils.decorators import constructor
from gstnapi.models import TransactionLog


@constructor("transaction_id", "is_get", "no_indent")
class PrintTransaction:
    def remove_fields(cls, d, fields):
        """
        Remove some fields from a dictionary
        """
        d = d.copy()
        for f in fields:
            d.pop(f, None)
        return d

    def do_all(self):
        try:
            tlog = TransactionLog.objects2.get(transaction_identifier=self.transaction_id)
        except TransactionLog.DoesNotExist:
            print("Transaction not found", file=sys.stderr)
            return
        print("Client ID:", tlog.headers["clientid"])
        print("ASP Name:", "CloudZen Software Labs Pvt. Ltd.")
        if self.is_get:
            print(f"Request URL: {tlog.url}?{urllib.parse.urlencode(tlog.payload)}")
        else:
            print("Request URL:", tlog.url)
        headers = self.remove_fields(tlog.headers, ["client-secret"])
        if self.no_indent:
            print("Request Headers:", headers)
        else:
            print("Request Headers")
            # dump load dump is needed to convert float into decimal
            print(json.dumps(json.loads(json.dumps(headers)), indent=2))
        request_payload = tlog.payload
        print("Request Payload")
        print(json.dumps(json.loads(json.dumps(request_payload)), indent=2))
        payload = self.remove_fields(tlog.response, ["rek", "hmac"])
        if self.no_indent:
            print("Response Payload:", payload)
        else:
            print("Response Payload")
            print(json.dumps(json.loads(json.dumps(payload)), indent=2))
        print("Error Description:")


@click.command()
@click.option("--transaction-id", required=True, help="The ID of the Transaction")
@click.option("--is-get", is_flag=True, help="Is this a GET request")
@click.option("--no-indent", is_flag=True, help="Do not indent JSON values")
def run(transaction_id, is_get, no_indent):
    PrintTransaction(transaction_id, is_get, no_indent).do_all()


if __name__ == "__main__":
    run()
