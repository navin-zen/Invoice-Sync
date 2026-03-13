#!/usr/bin/env python


"""
Populate all models in cz_permissions for a particular tenant

This utility function will be invoked while creating a new Customer as
well.
"""

import logging

if __name__ == "__main__":
    import django

    django.setup()

import click
from django.contrib.contenttypes.models import ContentType

from customers.models import Customer
from cz_permissions.models import ADMIN, FILER, READER, WRITER, Role
from taxpayer.models import GstIn, PermanentAccountNumber

logger = logging.getLogger(__name__)


class PopulatePermsConfig:
    PAN_ROLES = [
        # Order, is_admin, codename, description
        (100, False, FILER, "Can sign and file Tax returns"),
        (
            200,
            False,
            WRITER,
            "Role with write permission. Can save Invoices, Payments, Credit/Debit Notes.",
        ),
        (
            300,
            False,
            READER,
            "Role with read-only permission. Cannot make any modifications",
        ),
    ]

    GLOBAL_ROLES = [
        # Order, is_admin, codename, description
        (100, True, ADMIN, "An Administrator"),
    ]

    def update_roles(self, spec, model):
        """
        Update the roles associated with a model.
        """
        for order, is_admin, codename, name in spec:
            (role, created) = Role.objects2.update_or_create(
                defaults=dict(
                    order=order,
                    is_admin=is_admin,
                    name=name,
                ),
                codename=codename,
            )
            role.models.add(ContentType.objects.get_for_model(model))
            logger.info("{} Role {}".format("Created" if created else "Updated", role))

    def do_all(self):
        self.update_roles(self.PAN_ROLES, PermanentAccountNumber)
        self.update_roles(self.PAN_ROLES, GstIn)
        self.update_roles(self.GLOBAL_ROLES, Customer)


@click.command()
def run():
    PopulatePermsConfig().do_all()


if __name__ == "__main__":
    run()
