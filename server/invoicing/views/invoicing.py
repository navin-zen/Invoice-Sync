import json
import logging

import requests
from crispy_forms.layout import Field, Layout
from django import forms
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView, TemplateView, View
from invoicing import breadcrumbs
from invoicing.models import CachedData, GlobalConfiguration, GstIn, PurchaseInvoice
from invoicing.utils.count_purchase_sync import get_purchase_sync_count_json
from invoicing.utils.jsonschemas.sync_invoices import (
    SyncInvoicesEntrypointValidator,
    SyncInvoicesResponseValidator,
    SyncInvoicesStatusResponseValidator,
)
from invoicing.utils.purchase_invoice_generation import fetch_purchase_invoices_for_session
from invoicing.utils.sync_session_summary import get_sync_details

from cz_utils.allauth.account.utils import get_next_redirect_url
from cz_utils.breadcrumbs import breadcrumbify
from cz_utils.common_forms import FormTemplateMixin
from cz_utils.crispy_forms_utils import Colsm6 as C6, CreateUpdateFormHelper, Row as R
from cz_utils.decorators import instance_from_get_object, instance_from_url_uuid
from cz_utils.django.views.generic.detail import UuidDetailView
from cz_utils.json_utils import JSONEncoder, validate_json
from cz_utils.text_utils import squeeze_space

logger = logging.getLogger(__name__)

__all__ = (
    "Home",
    "InvoiceList",
    "PurchaseSyncEstablishLoginSession",
    "SyncPurchaseInvoicesStartSession",
    "SyncPurchaseInvoices",
    "SyncPurchaseInvoicesStatus",
    "SyncSessionStatus",
    "SyncSessionFeedback",
    "InvoiceCountStatus",
)


@breadcrumbify(breadcrumbs)
class Home(TemplateView):
    template_name = "invoicing/index.html"

    @property
    def gstin_list(self):
        return GstIn.objects2.all()

    @property
    def globalconfiguration(self):
        return GlobalConfiguration.get_solo()

    @cached_property
    @validate_json(SyncInvoicesEntrypointValidator)
    def sync_invoices_ts_args(self):
        return {
            "id": "sync-invoices-react-app",
            "syncUrl": reverse("invoicing:sync_purchase_invoices_start_session"),
        }

    @cached_property
    def invoice_count_details_list(self):
        return get_purchase_sync_count_json()

    @cached_property
    def purchasinvoicing_list(self):
        return PurchaseInvoice.objects2.order_by("-date")[:100]


class InvoiceList(TemplateView):
    template_name = "invoicing/invoice_list.html"

    @cached_property
    def purchasinvoicing_list(self):
        return PurchaseInvoice.objects2.order_by("-date")[:100]


class PurchaseSyncLoginForm(forms.Form):
    username = forms.CharField(
        label="Purchase Sync API Portal Username",
        required=True,
        help_text=squeeze_space(
            """The username of your account in the
        Purchase Sync portal."""
        ),
    )
    password = forms.CharField(
        label="Purchase Sync API Portal Password",
        required=True,
        widget=forms.PasswordInput(render_value=True),
        help_text=squeeze_space(
            """The password of your account in the
        Purchase Sync portal."""
        ),
    )
    clientid = forms.CharField(
        label="Purchase Sync Client ID",
        required=True,
        help_text=squeeze_space(
            """Client ID of your account in the
        Purchase Sync portal."""
        ),
    )
    client_secret = forms.CharField(
        label="Purchase Sync Client Secret Key",
        required=True,
        help_text=squeeze_space(
            """Client Secret key of your account in the
        Purchase Sync portal."""
        ),
    )


class PurchaseSyncFormHelper(CreateUpdateFormHelper):
    layout = Layout(
        R(
            C6(Field("username", autocomplete="off")),
            C6(Field("password", autocomplete="off")),
            C6(Field("clientid", autocomplete="off")),
            C6(Field("client_secret", autocomplete="off")),
        )
    )


@breadcrumbify(breadcrumbs, "gstin")
@instance_from_url_uuid(GstIn)
class PurchaseSyncEstablishLoginSession(FormTemplateMixin, FormView):
    view_description = "Purchase Sync Login Session"
    form_class = PurchaseSyncLoginForm
    form_helper = PurchaseSyncFormHelper()
    cz_form_button_text = "Login"
    cz_submit_button_class = "btn btn-success"
    cz_page_title = "Confirm Purchase Sync"
    cz_form_css_class = ""
    gstin: GstIn

    def get_local_permission_object(self):
        return self.gstin

    def get_initial(self):
        initial = super().get_initial()
        initial.update(
            {
                "username": self.gstin.purchase_sync_username,
                "password": self.gstin.purchase_sync_password,
                "clientid": self.gstin.purchase_sync_client_id,
                "client_secret": self.gstin.purchase_sync_client_secret,
            }
        )
        return initial

    def form_valid(self, form):
        data = form.cleaned_data
        self.gstin.purchase_sync_username = data["username"].strip()
        self.gstin.purchase_sync_password = data["password"].strip()
        self.gstin.purchase_sync_client_id = data["clientid"].strip()
        self.gstin.purchase_sync_client_secret = data["client_secret"].strip()
        self.gstin.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Successfully logged in to the Purchase Sync API Portal")
        return get_next_redirect_url(self.request) or self.gstin.get_absolute_url()


@method_decorator(csrf_exempt, name="dispatch")
class SyncPurchaseInvoicesStartSession(View):
    def post(self, request, *args, **kwargs):
        cd = CachedData(datatype=CachedData.DT_PURCHASE_SESSION_MARKER)
        cd.full_clean()
        cd.save()
        data = {
            "session_uuid": str(cd.uuid),
            "urls": {
                "sync_invoices": reverse("invoicing:sync_purchase_invoices", args=[cd.uuid]),
                "status": reverse("invoicing:sync_purchase_invoices_status", args=[cd.uuid]),
            },
        }
        SyncInvoicesResponseValidator(data)
        return JsonResponse(data)


@method_decorator(csrf_exempt, name="dispatch")
@instance_from_url_uuid(CachedData)
class SyncPurchaseInvoices(View):
    cacheddata: CachedData

    def post(self, request, *args, **kwargs):
        fetch_purchase_invoices_for_session(session_uuid=str(self.cacheddata.uuid))
        return JsonResponse({})


@instance_from_get_object("session")
class SyncPurchaseInvoicesStatus(UuidDetailView):
    model = CachedData
    session: CachedData

    @cached_property
    @validate_json(SyncInvoicesStatusResponseValidator, strict=settings.DEBUG)
    def status(self):
        errors = CachedData.objects2.filter(group=self.session, datatype=CachedData.DT_PURCHASE_ERRORS).youngest()
        return {
            "completed": CachedData.objects2.filter(
                group=self.session, datatype=CachedData.DT_PURCHASE_FINISH
            ).exists(),
            "errors": (errors and errors.data_json) or [],
        }

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(self.status)


class SyncSessionStatus(View):
    def get(self, request, *args, **kwargs):
        sync_status = get_sync_details()
        return JsonResponse(sync_status, encoder=JSONEncoder, safe=False)


class SyncSessionFeedback(View):
    def get_sync_feedback(self):
        return get_sync_details()

class InvoiceCountStatus(View):
    def get(self, request, *args, **kwargs):
        from invoicing.utils.count_purchase_sync import get_purchase_sync_count_json
        invoice_count = get_purchase_sync_count_json()
        return JsonResponse(invoice_count, encoder=JSONEncoder, safe=False)


