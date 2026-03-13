import datetime
import io

import requests
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.fields.files import FieldFile

from cz_utils.django.forms.fields import CzDateField as CzDateFormField, CzRichTextField

# from cz_utils.storages.backends.s3boto import PROTECTED_STORAGE
from cz_utils.randomized_filename import get_randomized_filename

__all__ = (
    "TrimmedCharField",
    "CzUppercaseField",
    "CzDateField",
    "CzTextField",
    "CzForeignKey",
    "CzTaxPercentField",
    "CzHtmlTextField",
)


class TrimmedCharField(models.CharField):
    """
    A CharField with no leading or trailing spaces.
    """

    "default_validators = models.CharField.default_validators + [validate_proper_xml]"

    def __init__(self, *args, **kwargs):
        defaults = {"max_length": 255}
        defaults.update(**kwargs)
        super().__init__(*args, **defaults)

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        if value is not None:
            value = value.strip()
        return value


class CzHtmlTextField(models.TextField):
    """
    A text field that stores HTML text.

    This field's widget is a rich text editor.
    """

    def formfield(self, **kwargs):
        defaults = {"form_class": CzRichTextField}
        return super().formfield(**defaults)


class CzPositiveDecimalField(models.DecimalField):
    default_validators = models.DecimalField.default_validators + [MinValueValidator(0)]


class CzUppercaseField(TrimmedCharField):
    """
    Converts all values to upper case before storing them.
    """

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        if value is not None:
            value = value.upper()
        return value


class CzTextField(models.TextField):
    "default_validators = models.TextField.default_validators + [validate_proper_xml]"

    """A text field that stores HTML text.

    This field's widget is a rich text editor."""

    def formfield(self, **kwargs):
        defaults = {"form_class": CzRichTextField}
        return super(CzHtmlTextField, self).formfield(**defaults)


class CzDateField(models.DateField):
    """DateField that uses a date-picker widget by default."""

    def formfield(self, **kwargs):
        defaults = {"form_class": CzDateFormField}
        return super().formfield(**defaults)

    def validate_date_in_past(value):
        if value > datetime.date.today():
            raise ValidationError("This date cannot be in the future.")


class CzForeignKey(models.ForeignKey):
    """CloudZen's customized ForeignKey field.

    On top of Django's default ForeignKey field, this field defines
    on_delete=models.PROTECT. This way, we prevent deletion of related
    objects.

    The field also comes with a select2 widget by default.
    """

    def __init__(self, to, **kwargs):
        defaults = {
            "on_delete": models.PROTECT,
        }
        defaults.update(kwargs)
        super().__init__(to, **defaults)

    def formfield(self, **kwargs):
        defaults = {
            "widget": forms.Select(
                attrs={
                    "class": "select2-widget",
                }
            ),
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CzTaxPercentField(CzPositiveDecimalField):
    """A decimal field for tax percentage."""

    def __init__(self, *args, **kwargs):
        defaults = {
            "max_digits": 5,
            "decimal_places": 2,
        }
        defaults.update(**kwargs)
        super().__init__(*args, **defaults)


class CzFieldFile(FieldFile):
    def cz_get_url(self, response_headers=None):
        """
        Our customization of FieldFile._get_url with response_headers.
        """
        if response_headers is None:
            return self.url
        else:
            self._require_file()
            return self.storage.cz_url(self.name, response_headers=response_headers)


def upload_to(instance, filename):  # pylint: disable=unused-argument
    """
    Ensure unique filenames for files.

    This is to be used as the parameter 'upload_to' for CzFileField.
    https://docs.djangoproject.com/en/1.8/ref/models/fields/#django.db.models.FileField.upload_to
    """
    return get_randomized_filename(filename)


def file_obj_from_filefield(filefield):
    """
    Return a file object to read the contents of a file field
    """
    if not filefield:
        return None
    # The following lines don't work on AWS lambda and we get a 403
    # forbidden error. No idea as to why.
    #
    # filefield.open(mode='rb')
    # return fieldfield  # This works locally
    #
    # Instead, we download the file from S3 using a GET (this works
    # reliably)
    return io.BytesIO(requests.get(filefield.url).content)


"""class CzFileField(models.FileField):
    attr_class = CzFieldFile

    def __init__(self, **kwargs):
        defaults = {
            "upload_to": upload_to,
            "storage": PROTECTED_STORAGE,
            "max_length": 255,
        }
        defaults.update(kwargs)
        super(CzFileField, self).__init__(**defaults)"""


class CzImageField(models.ImageField):
    def __init__(self, **kwargs):
        defaults = {
            "upload_to": upload_to,
            # "storage": PROTECTED_STORAGE,
            "max_length": 255,
        }
        defaults.update(kwargs)
        super().__init__(**defaults)


def valid_xml_char_ordinal(c):
    # Check that c is a valid character for XML
    # As per http://stackoverflow.com/a/8735509
    codepoint = ord(c)
    # conditions ordered by presumed frequency
    return (
        (0x20 <= codepoint <= 0xD7FF)
        or (codepoint in (0x9, 0xA, 0xD))
        or (0xE000 <= codepoint <= 0xFFFD)
        or (0x10000 <= codepoint <= 0x10FFFF)
    )


def validate_proper_xml(value):
    if not all(valid_xml_char_ordinal(c) for c in value):
        raise ValidationError("This text contains invalid characters.")
