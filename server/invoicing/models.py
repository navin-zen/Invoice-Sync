import hashlib
import time

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils.functional import cached_property
from jsonfield import JSONField
from pygstn.utils import json
from pygstn.utils.gstin import PAN_RE, GstinUtils
from pygstn.utils.utils import to_bytes
from solo.models import SingletonModel

from cz_utils.dateparse import parse_invoicing_datetime
from cz_utils.django.db.fields import CzDateField, CzForeignKey, CzTextField, CzUppercaseField, TrimmedCharField
from cz_utils.django.db.models import CloudZenModel
from cz_utils.json_utils import JSONEncoder
from cz_utils.qrcode_utils import str_to_qrcode_img, url_to_bmp_image
from cz_utils.queryset_utils import CloudZenQuerySet
from cz_utils.session_utils import SessionUtil
from cz_utils.text_utils import squeeze_space
from cz_utils.utils import make_django_validator
from taxmaster.models import State, TaxPayer

PAN_REGEX_VALIDATOR = RegexValidator(
    regex=PAN_RE,
    message="The specified number is not a valid PAN.",
)

INVOICE_NUMBER_RE = r"^[A-Z0-9-/]{1,16}$"
INVOICE_NUMBER_REGEX_VALIDATOR = RegexValidator(
    regex=INVOICE_NUMBER_RE,
    message="The specified number is not a valid Invoice number.",
)


class InvoicingJsonEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, State):
            return o.code
        else:
            return super().default(o)


class GlobalConfiguration(SingletonModel):
    site_name = TrimmedCharField(max_length=255, default="GSTZen")
    metadata = JSONField(default=dict, editable=False)


class ConfigurationQuerySet(CloudZenQuerySet):
    pass


class Configuration(CloudZenModel):
    site_name = TrimmedCharField(max_length=255, default="GSTZen")
    enable_autosync = models.BooleanField(default=False)
    metadata = JSONField(default=dict, editable=False)
    objects2 = ConfigurationQuerySet.as_manager()

    def __str__(self):
        return self.site_name


class PermanentAccountNumberQuerySet(CloudZenQuerySet):
    pass


class PermanentAccountNumber(models.Model):
    number = CzUppercaseField("PAN Number", validators=[PAN_REGEX_VALIDATOR], unique=True)
    name = TrimmedCharField("Tax Payer Name")
    metadata = JSONField(default=dict, editable=False)
    objects = models.Manager()
    objects2 = PermanentAccountNumberQuerySet.as_manager()

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.number})"


def validate_gstin(s):
    return make_django_validator(GstinUtils.validate_gstin)(s)


class GstInQuerySet(CloudZenQuerySet):
    pass


