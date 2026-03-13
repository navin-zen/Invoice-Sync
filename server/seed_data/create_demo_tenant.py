#!/usr/bin/env python


"""
Create a 'demo' schema.
"""

if __name__ == "__main__":
    import django

    django.setup()

from customers.utils.new_signup import DemoSignup


def run():
    cleaned_data = {
        "first_name": "Demo",
        "last_name": "User",
        "phone": "+919886560889",
        "referral_code": "",
        "organization": "Demo Company",
        "password": "demo",
        "password1": "demo",
        "email": "demo@cloudzen.in",
        "language": "en",
    }
    DemoSignup.do_all(cleaned_data, "")


if __name__ == "__main__":
    run()
