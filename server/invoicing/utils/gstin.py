"""
Utilities related to GST numbers
"""

import string

from django.utils.crypto import get_random_string
from pygstn.utils.gstin import GstinUtils

from taxmaster.models import State


def random_pan():
    """
    Returns a random PAN.
    """
    return "".join(
        [
            get_random_string(length=3, allowed_chars=string.ascii_uppercase),
            "C",
            get_random_string(length=1, allowed_chars=string.ascii_uppercase),
            get_random_string(length=4, allowed_chars=string.digits),
            get_random_string(length=1, allowed_chars=string.ascii_uppercase),
        ]
    )


def random_gstin(state=None):
    """
    Returns a random GSTIN.
    """
    gstin_without_checkdigit = "".join(
        [
            (state or State.objects2.first()).code,
            random_pan(),
            "1Z",
        ]
    )
    checkdigit = GstinUtils.getCheckDigit(gstin_without_checkdigit)
    return gstin_without_checkdigit + checkdigit


