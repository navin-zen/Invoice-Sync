"""
Construct the SAP post JSON data as Invoicing JSON as per Specification
"""

from invoicing.utils.invoicing.json_constructor.invoicing_json import InvoicingJsonConstructor


class SapInvoicingJsonConstructor(InvoicingJsonConstructor):
    @classmethod
    def get_lineitems_from_json(cls, td):
        """
        Get the Invoice line items from SAP JSON Data

        :params: td - SAP Data
        """
        return td.get("lineitems", {}).get("Items", [])
