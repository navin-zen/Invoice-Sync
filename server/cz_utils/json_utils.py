"""
Utilities related to JSON objects.
"""

import decimal
import json
import uuid
from functools import wraps

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.encoding import force_str


class JSONEncoder(DjangoJSONEncoder):
    """
    Our customization of Django's JSON Encoder
    """

    def default(self, o):
        if isinstance(o, bytes):
            return o.decode("utf-8")
        if isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, models.Model) and hasattr(o, "uuid"):
            return force_str(o.uuid)
        elif isinstance(o, uuid.UUID):
            return force_str(o)
        else:
            return super().default(o)


def validate_json(validator, encoder=JSONEncoder, strict=True):
    """
    Decorator that wraps a function and validates that the function returns
    a value that conforms to the schema of the `validator`.

    Usage:
        @validate_json(AddressValidator)
        def address():
            return {
                "name": "CloudZen Software Labs Private Limited",
            }
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            r = fn(*args, **kwargs)
            r = json.loads(json.dumps(r, cls=encoder))
            try:
                validator(r)
            except Exception:
                if strict:
                    raise
            return r

        return wrapper

    return decorator
