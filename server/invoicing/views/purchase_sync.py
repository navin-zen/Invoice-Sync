"""
Views related to Purchase Invoice synchronization and listing
"""

import logging
import operator
import itertools

from django.db.models.query_utils import Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import View, ListView
from django import forms
from django.views.decorators.csrf import csrf_exempt
from crispy_forms.layout import Layout

from invoicing import breadcrumbs
from invoicing.models import CachedData, Configuration, GstIn, PermanentAccountNumber, PurchaseInvoice
from invoicing.utils.purchase_invoice_generation import fetch_purchase_invoices_for_session
from invoicing.utils.purchase_gstzen_cloud import post_all_purchases_to_gstzen
from invoicing.utils.purchase_json_to_db import PurchaseUploader
from cz_utils.decorators import instance_from_get_object, instance_from_url_uuid
from cz_utils.breadcrumbs import breadcrumbify
from cz_utils.common_forms import ObjectListFilterMixin
from cz_utils.crispy_forms_utils import Colsm4 as C4, FilterFormHelper, Row as R
from cz_utils.django.forms.fields import CzDateRangeField, CzTypedMultipleChoiceField
from cz_utils.django.views.generic.detail import UuidDetailView

logger = logging.getLogger(__name__)

# Duplicate views removed to avoid shadowing invoicing.views.invoicing



@method_decorator(csrf_exempt, name="dispatch")
class AnyPostPurchase(View):
    view_description = "Post Purchase Invoice"
    http_method_names = ["post"]
    gstin = None
    purchase_data = None

    def dispatch(self, request, *args, **kwargs):
        return PurchaseUploader.handle_dispatch(self, request, *args, **kwargs) or super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return PurchaseUploader.handle_post(self.gstin, self.purchase_data, kwargs)


@method_decorator(csrf_exempt, name="dispatch")
class PurchaseJsonPost(AnyPostPurchase):
    view_description = "Post Purchase Invoice JSON"


class InvoiceFilterFormHelper(FilterFormHelper):
    layout = Layout(
        R(C4("number__icontains"), C4("date_range"), C4("purchase_status__in")),
    )


class InvoiceFilterMixin(ObjectListFilterMixin):
    filter_form_excluded_fields = [
        "date_range",
    ]

    def filter_form_qobj_date_range(self, date_range):
        qobj = Q()
        lower = date_range.lower
        if lower:
            qobj &= Q(date__gte=lower)
        upper = date_range.upper
        if upper:
            qobj &= Q(date__lte=upper)
        return qobj

    @cached_property
    def filter_form_qobj(self):
        qobj = super().filter_form_qobj
        data = self.filter_form_data
        date_range = data["date_range"]
        if date_range:
            qobj &= self.filter_form_qobj_date_range(date_range)
        return qobj

    @cached_property
    def filter_form_class(self):
        class FilterForm(forms.Form):
            number__icontains = forms.CharField(
                required=False,
                label="Invoice number search",
                help_text="Search for Invoice by Number",
            )
            date_range = CzDateRangeField(
                required=False,
                label="Date",
                help_text="Specify a date range (YYYY-MM-DD format) to filter by the invoice date.",
            )
            purchase_status__in = CzTypedMultipleChoiceField(
                required=False,
                coerce=int,
                label="Sync Status",
                help_text="Filter based on the type of Sync Status",
                cz_data_placeholder="Filter based on the type of Sync Status",
                choices=PurchaseInvoice.PURCHASE_STATUS_CHOICES,
            )
        return FilterForm


class InvoiceListMixin(InvoiceFilterMixin, ListView):
    model = MODEL = PurchaseInvoice
    paginate_by = 100
    ordering = ("-date", "-number")
    context_object_name = "purchasinvoicing_list"
    template_name = "invoicing/purchase_invoice/purchase_invoice_list.html"
    filter_form_helper = InvoiceFilterFormHelper()

    def filter_by_gstin(self, qs):
        return qs

    @cached_property
    def unfiltered_queryset(self):
        return self.filter_by_gstin(PurchaseInvoice.objects2).order_by(*self.ordering)

    def get_queryset(self):
        return self.unfiltered_queryset.filter(self.filter_form_qobj)


@breadcrumbify(breadcrumbs, "gstin")
@instance_from_url_uuid(GstIn)
class GstInInvoiceList(InvoiceListMixin):
    gstin: GstIn
    def filter_by_gstin(self, qs):
        return qs.gstin(self.gstin).order_by("-pk")


@breadcrumbify(breadcrumbs, "permanentaccountnumber")
@instance_from_url_uuid(PermanentAccountNumber)
class PanInvoiceList(InvoiceListMixin):
    permanentaccountnumber: PermanentAccountNumber
    def filter_by_gstin(self, qs):
        return qs.permanentaccountnumber(self.permanentaccountnumber)


@breadcrumbify(breadcrumbs)
class InvoiceList(InvoiceListMixin):
    def filter_by_gstin(self, qs):
        return qs.all()


@breadcrumbify(breadcrumbs)
@instance_from_get_object("invoice")
class PurchaseInvoiceDetail(UuidDetailView):
    model = PurchaseInvoice
    invoice: PurchaseInvoice
    context_object_name = "purchase_invoice"
    template_name = "invoicing/purchase_invoice/purchase_invoice_detail.html"

    @cached_property
    def purchase_json(self):
        data = self.object.purchase_json or {}
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pj = self.purchase_json
        context["invoicing"] = pj
        # Set flags for template
        items = pj.get("ItemList", [])
        context["is_taxval"] = True
        context["is_igst"] = any(item.get("IgstAmt", 0) > 0 for item in items)
        context["is_cgst"] = any(item.get("CgstAmt", 0) > 0 for item in items)
        context["is_sgst"] = any(item.get("SgstAmt", 0) > 0 for item in items)
        context["has_cess"] = any(
            item.get("CesAmt", 0) > 0 or item.get("CesNonAdvlAmt", 0) > 0 for item in items
        )
        context["has_othchrg"] = any(item.get("OthChrg", 0) > 0 for item in items)
        return context


class PurchaseInvoiceHtml(PurchaseInvoiceDetail):
    template_name = "invoicing/htmldisplay/invoicing/main.html"


class PurchaseInvoicePdf(PurchaseInvoiceHtml):
    def render_to_response(self, context, **response_kwargs):
        from cz_utils.pdf_utils import html_to_pdf_response
        url = self.request.build_absolute_uri(reverse("invoicing:purchase_invoice_html", args=[self.invoice.uuid]))
        return html_to_pdf_response(url=url, filename=f"PurchaseInvoice_{self.invoice.number}.pdf")


@instance_from_get_object("invoice")
class PurchaseInvoiceJson(UuidDetailView):
    model = PurchaseInvoice
    invoice: PurchaseInvoice
    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(
            self.invoice.purchase_json,
            json_dumps_params={"indent": 2, "sort_keys": True},
        )


@instance_from_get_object("invoice")
class PurchaseInvoiceResponseJson(UuidDetailView):
    model = PurchaseInvoice
    invoice: PurchaseInvoice
    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(self.invoice.purchase_response, json_dumps_params={"indent": 2})



