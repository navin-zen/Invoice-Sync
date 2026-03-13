"""
Common utilities for dealing with GSTR data
"""

import logging
import string

from invoicing.models import GstIn, PermanentAccountNumber

from cz_utils.functools import lru_cache
from taxmaster.models import State

logger = logging.getLogger(__name__)


@lru_cache()
def get_state_from_code(code):
    """
    Returns the State object for the specified code.
    Raises an error is the specified code does not exist in our db.

    :param: code - State Code
    """
    if not code:
        return None
    if isinstance(code, State):
        return code
    try:
        return State.objects2.order_by().get(code=code)
    except State.DoesNotExist:
        raise ValueError(f"Invalid state code: {code}")


@lru_cache()
def get_state_from_name(name):
    """
    Returns the State object for the specified code.
    Raises an error is the specified code does not exist in our db.

    :param: name - State Name
    """
    if not name:
        return None
    if isinstance(name, State):
        return name
    try:
        if isinstance(name, str):
            name = name.strip()
        return State.objects2.order_by().get(name__iexact=name)
    except State.DoesNotExist:
        raise ValueError(f"Invalid state: {name}")


@lru_cache()
def typecast_and_get_state(s):
    """
    Returns the State object for the specified code.  This function is used
    when importing data from an XLS file in which `s` may be of integer, float
    or string type.

    In addition to being specified as a code, the value may also be specified
    as `<numeric-code>-<State>`, e.g. `27-Maharashtra`.  In such cases, we
    consider the numeric code for getting the State.

    :param: s - State code
    """
    if isinstance(s, int):
        s = f"{s:02d}"
    elif isinstance(s, float):
        s = f"{s:02.0f}"
    elif isinstance(s, str):
        s = s.strip().split("-")[0].strip()
    if isinstance(s, str) and all((c in string.digits) for c in s):
        if len(s) == 1:
            return get_state_from_code("0" + s)
        else:
            return get_state_from_code(s)
    else:
        return get_state_from_name(s)


@lru_cache()
def get_state_from_name_or_alphacode(s):
    """
    Returns the State object for the specified name.
    Raises an error is the specified code does not exist in our db.

    :param: s - State name or alphacode (not the numeric code)
    """
    s = s.strip()
    state = (
        State.objects2.filter(name__iexact=s).order_by().first()
        or State.objects2.filter(alphaCode__iexact=s).order_by().first()
    )
    if not state:
        raise ValueError(f"Could not find state matching: '{s}'")
    return state


def get_or_create_permanentaccountnumber(number, name):
    """
    Returns the PermanentAccountNumber for the specified number.
    A PermanentAccountNumber is created if it does not exist already.

    :param: number - Permanent Account Number
    :param: name - Name
    :param: customer - Get the Cutomer's UUID
    """
    number = number.upper()
    pan = PermanentAccountNumber.objects2.filter(number=number).first()
    if not pan:
        pan = PermanentAccountNumber(number=number, name=name)
        pan.full_clean()
        pan.save()
    return pan


def get_or_create_gstin(gstin_string, name, taxpayer_type=None):
    """
    Returns (Gstin, LegalPerson) for a given GSTIN string and name.
    PermanentAccountNumber, LegalPerson, GstIn are created, if required.

    :param: gstin - GSTIN
    :param: name - LegalPerson name
    :customer - Customer
    """
    gstin_string = gstin_string.upper()
    statecode = GstIn.get_statecode_from_gstin_string(gstin_string)
    state = get_state_from_code(statecode)
    pan_string = GstIn.get_pan_from_gstin_string(gstin_string)
    # Create PermanentAccountNumber
    pan = get_or_create_permanentaccountnumber(pan_string, name)
    # Create GstIn
    gstin = GstIn.objects2.filter(gstin=gstin_string).first()
    if not gstin:
        gstin = GstIn(
            gstin=gstin_string,
            name=name,
            permanentaccountnumber=pan,
            state=state,
            taxpayer_type=taxpayer_type or GstIn.REGULAR,
        )
        gstin.full_clean()
        gstin.save()
    return gstin