class GstIn(CloudZenModel):
    (REGULAR, COMPOSITION, ISD) = range(11708, 11708 + 3)
    TAXPAYER_CHOICES = [
        (REGULAR, "Regular Tax Payer"),
        (COMPOSITION, "Composition Tax Payer"),
        # (ISD, "Input Service Distributor Tax Payer"),
    ]

    gstin = CzUppercaseField("GSTIN", validators=[validate_gstin], unique=True)
    name = TrimmedCharField("Tax Payer Name")
    permanentaccountnumber = CzForeignKey(PermanentAccountNumber)
    state = CzForeignKey(State)
    invoice_contact_information = CzTextField(
        "Contact Information (for Invoice)",
        blank=True,
    )
    invoice_notes = CzTextField(
        "Notes (for Invoice)",
        blank=True,
    )
    registration_date = CzDateField(
        blank=True,
        null=True,
    )
    cancellation_date = CzDateField(
        blank=True,
        null=True,
    )
    taxpayer_type = models.PositiveSmallIntegerField(
        default=REGULAR,
        choices=TAXPAYER_CHOICES,
        help_text="The type of taxpayer.",
    )
    metadata = JSONField(default=dict, editable=False)
    objects = models.Manager()
    objects2 = GstInQuerySet.as_manager()
    INVOICING_SESSION_KEY_PATH = ["invoicing", "session"]
    INVOICING_CLIENTID_KEY_PATH = ["invoicing", "credentials", "client_id"]
    INVOICING_CLIENTSECRET_KEY_PATH = ["invoicing", "credentials", "client_secret"]
    INVOICING_USERNAME_KEY_PATH = ["invoicing", "credentials", "username"]
    INVOICING_PASSWORD_KEY_PATH = ["invoicing", "credentials", "password"]

    class Meta:
        verbose_name = "GSTIN"
        ordering = (
            "permanentaccountnumber__name",
            "state__name",
        )

    def __str__(self):
        return f"{self.name} ({self.state.alphaCode} - {self.gstin})"

    @classmethod
    def get_statecode_from_gstin_string(cls, gstin):
        return gstin[:2]

    @cached_property
    def _statecode_from_gstin(self):
        """
        The 2-digit state code from the GSTIN.
        """
        return self.get_statecode_from_gstin_string(self.gstin)

    @classmethod
    def get_pan_from_gstin_string(cls, gstin):
        # Check the 13, 14th character (counting starts from from number 1)
        if gstin[12:14].upper() in [
            "UN",
            "ON",
            "NR",
            "OS",
        ]:  # UN, NRI, OIDAR not allowed
            return ""
        return gstin[2:12]

    @cached_property
    def _pan_from_gstin(self):
        """
        The PAN number from the GSTIN.
        """
        return self.get_pan_from_gstin_string(self.gstin)

    def _clean_gstin(self):
        state = getattr(self, "state", None)
        if state:
            if self._statecode_from_gstin != state.code:
                raise ValidationError("The GSTIN's state code does not match the specified state")
        permanentaccountnumber = getattr(self, "permanentaccountnumber", None)
        if permanentaccountnumber:
            if self._pan_from_gstin != permanentaccountnumber.number:
                raise ValidationError("The GSTIN does not match the specified PAN Number")

    def clean(self):
        super().clean()
        self._clean_gstin()

    @property
    def purchase_sync_client_id(self):
        """
        The client id for this GstIn in the Purchase Sync portal
        """
        return SessionUtil.get(self.metadata, self.INVOICING_CLIENTID_KEY_PATH, default="")

    @property
    def purchase_sync_client_secret(self):
        """
        The client secret for this GstIn in the Purchase Sync portal
        """
        return SessionUtil.get(self.metadata, self.INVOICING_CLIENTSECRET_KEY_PATH, default="")

    @property
    def purchase_sync_username(self):
        """
        The username for this GstIn in the Purchase Sync portal
        """
        return SessionUtil.get(self.metadata, self.INVOICING_USERNAME_KEY_PATH, default="")

    @property
    def purchase_sync_password(self):
        """
        The password for this GstIn in the Purchase Sync portal
        """
        return SessionUtil.get(self.metadata, self.INVOICING_PASSWORD_KEY_PATH, default="")

    @purchase_sync_client_id.setter
    def purchase_sync_client_id(self, value):
        SessionUtil.set(self.metadata, self.INVOICING_CLIENTID_KEY_PATH, value)
        self.save(update_fields=["metadata"])

    @purchase_sync_client_secret.setter
    def purchase_sync_client_secret(self, value):
        SessionUtil.set(self.metadata, self.INVOICING_CLIENTSECRET_KEY_PATH, value)
        self.save(update_fields=["metadata"])

    @purchase_sync_username.setter
    def purchase_sync_username(self, value):
        SessionUtil.set(self.metadata, self.INVOICING_USERNAME_KEY_PATH, value)
        self.save(update_fields=["metadata"])

    @purchase_sync_password.setter
    def purchase_sync_password(self, value):
        SessionUtil.set(self.metadata, self.INVOICING_PASSWORD_KEY_PATH, value)
        self.save(update_fields=["metadata"])

    @cached_property
    def purchase_sync_credentials_available(self):
        """
        Whether user has provided Purchase Sync portal credentials
        """
        return (
            self.purchase_sync_client_id
            and self.purchase_sync_client_secret
            and self.purchase_sync_username
            and self.purchase_sync_password
        )

    @property
    def invoicing_session_unchecked(self):
        """
        The session credentials, without any checking of session expiry.

        The only reason to use this property is when are in the process of
        establishing a session and have a partial session.
        """
        try:
            return SessionUtil.get(self.metadata, self.INVOICING_SESSION_KEY_PATH)
        except KeyError:
            return None

    @property
    def invoicing_session(self):
        """
        The credentials of the Invoicing session

        Returns None is no session exists or if the session is not active.
        """
        session = self.invoicing_session_unchecked
        return session if self._is_session_active(session) else None

    @invoicing_session.setter
    def invoicing_session(self, value):
        """
        Save the credentials of the Invoicing session
        """
        SessionUtil.set(self.metadata, self.INVOICING_SESSION_KEY_PATH, value)
        self.save(update_fields=["metadata"])

    def _is_session_active(self, session):
        """
        Is the passed in session object/dict active?
        """
        if not session:
            return False
        expiry_time = session.get("expiry_time", 0) or 0
        return time.time() < expiry_time


