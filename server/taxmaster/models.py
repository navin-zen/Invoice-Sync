"""
Master data related to Taxation.
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from invoicing.utils.return_type_enums import RETURN_TYPES, SHORT_NAME_MAP, return_period_display
from invoicing.utils.utils import financial_year as financial_year_fn
from jsonfield import JSONField
from pygstn.utils.gstin import PAN_RE, GstinUtils

from cz_utils.django.db.fields import CzDateField, CzForeignKey, CzTaxPercentField, CzUppercaseField, TrimmedCharField
from cz_utils.django.db.models import CloudZenModel, DateVersionedModel
from cz_utils.queryset_utils import CloudZenQuerySet, DateVersionedQuerySetMixin
from cz_utils.text_utils import squeeze_space
from cz_utils.utils import make_django_validator

PAN_REGEX_VALIDATOR = RegexValidator(
    regex=PAN_RE,
    message="The specified number is not a valid PAN.",
)


class StateQuerySet(CloudZenQuerySet):
    def real(self):
        """
        Show only real GST States, not those we have created for dummy use.
        """
        return self.filter(statetype__in=[State.STATE, State.UNION_TERRITORY])


class State(CloudZenModel):
    """
    State for an entity.  Can be one of State, UT or outside India.
    """

    class Meta:
        ordering = ["name"]
        default_permissions = ()

    (STATE, UNION_TERRITORY, INTERNATIONAL) = (1, 2, 3)
    STATE_CHOICE = (
        (STATE, "State"),
        (UNION_TERRITORY, "Union Territory"),
        (INTERNATIONAL, "International (Outside India)"),
    )
    created_by = modified_by = None
    name = TrimmedCharField("State", unique=True)
    statetype = models.PositiveIntegerField(choices=STATE_CHOICE)
    code = TrimmedCharField(unique=True)
    alphaCode = TrimmedCharField(unique=True)
    objects = models.Manager()
    objects2 = StateQuerySet.as_manager()

    def __str__(self):
        return self.name

    @cached_property
    def is_international(self):
        return self.statetype == State.INTERNATIONAL


class HsnCodeQuerySet(DateVersionedQuerySetMixin, CloudZenQuerySet):
    def official(self):
        return self.filter(is_official=True)


class HsnCode(DateVersionedModel, CloudZenModel):
    """
    HSN code for a given item.
    """

    class Meta:
        unique_together = (
            (
                "is_goods",
                "number",
                "birthdate",
            ),
        )
        ordering = ("number",)
        default_permissions = ()

    created_by = modified_by = None
    name = TrimmedCharField(max_length=1023)
    number = TrimmedCharField()
    description = models.TextField(blank=True)
    tax_rate_cgst = CzTaxPercentField(blank=True, null=True)
    tax_rate_sgst = CzTaxPercentField(blank=True, null=True)
    tax_rate_igst = CzTaxPercentField(blank=True, null=True)
    tax_rate_cess = CzTaxPercentField(blank=True, null=True)
    is_official = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether this is in the official list publised by GSTN.",
    )
    is_goods = models.BooleanField()
    objects = models.Manager()
    objects2 = HsnCodeQuerySet.as_manager()

    @cached_property
    def hsn_type_str(self):
        return "G" if self.is_goods else "S"

    @classmethod
    def is_goods_from_type_string(cls, type_string):
        choices = {"G": True, "S": False}
        return choices[type_string.upper()]

    def date_versioned_pre_save(self, old, new):
        new.uuid = uuid.uuid4()

    def __str__(self):
        return f"{self.number} - {self.name}"


class Unit(CloudZenModel):
    """
    List of units that may appear in an invoice.
    """

    created_by = modified_by = None
    name = TrimmedCharField(
        "UQC",
        unique=True,
        help_text=squeeze_space(
            """The Unit Quantity
        Code (UQC)"""
        ),
    )
    name_for_gstn = TrimmedCharField(
        "UQC for filing",
        default="OTH",
        help_text=squeeze_space(
            """The UQC
        that we should use for filing GST Return. This is because, some
        customers prefer to use a UQC that makes sense to them, like Carat,
        but GSTN does not accept this as a valid one. This column specifies
        the mapping."""
        ),
    )
    long_name = TrimmedCharField("Name", help_text="Unit name")
    objects = models.Manager()
    objects2 = CloudZenQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        default_permissions = ()

    def __str__(self):
        return f"{self.name} - {self.long_name}"


class Currency(CloudZenModel):
    """
    A Currency such as INR, USD, or EUR.
    """

    created_by = modified_by = None
    abbreviation = TrimmedCharField(unique=True, help_text="an abbreviation of the currency, such as INR")
    name = TrimmedCharField(unique=True, help_text="the full name of the currency")
    exchange_rate = models.DecimalField(
        "Exchange Rate",
        max_digits=16,
        decimal_places=6,
        validators=[
            MinValueValidator(0),
        ],
        help_text="the reference exchange rate to convert to the home currency",
    )
    is_home = models.BooleanField(
        null=True,
        blank=True,
        unique=True,
        help_text="""is this the home currency for your company?. If not,
        leave this field unset. Only one currency can be the home
        currency.""",
    )
    objects = models.Manager()
    objects2 = CloudZenQuerySet.as_manager()

    class Meta:
        ordering = ("abbreviation",)
        verbose_name_plural = "currencies"
        default_permissions = ()

    def __str__(self):
        return self.abbreviation


class PortCode(CloudZenModel):
    """
    The code number and name of a Port.
    """

    created_by = modified_by = None
    code = TrimmedCharField("Port Code", unique=True)
    name = TrimmedCharField("Port Name")
    objects = models.Manager()
    objects2 = CloudZenQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        default_permissions = ()

    def __str__(self):
        return f"{self.code} - {self.name}"


class DocumentType(CloudZenModel):
    """
    A type of Document (Invoice, Delivery Challan, etc.)
    """

    created_by = modified_by = None
    number = models.PositiveIntegerField(help_text="The number of this Document Type.")
    name = TrimmedCharField(help_text="The name of the Document Type.")
    objects = models.Manager()
    objects2 = CloudZenQuerySet.as_manager()

    class Meta:
        unique_together = (("number",),)
        ordering = ("number",)
        default_permissions = ()

    def __str__(self):
        return self.name


class PincodeQuerySet(CloudZenQuerySet):
    def details_available(self, b):
        return self.filter(details_available=b)


class Pincode(CloudZenModel):
    """
    Master data of all PIN Codes

    We are storing pincode as an integer. If we need to make it a string in
    the future, we can change it.
    """

    pincode = models.PositiveIntegerField(db_index=True, unique=True)
    # Storing as integer so that we can index it better
    details_available = models.BooleanField()
    # Whether details of city and state names are avaiable with us
    city = TrimmedCharField()
    state = TrimmedCharField()
    statecode = TrimmedCharField()
    city_slug = models.SlugField(blank=True, max_length=255)
    google_response = JSONField(
        editable=False,
        null=True,
        help_text="The response from Google about this PIN Code search",
    )
    objects = models.Manager()
    objects2 = PincodeQuerySet.as_manager()

    def clean(self):
        super().clean()
        self.city_slug = slugify(self.city)

    def __str__(self):
        return f"{self.pincode}, {self.city}, {self.state}"


def validate_gstin(s):
    """
    This function is defined here so that it can be used as a validator for
    TaxPayer.gstin field.
    """
    return make_django_validator(GstinUtils.validate_gstin)(s)


class TaxPayerQuerySet(CloudZenQuerySet):
    def for_website(self):
        """
        Those objects that can be shown on the website. Needs to have
        proper values for the `gstin`, `pan`, and `slug` fields.
        """
        return self.filter(~Q(slug="") & ~Q(gstin="") & ~Q(pan=""))

    def pan(self, pan):
        """
        Filter TaxPayers by PAN
        """
        return self.filter(pan=pan.upper())

    def gstin(self, gstin):
        return self.filter(gstin=gstin.upper())

    def pincode(self, pincode):
        if isinstance(pincode, str) or isinstance(pincode, int):
            return self.filter(pincode_obj__pincode=pincode)
        elif isinstance(pincode, Pincode):
            return self.filter(pincode_obj=pincode)
        else:
            return self.none()


class TaxPayer(CloudZenModel):
    """
    A GST Taxpayer

    The TIN number and other details obtained from:
    https://services.gst.gov.in/services/searchtp
    """

    created_by = modified_by = None
    pan = CzUppercaseField("PAN Number", blank=True, db_index=True, validators=[PAN_REGEX_VALIDATOR])
    gstin = CzUppercaseField(
        "GSTIN",
        validators=[validate_gstin],
        help_text="The 15-digit GSTIN Number",
        db_index=True,
        unique=True,
    )
    slug = models.SlugField(blank=True, max_length=255)
    legal_name = TrimmedCharField(
        "Legal Name",
        help_text=squeeze_space(
            """The Legal Name of the Tax
        Payer"""
        ),
        db_index=True,
    )
    trade_name = TrimmedCharField(
        "Trade Name",
        blank=True,
        help_text=squeeze_space(
            """The Trade Name
        of the Tax Payer"""
        ),
        db_index=True,
    )
    pincode = TrimmedCharField("PIN Code", blank=True)
    pincode_obj = CzForeignKey(Pincode, null=True, blank=True)
    state_obj = CzForeignKey(State, null=True, blank=True)
    valid = models.BooleanField(
        help_text=squeeze_space(
            """Whether this TIN number is a valid
        one."""
        )
    )
    registration_date = CzDateField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The date of
        registration of this Tax Payer."""
        ),
    )
    cancellation_date = CzDateField(
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The date of
        cancellation of this Tax Payer's registration."""
        ),
    )
    gstn_response = JSONField(
        default=dict,
        editable=False,
        help_text="The response from GSTN about this Tax Payer",
    )
    portal_response = JSONField(
        null=True,
        editable=False,
        help_text="The response from GSTN Portal (not API) about this Tax Payer",
    )
    ewb_response = JSONField(
        default=dict,
        editable=False,
        help_text=squeeze_space(
            """The response from the E-Way Bill website
        about this Tax Payer"""
        ),
    )
    metadata = JSONField(default=dict, editable=False)
    objects = models.Manager()
    objects2 = TaxPayerQuerySet.as_manager()

    class Meta:
        default_permissions = ()

    @cached_property
    def good_name(self):
        return self.trade_name or self.legal_name

    @cached_property
    def state(self):
        """
        The `taxmaster.models.State` object of this TaxPayer
        """
        return State.objects2.filter(code=self.gstin[:2]).first()

    def get_absolute_url(self):
        return reverse(
            "taxmaster:tax_payer_detail",
            urlconf=settings.PUBLIC_SCHEMA_URLCONF,
            args=[self.slug, self.gstin],
        )

    def get_pan_url(self):
        return reverse(
            "taxmaster:pan_detail",
            urlconf=settings.PUBLIC_SCHEMA_URLCONF,
            args=[self.slug, self.pan],
        )

    def __str__(self):
        return self.gstin


