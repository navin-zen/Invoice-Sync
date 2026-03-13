"""
Utilities for interacting with GSTN
"""

import abc
import decimal
import logging
import sys

from django.conf import settings
from django.contrib.messages import ERROR, SUCCESS, WARNING
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from invoicing.models import ApiCall, GstIn
from pygstn.exceptions import EmptyResponseError, GstnErrorResponseException, TokenResponseNonError, WrongUsernameError
from pygstn.utils.crypto import get_transaction_id

from cz_utils import pusher
from cz_utils.decimal_utils import cz_round2
from cz_utils.exceptions import GstnSessionRequiredException, GSTZenSoftwareErrorException, SuspensionException
from gstnapi.utils.client import get_invoicingclient_or_mock, get_gstnclient_or_mock

logger = logging.getLogger(__name__)


def get_dummy_transaction_id():
    prefix = "DUMMY"
    return prefix + get_transaction_id()[len(prefix) :]


class GstnApi(metaclass=abc.ABCMeta):
    """
    Defines the entrypoint for communicating with GSTN.
    """

    success_message = ""

    cz_data_transfer_cost = 0

    @cached_property
    def cost_per_api_invoice(self):
        billing_cost_per_api_invoice = self.customer.billing_cost_per_api_invoice
        if billing_cost_per_api_invoice is not None:
            return billing_cost_per_api_invoice
        else:
            return decimal.Decimal("0.01")

    CAN_SPLIT_LARGE_RESULT = False
    """
    Whether we have a mechanism to split a large result into smaller
    batches.
    """

    @abc.abstractproperty
    def EXCEPTIONS_TO_RERAISE(self):
        """
        We should not handle these exceptions, instead we should re-raise
        them.

        The caller will handle them (usually in the view to show to the
        user).
        """

    @abc.abstractproperty
    def INIT_SPEC(self):
        """
        The specification of this class's __init__.

        Specifies the name of the arguments of their validation.

        See, _initialize() for the usage of INIT_SPEC.
        """
        pass

    def _initialize(self, kwargs):
        """
        Initialize fields based on INIT_SPEC.
        """
        expected_fields = {field for (field, _, _) in self.INIT_SPEC}
        for field in kwargs:
            if field not in expected_fields:
                raise ValueError(f"'{field}' is not an expected field")
        for field, is_required, validator in self.INIT_SPEC:
            value = kwargs.get(field, None)
            if is_required and (value is None):
                raise ValueError(f"Required field '{field}' cannot be None")
            if (value is not None) and (validator is not None):
                if not validator(value):
                    raise ValueError(f"Got invalid value '{value}' for field '{field}'")
            setattr(self, field, value)

    def __init__(self, **kwargs):
        self._initialize(kwargs)
        self.complete_init()
        # These are the kwargs that can be used to instantiate this class again
        self._kwargs = kwargs

    @cached_property
    def _classname(self):
        """
        The full name of this class, including the module.
        """
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    def complete_init(self):
        pass

    def check_suspension_internal(self):
        """
        Check whether the account is suspended. If so, raise an exception
        """
        pass

    def check_suspension(self):
        """
        Check whether the account is suspended. If so, raise an exception
        """
        try:
            self.check_suspension_internal()
        except SuspensionException as ex:
            self.send_pusher_error_message(force_str(ex))
            raise

    def check_enterprise_trial(self):
        """
        If the account is on an enterprise trial, they can make API calls
        only for first few months tax returns, only for one GSTIN.
        """
        pass

    def check_rate_limit(self):
        """
        Prevent multiple calls to the same API in a short period of time

        Returns true if the call is rate-limited
        """
        return None

    @abc.abstractmethod
    def get_session(self):
        pass

    @abc.abstractproperty
    def API_NAME(self):
        """
        A name of the API that we want to log
        """
        pass

    @cached_property
    def apicall_description(self):
        return ""

    @cached_property
    def request_for_logging(self):
        return None

    def response_for_logging(self, result):
        return result

    def update_session(self, session):
        pass

    @classmethod
    def sanitize_gstn_response(cls, result):
        """
        We occasionally see GSTN sending floating point data with multiple
        decimal places in their response.

        Here's one such example: "tot_tr_amt": 3963.2799999999997

        We want to round such erroneous values to maximum 2 decimal places.
        """
        if isinstance(result, decimal.Decimal):
            return cz_round2(result)
        if isinstance(result, (list, tuple)):
            return [cls.sanitize_gstn_response(i) for i in result]
        if isinstance(result, dict):
            return {k: cls.sanitize_gstn_response(v) for (k, v) in result.items()}
        return result

    def post_process_result(self, result):
        pass

    def try_split_large_result(self, result):
        return False

    def handle_token_result(self, result):
        """
        This is a token response, where we have to download the result file
        after some time
        """
        raise ValueError("A token result is not expected for this API")

    def log_api_call(self, timestamp, action, request, response, is_exception, is_token=False):
        """
        Log the API Call

        :param: action - The `pygstn.managers.base.Action` object
        :param: timestamp - Timestamp (isoformat) at which the call is made
        :param: request - Any bit of request information that we want to store
        :param: response - Any bit of response information that we want to store
        :param: is_exception - Is this an exception response?
        :param: is_token - Whether this is a token response
        """
        pass

    def api_call_kwargs(self, timestamp, action, request, response, is_exception, is_token=False):
        """
        Get additional keyword arguments for the ApiCall object.
        """
        return {}

    def get_num_records(self, result):
        """
        The number of records in the request or result

        Sub-classes can extend this to return the number of records for
        usage tracking.
        """
        return None

    @cached_property
    def usage_description(self):
        return self.API_NAME

    @cached_property
    def pusher_channel(self):
        return None

    def send_pusher_message(self, level, message):
        """
        Send a message to the pusher channel of the TaxReturn object.
        """
        channel = self.pusher_channel
        if channel:
            pusher.trigger_notification(channel, level, message, fail_silently=True)
        else:
            logger.error("Request for notification without a defined channel")

    def send_pusher_success_message(self, text):
        return self.send_pusher_message(SUCCESS, text)

    def send_pusher_error_message(self, text):
        return self.send_pusher_message(ERROR, text)

    def send_pusher_warning_message(self, text):
        return self.send_pusher_message(WARNING, text)

    def can_user_proceed_further(self):
        """
        Check for various reasons we do not want to proceed with the API
        call.

        User may not have balance, account might be suspended, or maybe
        rate-limited, etc.

        Either raises an exception or returns False if the user should not
        proceed further.
        """
        self.check_suspension()
        self.check_enterprise_trial()
        if self.check_rate_limit():
            return False
        return True

    def do_all(self):
        """
        Make API call to GSTN and handle the response

        Returns the error response in case of error. Otherwise, returns
        None.
        """
        if not self.can_user_proceed_further():  # Will raise exception if the user cannot
            return None
        session = self.get_session()
        action = self.prepare_action(session)
        timestamp = timezone.now().isoformat()
        can_record_usage = True
        try:
            is_exception = False
            is_token = False
            result = action.result()
        except WrongUsernameError as wue:
            can_record_usage = True  # This is the user's fault
            is_exception = True
            with transaction.atomic():
                # This can happen only for sub-classes of GstInApi
                # So, self.gstin will be present
                gstin = GstIn.objects2.get(uuid=self.gstin.uuid)
                gstin.gstn_session = None  # This will clear the session to prevent future errors
                gstin.gstn_username = ""  # This will ensure that user has to enter a new username
            result = wue.args[1]
        except TokenResponseNonError as tr:
            # We will schedule a task to later download files using the token
            is_token = True
            result = tr.args[0]
        except EmptyResponseError:
            is_exception = True
            can_record_usage = False
            raise
        except self.EXCEPTIONS_TO_RERAISE as _:  # NOQA: F841
            raise
        except GstnErrorResponseException as gere:
            is_exception = True
            can_record_usage = False
            result = gere.args[1]
        return self.do_response_handling_alone_internal(
            session=session,
            timestamp=timestamp,
            action=action,
            result=result,
            is_exception=is_exception,
            is_token=is_token,
            can_record_usage=can_record_usage,
        )

    def do_response_handling_alone_internal(
        self, session, timestamp, action, result, is_exception, is_token, can_record_usage
    ):
        """
        Handle cases where we want to handle the response without making
        any API call.
        """
        request = self.request_for_logging
        response = self.response_for_logging(result)
        self.log_api_call(timestamp, action, request, response, is_exception, is_token=is_token)
        self.update_session(session)
        if is_exception:
            return self.post_process_exception_result(result)
        elif is_token:  # We have to run another task to download the data later
            self.handle_token_result(result)
        else:
            try:
                if settings.FORCE_SOFTWARE_ERROR:
                    raise ValueError("Simulating a software error")
                self.post_process_result(self.sanitize_gstn_response(result))
            except Exception:  # An exception here indicates a bug in our software
                _, _, tb = sys.exc_info()
                raise GSTZenSoftwareErrorException("Unexpected error while processing GSTN Response").with_traceback(tb)
        return None

    def do_response_handling_alone(self, result, is_exception, can_record_usage):
        """
        Handle cases where we want to handle the response without making
        any API call.
        """

        class Action:
            txn = get_dummy_transaction_id()

        return self.do_response_handling_alone_internal(
            session=None,
            timestamp=timezone.now().isoformat(),
            action=Action(),
            result=result,
            is_exception=is_exception,
            is_token=False,
            can_record_usage=can_record_usage,
        )

    def post_process_exception_result(self, result):
        """
        In case the API handler wants to handle certain exception
        responses, this is the place to do it.
        """
        return result


