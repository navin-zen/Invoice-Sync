#!/usr/bin/env python


"""
Populate the Currency model
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

from taxmaster.models import Currency

logger = logging.getLogger(__name__)


def run():
    """
    Import States database
    """
    Currency.objects2.update_or_create(
        defaults={
            "name": "Indian Rupee",
            "exchange_rate": 1,
            "is_home": True,
        },
        abbreviation="INR",
    )
    Currency.objects2.update_or_create(
        defaults={
            "name": "United States Dollar",
            "exchange_rate": 1,
        },
        abbreviation="USD",
    )
    Currency.objects2.update_or_create(
        defaults={
            "name": "Great Britain Pound",
            "exchange_rate": 1,
        },
        abbreviation="GBP",
    )
    Currency.objects2.update_or_create(
        defaults={
            "name": "Euro",
            "exchange_rate": 1,
        },
        abbreviation="EUR",
    )
    Currency.objects2.update_or_create(
        defaults={
            "name": "Japan Yen",
            "exchange_rate": 1,
        },
        abbreviation="JPY",
    )
    logger.info("Created currencies")


if __name__ == "__main__":
    run()
