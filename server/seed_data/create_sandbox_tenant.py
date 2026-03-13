#!/usr/bin/env python


"""
Create a 'demo' schema.
"""

if __name__ == "__main__":
    import django

    django.setup()

from customers.utils.new_signup import SandboxSignup


def run():
    cleaned_data = {
        "first_name": "Suriya",
        "last_name": "Subramanian",
        "phone": "+919886560889",
        "referral_code": "",
        "organization": "Demo Company",
        "password": "password",
        "password1": "password",
        "email": "suriya+sandbox@cloudzen.in",
    }
    SandboxSignup.do_all(cleaned_data, "")


if __name__ == "__main__":
    run()
