import decimal
import random

import six
from django import template
from django.template.defaultfilters import stringfilter, truncatechars
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from num2words import num2words as num2wordsfunc
from pygstn.utils import json

from cz_utils.django.forms.widgets import XlsUploadTypeRadioSelect
from cz_utils.json_utils import JSONEncoder

register = template.Library()


class VarExistsNode(template.Node):
    """
    Construct a node that checks the definition of variables
    """

    def __init__(self, variables):
        self.variables = [template.Variable(v) for v in variables]

    def render(self, context):
        missing = []
        for v in self.variables:
            try:
                v.resolve(context)
            except template.VariableDoesNotExist:
                missing.append(str(v))
        if missing:
            raise template.VariableDoesNotExist("Missing required variables: {}".format(", ".join(missing)))
        return ""


@register.tag
def cz_var_exists(parser, token):
    """
    Checks the presence of variables in the context.

    ::

        {% cz_var_exists var1 var2 ... %}

    If the specified variables are not defined, raises an exception. This
    will show up as a 500 error.
    """
    try:
        tokens = token.split_contents()
        variables = tokens[1:]
    except ValueError:
        raise template.TemplateSyntaxError("cz_var_exists is not properly defined")
    return VarExistsNode(variables)


@register.inclusion_tag("cz_utils/js_constants.html", takes_context=True)
def js_constants(context):
    return {
        # "PUSHER_KEY": settings.PUSHER_KEY,
        # "PUSHER_CLUSTER": settings.PUSHER_CLUSTER,
        "CSRF_TOKEN": context.get("csrf_token", ""),
    }


@register.filter(needs_autoescape=True)
@stringfilter
def cz_truncatechars(value, arg, autoescape=True):
    """
    Truncates a string after a certain number of characters.

    Argument: Number of characters to truncate after.

    This an improvement over Django's default `truncatechars` filter in
    that it adds a <span> tag with a tooltip showing the un-truncated text.
    """
    try:
        length = int(arg)
    except ValueError:  # Invalid literal for int().
        return truncatechars(value, arg)  # Call the default truncatechars
    esc = conditional_escape if autoescape else (lambda x: x)
    value = truncatechars(value, six.MAXSIZE)
    if len(value) <= length:
        return value
    truncated_value = truncatechars(value, length)
    result = f'<span rel="tooltip" title="{esc(value)}">{esc(truncated_value)}</span>'
    return mark_safe(result)


@register.filter
def cz_checkmark(value):
    """
    Show a checkmark based on the value.
    """
    if value:
        return mark_safe('<i style="color: #4cae4c; font-size: 1.4em;" class="fa fa-check-circle"></i>')
    else:
        return ""


@register.filter
def cz_check_cross(value):
    """
    Show a checkmark or cross on the value.
    """
    if value:
        return mark_safe('<i style="color: #4cae4c; font-size: 1.4em;" class="fa fa-check-circle"></i>')
    else:
        return mark_safe('<i style="color: red; font-size: 1.4em;" class="fa fa-times-circle"></i>')


@register.filter
def get_object_model_name(value):
    return value._meta.model_name


@register.filter
def get_object_app_label(value):
    return value._meta.app_label


@register.filter
def verbose_name(obj):
    """
    Our customization of Django's verbose_name
    """
    try:
        vname = obj._meta.verbose_name
        return "".join(min(x, y) for (x, y) in zip(vname, vname.title()))
    except Exception:
        return ""


@register.filter
def is_xlsupload_radioselect(field):
    """
    Whether the field uses our custom RadioSelect widget used for choosing
    the type of XLS upload (with appropriate image) in the upload page.

    See
        cz_utils/django/forms/widgets.py
        cz_utils/templatetags/cloudzen_extras.py
        gstcomply/templates/bootstrap4/field.html
        gstcomply/templates/bootstrap4/xlsupload_radioselect.html
    """
    return isinstance(field.field.widget, XlsUploadTypeRadioSelect)


@register.filter
def cz_json(d, indent=2):
    """
    Render JSON object.

    Pass indent=None to display in a single line.
    """
    return json.dumps(d, indent=indent, cls=JSONEncoder)


@register.filter
def num2words(value, lang="en_IN"):
    if isinstance(value, str):
        if not value:
            return value
        value = decimal.Decimal(value)
    try:
        words = num2wordsfunc(value, lang=lang)
    except OverflowError:
        words = num2wordsfunc(value, lang="en")
    return words.capitalize().replace("-", " ")


@register.filter
def get_message_array(messages):
    message_array = []
    for message in messages:
        message_description = message.message
        tag = message.tags
        id = f"{message_description.strip().lower().replace(' ', '-')}-{random.randint(1000, 9999)}"
        message_array.append(dict(id=id, message=message_description, tag=tag))
    return message_array