class GstInApi(GstnApi):
    """
    Base class for APIs related to GstIn object
    """

    def complete_init(self):
        self.gstin = GstIn.objects2.get(uuid=self.gstin_uuid)

    @transaction.atomic
    def log_api_call(self, timestamp, action, request, response, is_exception, is_token=False):
        """
        Log the API Call

        :param: action - The `pygstn.managers.base.Action` object
        :param: timestamp - Timestamp (isoformat) at which the call is made
        :param: request - Any bit of request information that we want to store
        :param: response - Any bit of response information that we want to store
        :param: is_exception - Is this an exception response?
        :param: is_token - Whether this is a token response
        """
        kwargs = self.api_call_kwargs(timestamp, action, request, response, is_exception, is_token)
        ac = ApiCall(
            gstin=self.gstin,
            timestamp=timestamp,
            transaction_identifier=action.txn,
            request=request or {},
            response=response,
            action=self.API_NAME,
            description=self.apicall_description,
            exception=is_exception,
            **kwargs,
        )
        ac.full_clean()
        ac.save()


class GstInApiGST(GstInApi):
    """
    API handler related to a GstIn object that talks to the GST website.
    """

    def get_session(self):
        return self.get_session_for_gstin(self.gstin)

    @classmethod
    def get_session_for_gstin(cls, gstin):
        session_credentials = gstin.gstn_session
        if not session_credentials:
            raise GstnSessionRequiredException("Session to GSTN is not established")
        session = get_gstnclient_or_mock(gstin.gstin).session(
            gstin.gstn_username,
            gstin.gstin,
            ip_usr=gstin.gstn_ipaddr,
        )
        session.establish_session_from_obj(session_credentials)
        return session


