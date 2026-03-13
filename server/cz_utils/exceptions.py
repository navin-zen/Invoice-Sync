"""
Definitions of Exceptions
"""

from pygstn.exceptions import FileGoneError


class ValueErrorWithCode(ValueError):
    """
    A sub-class of ValueError with an error code.

    We have this specifically, since we raise ValueError a lot.
    """

    def __init__(self, message, code):
        self.code = code
        super().__init__(message)


class DryRunSuccessException(Exception):
    """
    Raised when a Dry run succeeds.

    We raise it so that raising this exception will automatically rollback the
    transaction we are in (we usually are in a trasaction when doing bulk
    operations) and undo the work done in the dry run.
    """

    pass


class ExcelImportException(Exception):
    """
    Raised when the excel import operation fails.

    This can be raised for various reasons during the import process, e.g.,
    if a record has required fields missing, or other checks fail.
    """

    pass


class GstnSessionRequiredException(Exception):
    """
    Could not perform operation because the user does not have a valid
    session with GSTN.
    """

    pass


class SuspensionException(Exception):
    """
    Could not perform an operation because the user's account is suspended
    """

    pass


class TaxableAmountsInconsistentException(ValueError):
    """
    Taxable Amounts are not in line with Tax Rate and Taxable Value.
    """

    pass


class InvalidCaptchaException(Exception):
    """
    The captcha value we sent to the government portal is invalid.
    """

    pass


class PasswordProtectedFileException(Exception):
    """
    The file we are trying to open is password protected
    """

    pass


class TooMuchForLambdaException(Exception):
    """
    A task has computation beyond Lambda's RAM/time limits.
    """

    pass


class GSTZenSoftwareErrorException(Exception):
    """
    This is likely an exception in our source code / application logic.

    We define this exception class so that we don't keep re-trying the code
    in case of failure. Only solution is to fix our software.
    """

    pass


class RateLimitException(Exception):
    """
    Raised when user violates some rate-limit
    """

    pass


class UrlExpiredError(FileGoneError):
    """
    If we know the URL has already expired, we don't try to fetch the URL.

    We pre-emptively raise UrlExpiredError.

    We can save API calls.
    """

    pass
