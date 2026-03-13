"""
This script is used to build the CSV executable for invoicing.
"""

import os

import click
import django

if __name__ == "__main__":
    django.setup()

from django.conf import settings
from invoicing.models import CachedData, Configuration
from invoicing.utils.csv_utils import update_config
from invoicing.utils.gstzen_cloud import post_all_to_gstzen
from invoicing.utils.IRP import generate_invoice
from invoicing.utils.sqlalchemy_invoice_generation import fetch_invoices_for_session


@click.command()
@click.option(
    "--config-uuid",
    required=True,
    type=click.UUID,
    help="The UUID of the configuration object.",
)
def main(config_uuid):
    cd = CachedData(datatype=CachedData.DT_invoicing_SESSION_MARKER)
    cd.full_clean()
    cd.save()
    session_uuid = str(cd.uuid)
    config = Configuration.objects2.get(uuid=config_uuid)
    for filename in os.listdir(settings.invoicing_INPUT_PATH):
        if filename.endswith(".csv") or filename.endswith(".CSV"):
            config = update_config(config, settings.invoicing_INPUT_PATH + filename)
            config.save()
        fetch_invoices_for_session(session_uuid, only_config=config)
    if settings.TO_IRP_THROUGH_ZEN:
        post_all_to_gstzen()
    else:
        generate_invoice()


if __name__ == "__main__":
    main()


