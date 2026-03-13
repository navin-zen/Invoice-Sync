"""
Django widgets customized by CloudZen.
"""

from django.forms import widgets

__all__ = (
    "CzDateInput",
    "CzDateInputForRange",
)


class CzDateInput(widgets.DateInput):
    def __init__(self, attrs=None):
        default_attrs = {"class": "datepicker"}
        default_attrs.update(attrs or {})
        super().__init__(default_attrs)


class CzDateInputForRange(widgets.DateInput):
    def __init__(self, attrs=None):
        default_attrs = {
            "class": "datepicker datepickerwithinrange",
        }
        default_attrs.update(attrs or {})
        super().__init__(default_attrs)


class XlsUploadTypeRadioSelect(widgets.RadioSelect):
    """
    Used in XLS upload/importer for the user to choose the type of XLS file
    (shown with an image).

    See
        cz_utils/django/forms/widgets.py
        cz_utils/templatetags/cloudzen_extras.py
        gstcomply/templates/bootstrap4/field.html
        gstcomply/templates/bootstrap4/xlsupload_radioselect.html
    """

    pass
