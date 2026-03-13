#!/usr/bin/env python


"""
Populate the taxmaster.DocumentType model
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import DocumentType

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = [
    (1, "Invoices for outward supply"),
    (2, "Invoices for inward supply from unregistered person"),
    (3, "Revised Invoice"),
    (4, "Debit Note"),
    (5, "Credit Note"),
    (6, "Receipt voucher"),
    (7, "Payment Voucher"),
    (8, "Refund voucher"),
    (9, "Delivery Challan for job work"),
    (10, "Delivery Challan for supply on approval"),
    (11, "Delivery Challan in case of liquid gas"),
    (12, "Delivery Challan in cases other than by way of supply (excluding at S no. 9 to 11)"),
]


def run():
    """
    Create/Update DocumentType models
    """
    numnewdocumenttypes = 0
    for number, name in DOCUMENT_TYPES:
        defaults = dict(name=name)
        (_, created) = DocumentType.objects2.update_or_create(defaults=defaults, number=number)
        if created:
            numnewdocumenttypes += 1
    logger.info(f"Created {numnewdocumenttypes} new Document Type(s)")


if __name__ == "__main__":
    run()