class PurchaseInvoiceQuerySet(CloudZenQuerySet):
    def gstin(self, gstin):
        assert isinstance(gstin, GstIn)
        return self.filter(gstin=gstin)

    def permanentaccountnumber(self, permanentaccountnumber):
        assert isinstance(permanentaccountnumber, PermanentAccountNumber)
        return self.filter(gstin__permanentaccountnumber=permanentaccountnumber)


class PurchaseInvoice(CloudZenModel):
    """
    Details about a Purchase Invoice sync.
    """

    (DT_INVOICE, DT_NOTE) = range(5697, 5697 + 2)
    DOCTYPE_CHOICES = (
        (DT_INVOICE, "Invoice"),
        (DT_NOTE, "Note"),
    )

    (DST_NOT_APPLICABLE, DST_CREDIT_NOTE, DST_DEBIT_NOTE) = range(4240, 4240 + 3)
    DOCSUBTYPE_CHOICES = (
        (DST_NOT_APPLICABLE, "Not Applicable"),
        (DST_CREDIT_NOTE, "Credit Note"),
        (DST_DEBIT_NOTE, "Debit Note"),
    )

    (
        PIS_NON_CANDIDATE,
        PIS_CANDIDATE,
        PIS_UPLOADED,
        PIS_ERROR,
    ) = range(84, 84 + 4)
    PURCHASE_STATUS_CHOICES = [
        (PIS_NON_CANDIDATE, "Non-Candidate"),
        (PIS_CANDIDATE, "Candidate"),
        (PIS_UPLOADED, "Uploaded"),
        (PIS_ERROR, "Error"),
    ]

    gstin = CzForeignKey(GstIn)
    doctype = models.PositiveSmallIntegerField(choices=DOCTYPE_CHOICES)
    docsubtype = models.PositiveSmallIntegerField(choices=DOCSUBTYPE_CHOICES)
    financial_year = CzDateField(help_text="The first date of the financial year of the Invoice")
    date = CzDateField(help_text="The date of the invoice")
    number = CzUppercaseField(max_length=16, validators=[INVOICE_NUMBER_REGEX_VALIDATOR])
    ctin = CzUppercaseField("Counter Party GSTIN", blank=True)
    purchase_status = models.PositiveSmallIntegerField(
        choices=PURCHASE_STATUS_CHOICES,
        help_text="Field to indicate the status of Purchase Invoice sync",
    )
    purchase_json = JSONField(
        default=dict,
        editable=False,
        dump_kwargs={
            "cls": InvoicingJsonEncoder,
        },
    )
    purchase_response = JSONField(
        default=dict,
        editable=False,
        dump_kwargs={
            "cls": InvoicingJsonEncoder,
        },
    )
    metadata = JSONField(
        default=dict,
        editable=False,
        dump_kwargs={
            "cls": InvoicingJsonEncoder,
        },
    )
    configuration = CzForeignKey(Configuration, null=True, editable=False, blank=True, on_delete=models.SET_NULL)
    upload_uuid = models.UUIDField(editable=False, null=True)
    objects = models.Manager()
    objects2 = PurchaseInvoiceQuerySet.as_manager()

    class Meta:
        unique_together = (
            (
                "gstin",
                "ctin",
                "doctype",
                "financial_year",
                "number",
            ),
        )

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("invoicing:purchase_invoice_detail", args=[self.uuid])

    def __str__(self):
        return self.number

    @cached_property
    def document_type_display(self):
        if self.doctype == PurchaseInvoice.DT_INVOICE:
            return "Invoice"
        elif self.doctype == PurchaseInvoice.DT_NOTE:
            if self.docsubtype == PurchaseInvoice.DST_CREDIT_NOTE:
                return "Credit Note"
            elif self.docsubtype == PurchaseInvoice.DST_DEBIT_NOTE:
                return "Debit Note"
        return ""

    @property
    def status_message(self):
        if self.purchase_status == self.PIS_ERROR:
            # First check response for API level errors
            if self.purchase_response and isinstance(self.purchase_response, dict) and "message" in self.purchase_response:
                return self.purchase_response["message"]
            # Then check purchase_json for internal validation errors
            if self.purchase_json and isinstance(self.purchase_json, dict) and "error_message" in self.purchase_json:
                return self.purchase_json["error_message"]
            return "Unknown Error"
        if self.purchase_status == self.PIS_UPLOADED:
            return "Successfully Synced"
        return ""



