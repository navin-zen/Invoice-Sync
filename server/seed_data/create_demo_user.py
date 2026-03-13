#!/usr/bin/env python


"""
Create a User in the 'demo' schema
"""

if __name__ == "__main__":
    import django

    django.setup()

from django.contrib.auth.models import User
from gstcomply.customizations.django_tenants.utils import schema_context


def run():
    if User.objects.exists():
        return
    u = User(first_name="Suriya", last_name="Subramanian", username="suriya@cloudzen.in", email="suriya@cloudzen.in")
    u.set_password("password")
    u.full_clean()
    u.save()


if __name__ == "__main__":
    with schema_context("demo"):
        run()
