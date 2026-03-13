"""
Forms and templates for common use cases (Create item, Update item, Filter
a list of items)
"""

import base64

from django import forms
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model, Q
from django.forms.models import modelform_factory
from django.http import Http404, QueryDict
from django.shortcuts import get_object_or_404
from django.urls import reverse

from config.customizations.django.utils.functional import cached_property
from cz_utils.url_utils import CZ_HIDDEN_PREFIX, CZ_INITIAL_PREFIX


def rewrite_object_values(d):
    """
    We want to prepare a data dictionary suitable for POST parameters in a
    test or form initial values in a view.

    This replaces objects with their primary key. In the future, it will
    replace with the UUID.
    """
    for k, v in d.items():
        if isinstance(v, Model):
            d[k] = v.pk
    return d


def form_hidden_object_mixin_factory(model=None, var_name=""):
    """
    Factory for forms that accept a hidden related object.
    """

    class FormHiddenObjectMixin:
        """
        In forms in various create and update views, some of the form values
        are populated and hiddedn when the form is created. The user does not
        have to fill in this field. For example, when creating a shipment, we
        know that is for a particular purchase order. The purchase_order
        parameter of the form is set during form initialization.

        This mixin provides support for finding this related object either from
        URL query parameters (in the case of a CreateView) or from the object
        itself (in the case of an UpdateView).

        This mixin has a field raise_404_if_set_in_stone whose value
        controls whether to raise a 404 if the hidden object is frozen
        (i.e. set in stone). The default value of raise_404_if_set_in_stone
        is True. Override it to False if you don't want this behavior in
        your class.
        """

        hidden_object_model = model
        hidden_object_context_name = var_name
        hidden_object_uuid_query_param = f"{var_name}_uuid" if var_name else ""
        hidden_object_field_name = var_name
        # If the obj is frozen (i.e. set in stone), don't allow creation or
        # updation of a related object.
        raise_404_if_set_in_stone = True

        def get_initial(self):
            # Hidden initial data gets highest precedence
            initial = super().get_initial()
            initial.update(self.get_hidden_initial_form_data())
            return initial

        def get_form_widgets(self):
            widgets = super().get_form_widgets()
            widgets.update({self.hidden_object_field_name: forms.HiddenInput()})
            return widgets

        def get_hidden_object_from_object(self):
            if not hasattr(self, "object"):
                return None
            if not self.object:
                return None
            if not self.hidden_object_field_name:
                raise ImproperlyConfigured(
                    "FormHiddenObjectMixin requires the definition of 'hidden_object_field_name'"
                )
            return getattr(self.object, self.hidden_object_field_name)

        def get_hidden_object_from_url(self):
            if not (self.hidden_object_uuid_query_param and self.hidden_object_model):
                raise ImproperlyConfigured(
                    "FormHiddenObjectMixin requires the definition of 'hidden_object_uuid_query_param'"
                    " and 'hidden_object_model'"
                )
            if not self.hidden_object_field_name:
                raise ImproperlyConfigured(
                    "FormHiddenObjectMixin requires the definition of 'hidden_object_field_name'"
                )
            # The object's field still has an integer ID and not UUID
            # When it becomes UUID, the POST and GET code will look the same
            pk = self.request.POST.get(self.hidden_object_field_name, None)
            if isinstance(pk, str):
                try:
                    pk = int(pk)
                except ValueError:
                    pk = None
            if pk:
                return get_object_or_404(self.hidden_object_model, pk=pk)
            uuid = self.request.GET.get(self.hidden_object_uuid_query_param, None)
            if uuid:
                return get_object_or_404(self.hidden_object_model, uuid=uuid)
            raise Http404("Could not find (hidden) related object")

        def get_hidden_initial_form_data(self):
            if not self.hidden_object_field_name:
                raise ImproperlyConfigured(
                    "FormHiddenObjectMixin requires the definition of 'hidden_object_field_name'"
                )
            return {
                self.hidden_object_field_name: self.hidden_object,
            }

        def get_hidden_context_data(self):
            if not self.hidden_object_context_name:
                raise ImproperlyConfigured(
                    "FormHiddenObjectMixin requires the definition of 'hidden_object_context_name'"
                )
            return {
                self.hidden_object_context_name: self.hidden_object,
            }

    def hidden_object(self):
        obj = self.get_hidden_object_from_object() or self.get_hidden_object_from_url()
        if self.raise_404_if_set_in_stone and getattr(obj, "is_set_in_stone", None):
            raise Http404
        return obj

    setattr(FormHiddenObjectMixin, "hidden_object", cached_property(hidden_object, name="hidden_object"))
    if var_name:
        setattr(FormHiddenObjectMixin, var_name, cached_property(hidden_object, name=var_name))
    return FormHiddenObjectMixin


FormHiddenObjectMixin = form_hidden_object_mixin_factory(model=None, var_name="")