class FilingStatusQuerySet(CloudZenQuerySet):
    def gstin(self, gstin):
        if not gstin:
            return self.none()
        return self.filter(gstin=gstin.upper())

    def financial_year(self, date):
        """
        Filter all invoices in the financial year of the date.
        """
        (start, end) = financial_year_fn(date)
        return self.filter(return_period__gte=start, return_period__lte=end)

    def filed_financial_year(self, date):
        """
        Filter all invoices filed in the financial year of the date.
        """
        (start, end) = financial_year_fn(date)
        return self.filter(
            date_of_filing__isnull=False,
            date_of_filing__gte=start,
            date_of_filing__lte=end,
        )


class FilingStatus(CloudZenModel):
    """
    Store Tax Return Filing status details
    """

    uuid = None  # Remove UUID field and save space/compute
    gstin = CzUppercaseField(
        "GSTIN",
        validators=[validate_gstin],
        help_text="The 15-digit GSTIN Number",
        db_index=True,
    )
    return_period = models.DateField(
        "Return Period",
        help_text=squeeze_space(
            """The period for which
        this Tax Return is to be filed for."""
        ),
    )
    status = TrimmedCharField("Filing status", blank=True)
    mode_of_filing = TrimmedCharField("Mode of Filing", blank=True)
    date_of_filing = models.DateField(
        "Date of Filing",
        blank=True,
        null=True,
    )
    acknowledgement_number = TrimmedCharField("Acknlowledgement Number", blank=True)
    return_type = models.PositiveSmallIntegerField(
        "Return Type",
        choices=RETURN_TYPES,
        blank=True,
        null=True,
        help_text="The type of this Tax Return.",
    )
    return_type_string = TrimmedCharField("Return Type String", blank=True)
    metadata = JSONField(default=dict, editable=False)
    objects = models.Manager()
    objects2 = FilingStatusQuerySet.as_manager()

    def __str__(self):
        return f"{self.gstin} - {self.return_period}"

    @cached_property
    def return_type_shortname(self):
        return SHORT_NAME_MAP.get(self.return_type, "")

    @cached_property
    def return_period_display(self):
        return return_period_display(self.return_type, self.return_period)
