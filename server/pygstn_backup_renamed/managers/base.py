"""
Baseclass for handling GSTN actions.

An 'action' represented by an 'Action' class performs a particular task on
the GSTN network. Examples of actions are: RETSAVE to save a return,
OTPREQUEST to request a One-time password, etc.
"""

import abc
import decimal
import functools
import os

import jsonschema
import requests
from pygstn.exceptions import (
    EmptyResponseError,
    FileGoneError,
    Http503Error,
    LargePayloadError,
    NoRecordsFoundNonError,
    RequestSchemaValidationError,
    ResponseSchemaValidationError,
    TokenResponseNonError,
    check_error_in_gstn_response,
)
from pygstn.utils import json
from pygstn.utils.crypto import get_transaction_id
from requests.exceptions import HTTPError
from requests.sessions import Session

PYGSTN_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RequestPayloadLimitSession(Session):
    """
    Our customization of requests.Session that limits the size of the
    payload.
    """

    MAX_CONTENT_LENGTH = 5138022  # 4.9 MB

    def send(self, request, **kwargs):
        content_length_string = request.headers.get("Content-Length")
        if content_length_string:
            try:
                content_length = int(content_length_string)
            except ValueError:
                content_length = 0
            if content_length > self.MAX_CONTENT_LENGTH:
                raise LargePayloadError(f"Payload size is: {content_length}")
        return super().send(request, **kwargs)


