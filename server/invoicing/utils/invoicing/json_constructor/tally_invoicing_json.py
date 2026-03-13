"""
Construct the Tally post JSON data as Invoicing JSON as per Specification
"""

from invoicing.utils.invoicing.json_constructor.invoicing_json import InvoicingJsonConstructor


class TallyInvoicingJsonConstructor(InvoicingJsonConstructor):
    @classmethod
    def get_lineitems_from_json(cls, td):
        """
        Get the Invoice line items from Tally JSON Data

        :params: td - Tally Data
        """
        return td.get("lineitems", {}).get("lineitem", [])
