"""
Clone a configuration into another with a different name
"""

import click
import django

if __name__ == "__main__":
    django.setup()

from invoicing.models import Configuration


@click.command()
@click.option(
    "--config-uuid",
    required=True,
    type=click.UUID,
    help="The UUID of the configuration object that needs to be cloned",
)
@click.option("--site-name", required=True, help="The name of the new configuration object")
@click.option("--view-name", required=True, help="The view that should be used for this config")
@click.option("--enable-autosync", is_flag=True, help="Whether to enable autosync")
def main(config_uuid, site_name, view_name, enable_autosync):
    old_metadata = Configuration.objects2.get(uuid=config_uuid).metadata
    old_metadata["datamapping"]["table"] = view_name
    clone = Configuration(site_name=site_name, enable_autosync=enable_autosync, metadata=old_metadata)
    clone.full_clean()
    clone.save()


if __name__ == "__main__":
    main()