class Action(metaclass=abc.ABCMeta):
    """
    Base class describing an GSTN action

    The fields are
        request_schema_path - The path to the JSON schema file describing
            the request. This path starts at the same level as the
            `pygstn` module. For example: pygstn/schemas/...
        response_schema_path - The path to the JSON schema file describing
            the response.
    """

    ALLOWED_METHODS = (
        "GET",
        "PUT",
        "POST",
    )

    request_schema_path = ""  # The path to the JSON schema file describing the request
    response_schema_path = ""  # The path to the JSON schema file describing the response

    needs_session = True  # Whether a GSTN session must be established before making this Action API call

    empty_response = None  # How an empty response for a GET API should look

    requests_session_class = RequestPayloadLimitSession
    """
    Requests session class that limits payload size

    We have it here so that sub-classes can override this if they want to
    increase the size limit.
    """

    SCHEMA_VALIDATION_EXCEPTION_CLASSES = {
        "request": RequestSchemaValidationError,
        "response": ResponseSchemaValidationError,
    }

    STATUS_CODE_FIELD = "status_cd"  # The field in the response that indicates success or error

    post_url_params = None
    """
    Addition params that we want to send in the URL querystring for
    PUT/POST requests.

    Usually, all data for POST requests are sent in the payload body.
    However, for some APIs such as PROCEEDFILE, some arguments are passed
    in the query string.
    """

    @abc.abstractproperty
    def method(self):
        """
        The name of the HTTP method, e.g. GET, POST, or PUT.
        """

    @abc.abstractproperty
    def name(self):
        """
        The name of the GSTN action, e.g. RETSAVE.
        """

    @abc.abstractproperty
    def api_base_path(self):
        """
        The base URL path of this API call

        For example, in https://<domain-name>/taxpayerapi/v0.3/returns/gstr1
        the api_base_path is taxpayerapi
        """

    @abc.abstractproperty
    def version(self):
        """
        API version of the taxpayer APIs, e.g. v0.2.
        """

    @abc.abstractproperty
    def path(self):
        """
        The URL path of this action.
        """

    @abc.abstractproperty
    def INIT_SPEC(self):
        """
        A specification of how to initialize this action.

        This is a list of 3-tuples. The tuple is of the (field, is_required, validator) with
            field - the name of the field (a string)
            is_required - whether the field is required (a bool)
            validator - any validation to apply to the field (a callable or None for no validation)
                the validator should return True/False

        This spec is used in self._initialize()
        """

    _schema_validator_cache = {}

    @classmethod
    def get_validator_for_schema(cls, schema):
        """
        Get the validator for `schema`

        schema is the Python object loaded from the schema JSON file.

        We first try the version 4 validator, then we try the version 3
        validator.
        """
        types = {
            "string": (str,) + (bytes,),
        }
        for validator_class in [jsonschema.Draft4Validator, jsonschema.Draft3Validator]:
            try:
                validator_class.check_schema(schema)
                validator = validator_class(schema, types=types)
                # Copied from https://github.com/Julian/jsonschema/issues/225#issue-74925446
                validator.resolver.store["masterschema.json"] = cls.get_schema("pygstn/schemas/masterschema.json")
                return validator
            except jsonschema.exceptions.SchemaError:
                pass
        assert False, "Schema not valid"

    @classmethod
    def get_schema(cls, path):
        """
        Get the schema from a path.
        """
        filename = os.path.join(PYGSTN_PATH, path)
        return json.loads(open(filename, "rb").read().decode("utf-8"))

    @classmethod
    def get_schema_validator(cls, path):
        """
        Get validator for the JSON schema residing at `path`.

        This command parses the file and returns a schema validator
        """
        if not path:
            return None
        try:
            validator = cls._schema_validator_cache[path]
        except KeyError:
            schema = cls.get_schema(path)
            validator = cls.get_validator_for_schema(schema)
            cls._schema_validator_cache[path] = validator
        return validator

    def _initialize(self, kwargs):
        for field, is_required, validator in self.INIT_SPEC:
            value = kwargs.get(field, None)
            if is_required and (value is None):
                raise ValueError(f"Required field '{field}' cannot be None")
            if (value is not None) and validator:
                # It looks like we made a mistake specifying INIT_SPEC in
                # some cases. `validator` should raise exception if not
                # valid. Instead, in some cases it returns a False value to
                # indicate invalid value.
                if not validator(value):
                    raise ValueError(f"Got invalid value '{value}' for field '{field}'")
            setattr(self, field, value)

    def __init__(self, *args, **kwargs):
        self._initialize(kwargs)
        self.usersession = kwargs["usersession"]
        self.request_schema_validator = Action.get_schema_validator(self.request_schema_path)
        self.response_schema_validator = Action.get_schema_validator(self.response_schema_path)
        if self.empty_response is not None:
            self.validate_response(self.empty_response)
        self.txn = None  # The transaction ID

    def make_headers(self):
        # Usage existing self.txn value if available.
        # We should call make_headers() only once. However, Cygnet seems to
        # require a field called 'hdr' within the payload, only for GSTR-9
        # RETSAVE payload. Not sure why this is needed. In order to use
        # same transaction identifier in both header and payload, we use
        # add this check.
        if not self.txn:
            self.txn = get_transaction_id()
        headers = {
            "clientid": self.usersession.clientid,
            "client-secret": self.usersession.client_secret,
            "username": self.usersession.username,
            "state-cd": self.usersession.state_cd,
            "ip-usr": self.usersession.ip_usr,
            "txn": self.txn,
            "Content-Type": "application/json",
        }
        if self.usersession._is_established:
            headers["auth-token"] = self.usersession.auth_token
        return headers

    def make_payload(self):
        """
        Create the Payload to be sent with the request

        Must return a dictionary.
        """
        return {
            "action": self.name,
        }

    def payload_for_logging(self, payload):
        """
        Any modifications to make to the payload so that we log it
        properly.

        In PUT/POST requests, the payload could be encrypted. Subclasses
        can override this function to provide a payload without encryption.
        """
        return payload

    def response_data_for_logging(self, response_data):
        """
        Any modifications to make to the response data so that we can log
        it properly.

        Typically, this involves decrypting the data
        """
        return response_data

    '''
    def log_request(self, payload, headers):
        """
        Logs the request and returns an object that should be passed to
        log_response()

        This can be used to tie a response to a request.
        """
        return self.usersession.client.log_request(
            self.method,
            self.api_base_path,
            self.version,
            self.path,
            self.name,
            payload,
            headers
        )
    '''

    '''
    def log_response(self, logobj, response, response_data=None):
        """
        :param: An object that was returned by log_request
        :param: The Response object from the requests library
        :param: The JSON response data from GSTN (could be None in the case of exception)
        """
        self. usersession.client.log_response(logobj, response, response_data)
    '''

    def get_request_for_validation(self, payload):
        """
        Get the data that has to conform to the request schema
        """
        return payload

    def get_response_for_validation(self, response_data):
        """
        Get the portion of the response data that has to conform to the
        response schema
        """
        return response_data

    def unpack_result(self, data):
        """
        Unpack the result of this action from the data returned by GSTN
        """
        return data

    @classmethod
    def validate_data(cls, schema_path, data):
        """
        A utility function to validate data against a schema.

        :param: schema_path - the path of the schema file relative to the pygstn project.
        :param: data - the data to validate
        """
        cls.ensure_no_floats(data)
        validator = cls.get_schema_validator(schema_path)
        validator.validate(data)
        return True

    @classmethod
    def ensure_no_floats(cls, data):
        """
        Ensure that there is no float object in our data.
        """
        if isinstance(data, float):
            raise ValueError(f"Got unexpected float value: '{data}'")
        elif isinstance(data, (list, tuple)):
            for i in data:
                cls.ensure_no_floats(i)
        elif isinstance(data, dict):
            for k, v in data.items():
                cls.ensure_no_floats(k)
                cls.ensure_no_floats(v)

    def validate_request_or_response(self, type_, path, validator, data):
        """
        Validate `data` using schema `validator`

        :param: type_ - a string that is either `request` or `response`
            specifying whether we are validating a request or a response
        """
        self.ensure_no_floats(data)
        if validator:
            try:
                validator.validate(data)
            except jsonschema.ValidationError as ex:
                message_template = "In {module}.{class_}: {type_} data does not conform to schema described in {path}"
                message = message_template.format(
                    module=self.__class__.__module__,
                    class_=self.__class__.__name__,
                    type_=type_,
                    path=path,
                )
                self.usersession.logger.exception(message)
                self.usersession.logger.error("The failing instance is:")
                self.usersession.logger.error(json.dumps(ex.instance, indent=2))
                self.usersession.logger.error("The failing schema is:")
                self.usersession.logger.error(json.dumps(ex.schema, indent=2))
                raise self.SCHEMA_VALIDATION_EXCEPTION_CLASSES[type_](message)
        else:
            message_template = (
                "Can't perform {type_} validation in {module}.{class_}. Please define `{type_}_schema_path`"
            )
            message = message_template.format(
                type_=type_,
                module=self.__class__.__module__,
                class_=self.__class__.__name__,
            )
            self.usersession.logger.warning(message)

    def validate_request(self, data):
        self.validate_request_or_response("request", self.request_schema_path, self.request_schema_validator, data)

    def validate_response(self, data):
        self.validate_request_or_response("response", self.response_schema_path, self.response_schema_validator, data)

    def call(self, method, api_base_path, version, path, action, data, headers={}):
        """
        Make an API call to the GSTN network.

        :param: method - The HTTP method to use, GET, POST, or PUT.
        :param: api_base_path - The API base path of the URL
        :param: version - The version numver of the API call
        :param: path - The path of the API in the URL
        :param: action - The API action (defined by GSTN) to invoke. For e.g. 'RETSAVE'
        :param: data - The data to send with the API call
        :param: headers - Additional HTTP headers to add to the request

        Returns a 2-tuple, (the response object, JSON response data)
        """
        if method not in self.ALLOWED_METHODS:
            raise ValueError(f"'{method}' is not an allowed method")
        url = self.make_url(api_base_path, version, path)
        if method in ["PUT", "POST"]:
            # The right way to use a custom JSON encoder with requests
            # http://stackoverflow.com/questions/34366405/custom-jsonencoder-for-requests-post/43055172#43055172
            # https://github.com/kennethreitz/requests/issues/2755#issuecomment-137582948
            with self.requests_session_class() as session:
                r = session.request(
                    method=method, url=url, params=self.post_url_params, data=json.dumps(data), headers=headers
                )
        elif method == "GET":
            r = requests.get(url, params=data, headers=headers)
        else:
            raise NotImplementedError()
        if r.status_code == 410:
            raise FileGoneError("Got a HTTP 410 Gone Response")
        elif r.status_code == 503:
            self.usersession.logger.info("Got HTTP 503 response")
            self.usersession.logger.info(f"Headers: {r.headers}")
            raise Http503Error("Got a HTTP 503 Response")
        r.raise_for_status()
        return (r, self.parse_json(r))

    def make_url(self, api_base_path, version, path):
        return self.usersession.client.make_url(api_base_path, version, path)

    def parse_json(self, response):
        """
        Parse the JSON data in the response

        :param: response - A requests.Response object
        http://docs.python-requests.org/en/master/api/#requests.Response
        """
        if not response.content:
            # We have errors where Portal response is empty, i.e. 0-byte response
            raise EmptyResponseError("Got empty data from Government Portal.", {})
        return response.json(parse_float=decimal.Decimal)

    def check_error_in_response(self, response_data):
        """
        Check whether the response is an error response and if so, raise
        appropriate exception.
        """
        check_error_in_gstn_response(response_data, status_code_field=self.STATUS_CODE_FIELD)

    def try_handle_error_response(self, response_data):
        """
        Raise in case of API errors.

        We might encounter:
        (i) API errors: authorization, schema validation and such
        (ii) Errors because of no records in the response. In this case,
             we should not report an error, but return empty data.
        """
        try:
            self.check_error_in_response(response_data)
            return None
        except NoRecordsFoundNonError as _:  # NOQA: F841
            if self.empty_response is None:
                raise
            self.usersession.logger.debug("Got empty list from GSTN. This is harmless")
            self.validate_response(self.empty_response)
            return self.empty_response

    def is_token_response(self, response_data):
        """
        Is this a case where we get a token instead of the actual data.

        When we get a token, we have to use the token to download the data
        file after some time.
        """
        return response_data.get(self.STATUS_CODE_FIELD, None) == "2"

    '''
    def try_log_error_response(self, logobj, response, response_data):
        """
        :param: The Response object from the requests library
        :param: The JSON response data from GSTN (could be None in the case of exception)
        """
        if (response_data.get(self.STATUS_CODE_FIELD, '') == '0'):
            self.log_response(logobj, response, response_data)
    '''

    def result(self):
        """
        Makes an API call to GSTN and returns the result.
        """
        if self.needs_session:
            assert self.usersession._is_established
        headers = self.make_headers()
        payload = self.make_payload()
        self.validate_request(self.get_request_for_validation(payload))
        #############################################################
        # Log the Request
        # logobj = self.log_request(self.payload_for_logging(payload), headers)
        #############################################################
        # Make the Request.
        # Logging the response is a bit tricky. We have to do it in a
        # number of places based on error conditions
        try:
            (response, response_data) = self.call(
                self.method, self.api_base_path, self.version, self.path, self.name, payload, headers
            )
        except HTTPError as ex:
            # Log response if there is a 4xx, 5xx error
            response = ex.response
            # self.log_response(logobj, response)
            raise
        #############################################################
        # Maybe this is an error response. Try logging it
        # self.try_log_error_response(logobj, response, response_data)
        self.try_log_error_response(response, response_data)
        our_replacement = self.try_handle_error_response(response_data)
        if our_replacement is not None:
            return our_replacement
        #############################################################
        # Looks like we did not get an exception response. Log it
        # self.log_response(logobj, response, self.response_data_for_logging(response_data))
        #############################################################
        # We should be here iff status_cd in ['1', '2']
        # We either have the actual data or a token
        if self.is_token_response(response_data):
            raise TokenResponseNonError(self.unpack_result(response_data))
        # We can validate only if we got the actual data
        self.validate_response(self.get_response_for_validation(response_data))
        return self.unpack_result(response_data)


