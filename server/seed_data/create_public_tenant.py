#!/usr/bin/env python


"""
Create a 'demo' schema.
"""

if __name__ == "__main__":
    import django

    django.setup()

from customers.models import Customer


def run():
    cleaned_data = {
        "schema_name": "public",
        "first_name": "Public",
        "last_name": "Public",
        "phone": "+919886560889",
        "referral_code": "",
        "organization": "Public Tenant",
        "email": "public-tenant@cloudzen.in",
    }
    c = Customer(**cleaned_data)
    c.full_clean()
    c.save()


if __name__ == "__main__":
    run()
