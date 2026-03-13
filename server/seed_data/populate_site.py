#!/usr/bin/env python


"""
Set the Site details
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

from django.conf import settings
from django.contrib.sites.models import Site

logger = logging.getLogger(__name__)


def run():
    """
    Import States database
    """
    site = Site.objects.get(pk=settings.SITE_ID)
    site.domain = "my.gstzen.in"
    site.name = "GSTZen"
    site.full_clean()
    site.save()
    logger.info(f"Update Site details to {site}")


if __name__ == "__main__":
    run()
