"""
Utility to parse date
"""

import datetime

from django.utils.encoding import force_str

from cz_utils.utils import IST

DATE_STRPTIME_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y.%m.%d",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%d-%b-%Y",
    "%d/%b/%Y",
    "%d.%b.%Y",
    "%d-%b-%y",
    "%d/%b/%y",
    "%d.%b.%y",
]


def pretty_date_format(d):
    """
    Format date as 01-Apr-2019
    """
    assert isinstance(d, datetime.date)
    return d.strftime("%d-%b-%Y")


def pretty_month_format(d):
    """
    Format date as Apr-2019
    """
    assert isinstance(d, datetime.date)
    return d.strftime("%b-%Y")


def parse_date(s, formats=None):
    """
    Returns the date object for the date string in "%d/%m/%Y" format.
    """
    if s is None:
        return None
    elif s == "":
        return s
    elif isinstance(s, datetime.datetime):
        return s.date()
    elif isinstance(s, datetime.date):
        return s
    elif isinstance(s, str):
        s = s.strip()
        if not s:
            return None
        for format in formats or DATE_STRPTIME_FORMATS:
            try:
                return datetime.datetime.strptime(s, format).date()
            except ValueError:
                pass
    raise ValueError(f"Invalid date '{s}'")


def parse_return_period(s):
    """
    Parse return period string given by GSTN response.
    """
    if not s:
        raise ValueError("Invalid Return Period")
    (month, year) = (int(s[0:2]), int(s[2:6]))
    ######################################################
    # Special handling of Quarterly return period (we think)
    if month <= 12:  # Nothing to do
        pass
    elif month == 13:  # Apr-Jun Quarter -> Jun
        month = 6
    elif month == 14:  # Jul-Sep Quarter -> Sep
        month = 9
    elif month == 15:  # Oct-Dec Quarter -> Dec
        month = 12
    elif month == 16:  # Jan-Mar Quarter -> Mar
        (month, year) = (3, year + 1)
    else:
        raise ValueError("Unexpected month")
    return datetime.date(year, month, 1)


def parse_ewb_datetime(s):
    """
    Parse datetime as received from EWB website.

    Example: "16/09/2017 10:30:00 AM"
    """
    try:
        return datetime.datetime.strptime(s, "%d/%m/%Y %I:%M:%S %p").replace(tzinfo=IST)
    except ValueError:
        pass
    return datetime.datetime.strptime(s, "%d/%m/%Y %H:%M:%S %p").replace(tzinfo=IST)


def parse_invoicing_datetime(s):
    """
    Parse datetime as received from EWB website.

    Example: "2020-04-13 23:30:00"
    """
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    except ValueError:
        return None


def parse_time(s):
    """
    Parse a time HH:MM:SS
    """
    if (s is None) or (s == ""):
        return None
    s = force_str(s)
    parts = s.split(":")
    if len(parts) == 2:
        (hh, mm) = parts
        ss = 0
    elif len(parts) == 3:
        (hh, mm, ss) = parts
    else:
        raise ValueError("Invalid time")
    try:
        (hh, mm, ss) = (int(hh), int(mm), int(ss))
    except ValueError:
        raise ValueError("Invalid time")
    return datetime.time(hh, mm, ss)
