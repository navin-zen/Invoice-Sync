"""
Very simple and commonly used utility functions
"""

import calendar
import datetime
import decimal
import string
from decimal import Decimal as D

from django.utils.encoding import force_str

from cz_utils.decimal_utils import cz_round, cz_round2, cz_round3

# These are the allowed GST tax rates in India
ALLOWED_TAX_RATES = [0, D("0.1"), D("0.25"), D("1.5"), D("3"), D("5"), D("12"), D("18"), D("28")]
ALLOWED_HALF_TAX_RATES = [(d / 2) for d in ALLOWED_TAX_RATES]
ALLOWED_TAX_FRACTIONS = [(d / 100) for d in ALLOWED_TAX_RATES]
ALLOWED_HALF_TAX_FRACTIONS = [(d / 200) for d in ALLOWED_TAX_RATES]


def financial_year(date):
    """
    Returns a 2-tuple (start, end) of the FY of which date is a part of.

    :param: date - a datetime.date object
    """
    if date.month <= 3:
        start = datetime.date(date.year - 1, 4, 1)
        end = datetime.date(date.year, 3, 31)
    else:
        start = datetime.date(date.year, 4, 1)
        end = datetime.date(date.year + 1, 3, 31)
    return (start, end)


fy_range = financial_year


def quarters_in_fy(date, within=None):
    """
    Return the Quarters in a Financial Year.

    Returns Jun 1, Sep 1, Dec 1, and Mar 1.

    within: optional parameter providing start and end range for filtering
    """
    (start, end) = financial_year(date)
    dates = [
        datetime.date(start.year, 6, 1),
        datetime.date(start.year, 9, 1),
        datetime.date(start.year, 12, 1),
        datetime.date(end.year, 3, 1),
    ]
    if not within:
        return dates
    (start_within, end_within) = within
    return [d for d in dates if (start_within <= d <= end_within)]


def month_range(date):
    """
    Returns 2-tuple (start, end) of the dates in a month

    :param: date - a datetime.date object
    """
    (_, num_days) = calendar.monthrange(date.year, date.month)
    return (date.replace(day=1), date.replace(day=num_days))


def month_display(d):
    return d.strftime("%b %Y")


def date_display(d):
    return d.strftime("%d-%b-%Y")


def floatval(amt):
    """
    floatval converts amt to a floating point number.
    If amt is None, it returns float(0)
    This has been added temporarily.
    """
    if amt is None:
        return float(0)

    return float(amt)


def bool2str(b):
    """
    Convert a boolean to string per GSTN APIs
    """
    if b:
        return "Y"
    else:
        return "N"


def nullbool2str(b):
    """
    Convert a NullBoolean to string
    """
    if b:
        return "Y"
    elif b is None:
        return ""
    return "N"


def str2bool(s, default=None):
    """
    Convert a string to boolean per GSTN APIs

    If `s` is empty, and `default` is provided, then returns `default`.
    If `s` is empty, but `default` is not provided, raises ValueError.
    """
    if s is None:
        if default is not None:
            return default
    s = force_str(s).strip()
    if not s:
        if default is not None:
            return default
    s_upper = "".join(c for c in s.upper() if (c in string.ascii_uppercase))
    if s_upper in ["Y", "YES"]:
        return True
    elif s_upper in ["N", "NO"]:
        return False
    else:
        raise ValueError(f"Invalid Yes/No value: '{s}'. Valid choices are 'Y' or 'N'.")


def to_decimal(v):
    """
    Returns the decimal value.
    """
    if v is None:
        return 0
    if isinstance(v, decimal.Decimal):
        return v
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
    try:
        return decimal.Decimal(force_str(v))
    except decimal.DecimalException:
        raise ValueError(f'"{v}" is not a number.')


def to_decimal_round2(v):
    """
    Returns decimal value rounded to 2 decimal places.
    """
    return cz_round2(to_decimal(v))


def to_decimal_round3(v):
    """
    Returns decimal value rounded to 2 decimal places.
    """
    return cz_round3(to_decimal(v))


def to_int(v):
    return cz_round(to_decimal(v))