class VersionLookup:
    """
    An internal class used by the `versioned` function defined below.
    """

    def __init__(self, mapping, partial_kwargs, *args, **kwargs):
        self._mapping = mapping
        self._partial_kwargs = partial_kwargs
        self._args = args
        self._kwargs = kwargs

    def __getattr__(self, name):
        try:
            manager_class = self._mapping[name]
        except KeyError:
            raise ValueError(f"Unknown version `{name}`")
        kwargs = self._partial_kwargs.copy()
        kwargs.update(self._kwargs)
        return functools.partial(manager_class, *self._args, **kwargs)


def versioned(mapping, **partial_kwargs):
    """
    Return a handle to a versioned `Action` class that handles API calls.

    Here's some background. The GSTN API has several methods/calls and each
    call is implemented in our codebase by a sub-class of `Action`. The
    classes themselves are unaware of their hierarchy. You can instantiate
    a class with the right parameters and call it. However, we want to
    provide a meaningful hierarchy that maps GSTN's hiearchy of API calls.

    The user should be able to write something like:
        session.returns(...).gstr2(...).retsave(...)
    to access the RETSAVE call within the GSTR2 portion of the Returns API.

    Not all function calls in the example chain need parameters and in
    fact, we don't have to require a function call. We could have supported
    something like
        session.returns.gstr2(...).retsave()
    For the sake of consistency, we require parentheses for each step down
    the hiearchy.

    Now, comes the question of how to support multiple versions of an API
    call. Our syntax is
        session.returns().gstr2().retsave().v02()
    to access the version 0.2 API call, and
        session.returns().gstr2().retsave().v03()
    to access the version 0.3 API call. This is because these calls are
    almost identical in behavior. Specifying the version last helps reduce
    duplication in our codebase.

    Coming to the usage of this function, the user should write something
    like:

        retsave = versioned({
            'v02': RetsaveActionV02,
            'v03': RetsaveActionV03,
        }, usersession=usersession, ... any other parameters ...)

    :param: mapping - a mapping specifying version number to the `Action`
        class for that version
    :param: **partial_kwargs - any keyword arguments to pass to the Action
        class's constructor
    """

    def versioned_callable(*args, **kwargs):
        return VersionLookup(mapping, partial_kwargs, *args, **kwargs)

    return versioned_callable