class CachedDataQuerySet(CloudZenQuerySet):
    def datatype(self, datatype):
        return self.filter(datatype=datatype)


class CachedData(CloudZenModel):
    """
    A cache for computed data
    """

    (
        DT_PURCHASE_SESSION_MARKER,
        DT_PURCHASE_ERRORS,
        DT_PURCHASE_SUMMARY,
        DT_PURCHASE_FINISH,
    ) = range(17230, 17230 + 4)
    DATATYPE_CHOICES = [
        (DT_PURCHASE_SESSION_MARKER, "Purchase Session Marker"),
        (DT_PURCHASE_ERRORS, "Purchase Errors"),
        (DT_PURCHASE_SUMMARY, "Purchase Summary"),
        (DT_PURCHASE_FINISH, "Purchase Finish"),
    ]
    DATA_TYPE_CONTENTTYPE_MAP = {
        DT_PURCHASE_ERRORS: "json",
        DT_PURCHASE_SUMMARY: "json",
    }
    group = CzForeignKey(
        "self",
        blank=True,
        null=True,
        help_text=squeeze_space(
            """The
        related Cached Data (to signify that these related items are part
        of a single group. Payload and chunks all link to the same
        Summary."""
        ),
    )
    gstin = CzForeignKey(GstIn, blank=True, null=True)
    datatype = models.PositiveSmallIntegerField(choices=DATATYPE_CHOICES)
    data_bytes = models.BinaryField(blank=True, null=True, help_text="Binary/bytes data.")
    data_text = models.TextField(blank=True, help_text="Data in text format.")
    data_json = JSONField(default=dict, null=True, editable=False, help_text="Data in JSON format.")
    objects = models.Manager()
    objects2 = CachedDataQuerySet.as_manager()

    def __str__(self):
        return f"CachedData - {self.get_datatype_display()}"

    @classmethod
    def add_cached_data(cls, datatype, data_json, group=None):
        cd = CachedData(
            group=group,  # gstin=taxreturn.gstin, #taxreturn=taxreturn,
            datatype=datatype,
            data_text=json.dumps(data_json, cls=JSONEncoder),
            data_json=data_json,
        )
        cd.full_clean()
        cd.save()
        return cd

    @classmethod
    def add_cached_data_for_gstin(cls, gstin, datatype, data_json, group=None):
        assert isinstance(gstin, GstIn)
        cd = CachedData(
            group=group,
            gstin=gstin,
            datatype=datatype,
            data_text=json.dumps(data_json),
            data_json=data_json,
        )
        cd.full_clean()
        cd.save()
        return cd

    @classmethod
    def add_cached_json_data(cls, uuid_, datatype, data_json):
        with transaction.atomic():
            cd = CachedData.objects2.filter(uuid=uuid_).first()
            if not cd:
                cd = CachedData(
                    uuid=uuid_,
                    datatype=datatype,
                    data_text=json.dumps(data_json),
                    data_json=data_json,
                )
            else:
                cd.datatype = datatype
                cd.data_text = json.dumps(data_json)
                cd.data_json = data_json
            cd.full_clean()
            cd.save()
            return cd