def tax_rate_options(seq):
    """
    Returns the tax rate options as a string.
    """
    assert isinstance(seq, list)
    if not seq:
        return ""
    if len(seq) == 1:
        return f"{seq[0]}%"
    return "{}, and {}%".format(", ".join(f"{i}%" for i in seq[:-1]), seq[-1])


def parse_percent_value(s):
    """
    Strips the percent sign from the value and returns the decimal value.
    """
    if s is None:
        return decimal.Decimal(0)
    elif s == "":
        return decimal.Decimal(0)
    elif isinstance(s, decimal.Decimal):
        return s
    elif isinstance(s, int):
        return decimal.Decimal(s)
    elif isinstance(s, float):
        return decimal.Decimal(str(s))
    elif isinstance(s, str):
        v = s.strip()
        if v:
            return to_decimal(v.replace("%", ""))
        else:
            return decimal.Decimal(0)


def parse_percent_value_round2(s):
    """
    Parses percent value and rounds to 2 decimal places
    """
    return cz_round2(parse_percent_value(s))


def parse_tax_rate_unused(s):
    """
    THIS FUNCTION IS NOT USED. SEE The FUNCTION BELOW WITH THE SAME NAME.

    Parse a GST Tax Rate

    The value could be a either a percent value or a rate. For example, the
    GST rate of 28% could either be the value 28 or 0.28.

    We have to disambiguate whether the value is a percent or a fraction.
    For example,
        0.25 stands for 0.25% because this is a valid tax rate.
        0.28 stands for 28% because 28% is the tax rate and 0.28 is not.
        0.125 stands for 0.125% because this is a valid half tax-rate
        0.12 stands for 12% because 12% is the tax rate slab and 0.12 is not.

    The tricky part here is that the input value `s` could have some
    inaccuracy and we might have to round it. But, to what decimal place do
    we round it? 0.125 and 0.12 are too close in the example above that
    rounding will break our disambiguation. Therefore we don't do any
    rounding before some disambiguation.

    ALLOWED_TAX_RATES = [0, decimal.Decimal('0.25'), 3, 5, 12, 18, 28]
    ALLOWED_HALF_TAX_RATES = [0, 0.125, 1.5, 2.5, 6, 9, 14]
    ALLOWED_TAX_FRACTIONS = [0, 0.0025, 0.03, 0.05, 0.12, 0.18, 0.28]
    ALLOWED_HALF_TAX_FRACTIONS = [0, 0.00125, 0.015, 0.025, 0.06, 0.09, 0.14]

    ALLOWED_TAX_RATES = [0, 0.25]
    ALLOWED_HALF_TAX_RATES = [0, 0.125]
    ALLOWED_TAX_FRACTIONS = [0, 0.0025, 0.03, 0.05, 0.12, 0.18, 0.28]
    ALLOWED_HALF_TAX_FRACTIONS = [0, 0.00125, 0.015, 0.025, 0.06, 0.09, 0.14]
    """
    raise NotImplementedError("This function is still under development")
    v = parse_percent_value(s)
    if v >= 1:
        return cz_round2(v)
    if v < D("0.1"):
        return cz_round2(v * 100)


def parse_tax_rate(s):
    """
    Parse a GST Tax Rate
    """
    v = parse_percent_value(s)
    if v < 1:
        r = cz_round3(v)
    else:
        r = cz_round2(v)
    if r in ALLOWED_TAX_RATES:
        return r
    raise ValueError(f"Invalid GST Rate '{r}'")


def parse_half_tax_rate(s):
    """
    Parse a GST Tax Rate
    """
    v = parse_percent_value(s)
    if v < 1:
        r = cz_round3(v)
    else:
        r = cz_round2(v)
    if r in ALLOWED_HALF_TAX_RATES:
        return r
    raise ValueError(f"Invalid GST Rate '{r}'")


def get_string_in_xls(s):
    """
    Get a string value from an XLS cell
    """
    if s is None:
        return ""
    if not isinstance(s, str):
        s = force_str(s)
    return s.strip()


def parse_description(s):
    return get_string_in_xls(s)[:250]


