import functools

from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, BaseInput, Div, Field, Layout
from crispy_forms.utils import get_template_pack
from django import forms
from django.utils.crypto import get_random_string

Row = functools.partial(Div, css_class="row")
Colsm1 = functools.partial(Div, css_class="col-sm-1 md-form")
Colsm2 = functools.partial(Div, css_class="col-sm-2 md-form")
Colsm3 = functools.partial(Div, css_class="col-sm-3 md-form")
Colsm4 = functools.partial(Div, css_class="col-sm-4 md-form")
Colsm5 = functools.partial(Div, css_class="col-sm-5 md-form")
Colsm6 = functools.partial(Div, css_class="col-sm-6 md-form")
Colsm7 = functools.partial(Div, css_class="col-sm-7 md-form")
Colsm8 = functools.partial(Div, css_class="col-sm-8 md-form")
Colsm9 = functools.partial(Div, css_class="col-sm-9 md-form")
Colsm10 = functools.partial(Div, css_class="col-sm-10 md-form")
Colsm11 = functools.partial(Div, css_class="col-sm-11 md-form")
Colsm12 = ColFull = functools.partial(Div, css_class="col-sm-12 md-form")
TextArea = functools.partial(Field, css_class="md-textarea")


class H1(Div):
    template = "%s/layout/h1.html"


class H2(Div):
    template = "%s/layout/h2.html"


class H3(Div):
    template = "%s/layout/h3.html"


class H4(Div):
    template = "%s/layout/h4.html"


class H5(Div):
    template = "%s/layout/h5.html"


class H6(Div):
    template = "%s/layout/h6.html"


class Collapser(HTML):
    """
    A <a href="#"> link that can control a collapsible target

    Example:
        Collapser("Purchase Order Details", "#a4d821e89")
    """

    def __init__(self, text, target):
        html = """
        <a
            href="#" class="cz-collapse-controller collapsed"
            data-toggle="collapse" data-target="{target}">
            {text}
        </a>
        """.format(text=text, target=target)
        super().__init__(html)


class CollapseContainer(Div):
    """
    A Collapse link and a Div with elements inside it.
    """

    def __init__(self, title, *fields, **kwargs):
        identifier = f"c{get_random_string()}"
        new_fields = [
            H5(Collapser(title, f"#{identifier}")),
            Div(*fields, css_id=identifier, css_class=self.COLLAPSE_CSS_CLASS),
        ]
        super().__init__(*new_fields, **kwargs)


class CollapseContainerExposure(CollapseContainer):
    COLLAPSE_CSS_CLASS = "collapse show mt-2"


class CollapseContainerHidden(CollapseContainer):
    COLLAPSE_CSS_CLASS = "collapse mt-2"


class CreateUpdateFormHelper(FormHelper):
    form_tag = False


class Submit(BaseInput):
    """
    Used to create a Submit button descriptor for the {% crispy %} template tag::

        submit = Submit('Search the Site', 'search this site')

    .. note:: The first argument is also slugified and turned into the id for the submit button.

    Copied from crispy_forms.layout.Submit. We want to change the button
    color.
    """

    input_type = "submit"

    def __init__(self, *args, **kwargs):
        self.field_classes = "submit submitButton" if get_template_pack() == "uni_form" else "btn btn-info"
        super().__init__(*args, **kwargs)


class FilterFormHelper(FormHelper):
    # http://django-crispy-forms.readthedocs.io/en/latest/form_helper.html#helper-attributes-you-can-set
    form_tag = False
    form_id = "filter-form"
    form_class = "collapse"
    form_method = "get"

    def __init__(self, form=None):
        super().__init__(form)
        # HTML does not work within submit. Only plain text does
        # self.add_input(Submit('submit', mark_safe('<i class="fa fa-filter"></i> Filter')))
        self.add_input(Submit("submit", "Filter results"))


class DummyForm(forms.Form):
    """
    A form with a dummy field.

    We need this because crispy form helper needs atleast one field.
    Otherwise, bool(CreateUpdateFormHelper()) ends up being False, and our
    template does not show this form.
    """

    dummy = forms.CharField(required=False, widget=forms.HiddenInput)


class DummyFormHelper(CreateUpdateFormHelper):
    layout = Layout("dummy")


def simple_form_helper(fields, base_class=CreateUpdateFormHelper):
    """
    Generate simple form helper without much customization
    """

    class SimpleFormHelper(base_class):
        layout = Layout(
            Row(*[Colsm4(f) for f in fields]),
        )

    return SimpleFormHelper


def single_field_form_helper(field_name):
    """
    Generate formhelper for a form with a single field.
    """
    return simple_form_helper([field_name])
