"""
Utilities for Model validation.
"""

import datetime

from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import models
from django.db.models import ForeignKey, OneToOneField
from django.db.models.constants import LOOKUP_SEP

__all__ = (
    "validate_equal",
    "get_model_field",
    "validate_date_in_past",
)


def get_model_field(model, fieldspec):
    """
    Lookup a model's field traversing double underscores.

    fieldspec is usually a string representing a field specification.
    fieldspec can also be a tuple, in which case we get the spec from its
    contents.

    Traverses ForeignKey and OneToOneField relations. Returns a field
    object.

    Returns None if the lookup is invalid.

    Adapted from:
    https://github.com/alex/django-filter/blob/73a391adb27ef31047faf1a3497b562fd071f6cb/django_filters/filterset.py#L84
    """
    opts = model._meta
    if not isinstance(fieldspec, tuple):
        fieldspec = fieldspec.split(LOOKUP_SEP)
    rel = None
    for i, name in enumerate(fieldspec):
        if i > 0:
            if not isinstance(rel, (ForeignKey, OneToOneField)):
                return None
            opts = rel.related_model._meta
        try:
            (rel, _, _, _) = opts.get_field_by_name(name)
        except FieldDoesNotExist:
            return None
    return rel


def get_field(obj, fieldspec):
    """
    Get a field of 'obj'. fieldspec could traverse related fields through
    double underscore '__'.
    """
    for f in fieldspec.split(LOOKUP_SEP):
        if obj is None:
            break
        if not isinstance(obj, models.Model):
            raise TypeError("Expected a Django model")
        obj = getattr(obj, f, None)
    return obj


def validate_equal(obj, field1, field2, message):
    """
    Validate that obj.field1 is equal to obj.field2. field1 and field2 can
    refer to related objects through double underscore '__'. If validation
    fails, raise a ValidationError.
    """
    value1 = get_field(obj, field1)
    value2 = get_field(obj, field2)
    if (value1 is not None) and (value2 is not None) and (value1 != value2):
        raise ValidationError({field2.split(LOOKUP_SEP)[0]: message})


def validate_date_in_past(value):
    """Validate that a date is in the past."""
    if value > datetime.date.today():
        raise ValidationError("This date cannot be in the future.")
