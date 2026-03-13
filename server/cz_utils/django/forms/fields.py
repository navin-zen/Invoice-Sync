from django import forms
from django.contrib.postgres.forms import DateRangeField

from cz_utils.django.forms.widgets import CzDateInput, CzDateInputForRange

__all__ = (
    "CzDateField",
    "CzRichTextField",
    "CzChoiceField",
    "CzTypedChoiceField",
    "CzTypedMultipleChoiceField",
)


class CzDateField(forms.DateField):
    widget = CzDateInput


class CzDateFieldForRange(forms.DateField):
    """
    A DateField to be used as one of the fields of CzDateForRangeField
    """

    widget = CzDateInputForRange


class CzDateRangeField(DateRangeField):
    base_field = CzDateFieldForRange


class CzChoiceField(forms.ChoiceField):
    widget = forms.Select({"class": "select2-widget"})


class CzRichTextField(forms.CharField):
    def widget_attrs(self, widget):
        default = {"class": "richtext"}
        default.update(super().widget_attrs(widget))
        return default


class CzTypedChoiceField(forms.TypedChoiceField):
    widget = forms.Select({"class": "select2-widget"})


class CzTypedMultipleChoiceField(forms.TypedMultipleChoiceField):
    def __init__(self, **kwargs):
        cz_data_placeholder = kwargs.pop("cz_data_placeholder", "")
        defaults = {
            "widget": forms.SelectMultiple(
                {
                    "class": "select2-widget",
                    "data-placeholder": cz_data_placeholder,
                }
            ),
        }
        defaults.update(kwargs)
        super().__init__(**defaults)