class GstInApiEWB(GstInApi):
    """
    API handler related to a GstIn object that talks to the EWB website.
    """

    def get_session(self):
        return self.get_session_for_gstin(self.gstin)

    @classmethod
    def get_session_for_gstin(cls, gstin):
        session_credentials = gstin.ewb_session
        if not session_credentials:
            raise GstnSessionRequiredException("Session to EWB is not established")
        session = get_gstnclient_or_mock(gstin.gstin).session(
            gstin.ewb_username,
            gstin.gstin,
        )
        session.establish_session_from_obj(session_credentials)
        return session


class GstInApiinvoicing(GstInApi):
    """
    API handler related to a GstIn object that talks to the Invoicing website.
    """

    def get_session(self):
        return self.get_session_for_gstin(self.gstin)

    @classmethod
    def get_session_for_gstin(cls, gstin):
        session_credentials = gstin.invoicing_session
        if not session_credentials:
            raise GstnSessionRequiredException("Session to Invoicing is not established")
        session = get_invoicingclient_or_mock(
            gstin.gstin, gstin.invoicing_client_id, gstin.invoicing_client_secret
        ).session(
            gstin.invoicing_username,
            gstin.gstin,
        )
        session.establish_session_from_obj(session_credentials)
        return session

    @cached_property
    def pusher_channel(self):
        """
        We use a pusher channel, only if the user explicitly sends one.
        """
        return getattr(self, "pusher_channel_override", None) or None

    @transaction.atomic
    def log_api_call(self, timestamp, action, request, response, is_exception, is_token=False):
        """
        Log the API Call

        :param: action - The `pygstn.managers.base.Action` object
        :param: timestamp - Timestamp (isoformat) at which the call is made
        :param: request - Any bit of request information that we want to store
        :param: response - Any bit of response information that we want to store
        :param: is_exception - Is this an exception response?
        :param: is_token - Whether this is a token response
        """
        super().log_api_call(
            timestamp=timestamp,
            action=action,
            request=request,
            response=response,
            is_exception=is_exception,
            is_token=is_token,
        )
        if is_exception:
            msg = "Got an error message from the Government Portal: {}".format(
                (response or {}).get("Error", {}).get("message", "")
            )
            self.send_pusher_error_message(msg)
        elif self.success_message:
            self.send_pusher_success_message(self.success_message)

    def check_suspension_internal(self):
        pass