class FormTemplateMixin:
    help_texts = None
    cz_extra_form_buttons = []
    hidden_fields = []
    extra_required_fields = []
    extra_optional_fields = []
    base_template_name = "base.html"
    field_classes = None
    formfield_callback = None

    def add_success_message(self):
        """
        Add a message upon success (with an AJAX view).
        """
        pass

    def get_success_url(self):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            self.add_success_message()
            return reverse("cz_utils:success_view")
        else:
            return super().get_success_url()

    def get_template_names(self):
        if self.request.headers.get("x-requested-with") == "XMLHttpRequest":
            assert False
            return ["cz_utils/common_form_only.html"]
        else:
            return ["cz_utils/common_form_template.html"]

    @cached_property
    def cz_page_title(self):
        return f"{self.model._meta.app_label.capitalize()} : Add/Edit {self.model._meta.verbose_name.title()}"

    @cached_property
    def cz_form_js_template(self):
        return ""

    @cached_property
    def cz_related_object_template(self):
        return ""

    @cached_property
    def cz_related_object_url(self):
        return ""

    @cached_property
    def cz_form_message_text(self):
        return ""

    @cached_property
    def cz_form_button_text(self):
        return ""

    @cached_property
    def cz_form_method(self):
        return ""

    @cached_property
    def cz_form_css_class(self):
        return "form"
        # returning the above string only because we haven't created a model and hence that returned an error
        return f"{self.model._meta.app_label}-{self.model.__name__.lower()}-form"

    @cached_property
    def cz_inline_formset_header(self):
        return ""

    def get_form_class(self):
        if self.form_class:
            return self.form_class
        return modelform_factory(
            self.model,
            form=self.modelform_baseclass,
            fields=self.fields,
            widgets=self.get_form_widgets(),
            labels=self.get_form_labels(),
            help_texts=self.help_texts,
            field_classes=self.field_classes,
            formfield_callback=self.formfield_callback,
        )

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for f in self.extra_required_fields:  # Fields explicitly marked as required
            if f in form.fields:
                form.fields[f].required = True
        for f in self.extra_optional_fields:  # Fields explicitly marked as optional
            if f in form.fields:
                form.fields[f].required = False
        return form

    modelform_baseclass = forms.ModelForm

    def get_initial(self):
        # Give lower precedence to URL arguments than that given to super()
        initial = {
            k[len(CZ_INITIAL_PREFIX) :]: v for (k, v) in self.request.GET.items() if k.startswith(CZ_INITIAL_PREFIX)
        }
        initial.update(super().get_initial())
        return initial

    def get_form_widgets(self):
        widgets = {}
        widgets.update(
            (k[len(CZ_HIDDEN_PREFIX) :], forms.HiddenInput())
            for (k, v) in self.request.GET.items()
            if (k.startswith(CZ_HIDDEN_PREFIX) and v)
        )
        widgets.update((f, forms.HiddenInput()) for f in self.hidden_fields)
        return widgets

    def get_form_labels(self):
        return {}


class ObjectListFilterMixin:
    """
    A generic way to specify filtering criteria in a `ListView`.

    When you have a `ListView` and want to provide the user with a
    filtering functionality, simply extend this class
    `ObjectListFilterMixin` and override `filter_form_class`.

    The template will have access to `view.filter_form` which will display
    the form for the user to make a selection and the view code can use
    `self.filter_form_qobj` to filter the queryset to choose objects
    matching the user specified criterion.

    Include this in your template as:
        {% include 'cz_utils/common_filter_form.html' with filter_form=view.filter_form %}
    """

    filter_form_helper = None

    @cached_property
    def filter_form_class(self):
        raise NotImplementedError(f"{self.__class__.__name__}.filter_form_class")

    @cached_property
    def url_has_params(self):
        """
        Whether the user has passed any parameters in the URL querystring
        """
        return any((f in self.request.GET) for f in self.filter_form_class.declared_fields.keys())

    filter_form_initial = {}

    @cached_property
    def filter_form(self):
        workaround = self.request.GET.get("apigatewayworkaround")
        if workaround:
            try:
                if isinstance(workaround, str):
                    workaround = workaround.encode("ascii")  # Because this will be base64 encoded
                workaround = QueryDict(base64.b64decode(workaround))
            except Exception:
                workaround = None
        return self.filter_form_class(workaround or self.request.GET or self.filter_form_initial)

    @cached_property
    def filter_form_data(self):
        form = self.filter_form
        if form.is_valid():
            return form.cleaned_data
        else:
            raise Http404("Filter form is not valid")

    def filter_form_qobj_with_lookup_map(self, lookup_map={}):
        qobj = Q()
        data = self.filter_form_data
        if not data:
            return qobj
        for field, lookup, transform in self.filter_form_lookups:
            if not transform:
                transform = lambda x: x  # NOQA
            value = data[field]
            lookup = lookup_map.get(lookup, lookup)
            if not lookup:
                continue
            # value being False is a queryable value for boolean fields.
            if (value is not False) and not value:
                continue
            value = transform(value)
            # None as a query is allowed only for __exact and __iexact
            if (value is not None) or lookup.endswith("__exact") or lookup.endswith("__iexact"):
                qobj = qobj & Q(**{lookup: value})
        return qobj

    @cached_property
    def filter_form_qobj(self):
        return self.filter_form_qobj_with_lookup_map()

    filter_form_excluded_fields = []

    @cached_property
    def filter_form_lookups(self):
        """
        Override this function to specify the lookups you want, based on
        how you want to filter.

        As an example, something like:
            return [
                ('vendor',        'vendor__pk__in',        lambda x: x.values_list('pk', flat=True)),
                ('purchaseorder', 'purchaseorder__pk__in', lambda x: x.values_list('pk', flat=True)),
                ('number',        'number__icontains',     lambda x: x),
                ('project',       'project__pk__in',       lambda x: x.values_list('pk', flat=True)),
            ]
        """
        fields = filter(lambda f: f not in self.filter_form_excluded_fields, self.filter_form_class.declared_fields)
        return [(i, i, None) for i in fields]
