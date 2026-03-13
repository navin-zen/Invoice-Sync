"""
Get GSTIN details
"""

import click

if __name__ == "__main__":
    import django

    django.setup()

from invoicing.utils.gstnutils_invoicing import get_invoicing_gstin_detail


@click.command()
@click.option("--gstin-uuid", required=True, type=click.UUID, help="The UUID of the GSTIN")
@click.option("--gstin-string", required=True, help="The GSTIN to be queried")
def run(gstin_uuid, gstin_string):
    get_invoicing_gstin_detail(str(gstin_uuid), gstin_string)


if __name__ == "__main__":
    run()


