"""
Views related to GSTIN
"""

from crispy_forms.layout import Layout
from django import forms
from django.http.response import HttpResponseRedirect
from django.utils.functional import cached_property
from django.views.generic import FormView
from invoicing import breadcrumbs
from invoicing.models import GstIn, PermanentAccountNumber
from invoicing.utils.api.common import get_or_create_gstin
from invoicing.utils.count_purchase_sync import get_purchase_sync_count_json
from pygstn.utils.gstin import GstinUtils

from cz_utils.breadcrumbs import breadcrumbify
from cz_utils.common_forms import FormTemplateMixin
from cz_utils.crispy_forms_utils import Colsm4 as C4, Colsm8 as C8, CreateUpdateFormHelper, Row as R
from cz_utils.decorators import instance_from_get_object
from cz_utils.django.views.generic.detail import UuidDetailView
from cz_utils.utils import make_django_validator

__all__ = ("GstInDetail", "PermanentAccountNumberDetail", "GstInCreateSimple")


@breadcrumbify(breadcrumbs)
@instance_from_get_object("gstin")
class GstInDetail(UuidDetailView):
    model = GstIn

    @cached_property
    def invoice_count_details_list(self):
        return get_purchase_sync_count_json(self.object)


@breadcrumbify(breadcrumbs)
@instance_from_get_object("permanentaccountnumber")
class PermanentAccountNumberDetail(UuidDetailView):
    model = PermanentAccountNumber


class GstInCreateSimpleForm(forms.Form):
    gstin = forms.CharField(
        label="GSTIN",
        validators=[make_django_validator(GstinUtils.validate_gstin)],
        help_text="The 15-digit GSTIN Number",
    )
    name = forms.CharField(help_text="The name of the Taxpayer")


class GstInCreateSimpleFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(C4("gstin"), C8("name")),
    )


@breadcrumbify(breadcrumbs)
class GstInCreateSimple(FormTemplateMixin, FormView):
    view_description = "Create a GstIn object from Name and Number"
    cz_page_title = "New GSTIN"
    cz_form_css_class = ""
    cz_form_button_text = "Add GSTIN"
    form_class = GstInCreateSimpleForm
    form_helper = GstInCreateSimpleFormHelper()

    def form_valid(self, form):
        data = form.cleaned_data
        gstin = get_or_create_gstin(data["gstin"], data["name"])
        return HttpResponseRedirect(gstin.get_absolute_url())


