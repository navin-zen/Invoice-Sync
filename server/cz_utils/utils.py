"""
Utility functions by CloudZen.
"""

import datetime
import operator
import time

import dateutil.parser
import pytz
from django.core.exceptions import ValidationError
from django.utils.timesince import timesince
from django.utils.timezone import now

from cz_utils.itertools_utils import lookahead

__all__ = (
    "retry",
    "is_valid_choice",
    "make_django_validator",
)


class MaxRetriesException(Exception):
    pass


def retry(partial, retry_exception, numtries=5, timeout=3, exponential=True):
    """
    Retry the partial function until success or after exhausting the number
    of tries.

    The two required parameters are
        'partial': the partial function to execute, and
        'retry_exception': an exception type indicating that we that we
        should re-try
    """
    if exponential:
        timeouts = [(timeout * (2**i)) for i in range(numtries)]
    else:
        timeouts = [timeout for i in range(numtries)]
    for t, has_more in lookahead(timeouts):
        try:
            return partial()
        except Exception as exception:  # pylint: disable=broad-except
            if not isinstance(exception, retry_exception):
                raise exception
            if has_more:
                time.sleep(t)
    raise MaxRetriesException(f"No success after {numtries} retries")


def is_valid_choice(x, choices):
    """
    Assert that `x` is a valid choice for `choices`
    """
    if x not in [k for (k, _) in choices]:
        raise ValueError("Got an invalid choice")
    return True


def make_django_validator(fn):
    """
    Make a Django Validator, i.e., a function that validates its input and
    returns ValidationError.

    Takes a function that returns ValueError on invalid input and returns a
    function that returns ValidationError.
    """

    def wrapper(x):
        try:
            fn(x)
        except ValueError as ex:
            raise ValidationError(ex.args[0])

    return wrapper


def get_client_ip(request):
    """
    Get IP address of the client.

    Copied from <https://stackoverflow.com/a/4581997>.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


IST = pytz.timezone("Asia/Calcutta")


def in_ist(dt):
    """
    A date time object in IST
    """
    return dt.astimezone(tz=IST)


def india_date():
    """
    The current date in India
    """
    return in_ist(now()).date()


def date_to_india_datetime(d):
    return IST.localize(datetime.datetime.combine(date=d, time=datetime.time()))


def cz_human_date(dt):
    """
    Human friendly representation of a datetime object
    """
    return f"{in_ist(dt)} ({timesince(dt)} ago)"


def parse_iso_datetime(isoformat):
    """
    Parse string in ISO format and return a datetime object
    """
    try:
        return dateutil.parser.parse(isoformat)
    except ValueError:
        return None


def typechecker(type_):
    """
    Returns a function that checks that argument if of type `type_`
    """

    def check_type(x):
        return isinstance(x, type_)

    return check_type


def merge_dicts(dicts):
    """
    Merge keys, values in multiple dicts into one dict.

    If duplicate keys exist, value from latter dicts will be present.
    """
    merged = {}
    for d in dicts:
        merged.update(d)
    return merged


def multi_itemgetter(args):
    """
    Wrapper around operator.itemgetter but handles multiple args.
    """
    if len(args) == 0:
        return lambda x: None
    else:
        return operator.itemgetter(*args)
