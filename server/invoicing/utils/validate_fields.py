import datetime
import decimal
import re
import string

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.encoding import force_str
from invoicing.utils.datamapper.purchase_fields_spec import COLUMN_MAPPING_DEFAULTS
from invoicing.utils.utils import cz_round3, month_range, to_decimal
from pygstn.utils.gstin import GstinUtils

from cz_utils.dateparse import parse_date, pretty_date_format
from cz_utils.exceptions import ValueErrorWithCode

UNITS = [
    ("BAG", "BAGS"),
    ("BAL", "BALE"),
    ("BDL", "BUNDLES"),
    ("BKL", "BUCKLES"),
    ("BOU", "BILLIONS OF UNITS"),
    ("BOX", "BOX"),
    ("BTL", "BOTTLES"),
    ("BUN", "BUNCHES"),
    ("CAN", "CANS"),
    ("CBM", "CUBIC METER"),
    ("CCM", "CUBIC CENTIMETER"),
    ("CMS", "CENTIMETER"),
    ("CTN", "CARTONS"),
    ("DOZ", "DOZEN"),
    ("DRM", "DRUM"),
    ("GGK", "GREAT GROSS"),
    ("GMS", "GRAMS"),
    ("GRS", "GROSS"),
    ("GYD", "GROSS YARDS"),
    ("KGS", "KILOGRAMS"),
    ("KLR", "KILOLITER"),
    ("KME", "KILOMETERS"),
    ("MLT", "MILLILITER"),
    ("MTR", "METER"),
    ("MTS", "METRIC TON"),
    ("NOS", "NUMBER"),
    ("PAC", "PACKS"),
    ("PCS", "PIECES"),
    ("PRS", "PAIRS"),
    ("QTL", "QUINTAL"),
    ("ROL", "ROLLS"),
    ("SET", "SETS"),
    ("SQF", "SQUARE FEET"),
    ("SQM", "SQUARE METER"),
    ("SQY", "SQUARE YARDS"),
    ("TBS", "TABLETS"),
    ("TGM", "TEN GRAMS"),
    ("THD", "THOUSANDS"),
    ("TON", "GREAT BRITAIN TON"),
    ("TUB", "TUBES"),
    ("UGS", "US GALLONS"),
    ("UNT", "UNITS"),
    ("YDS", "YARDS"),
    ("OTH", "OTHERS"),
]

UNIT_SHORT_NAMES = {u for (u, _) in UNITS}

GSTIN_ALLOWED_CHARS = string.ascii_lowercase + string.ascii_uppercase + string.digits

INVOICE_NUMBER_ALLOWED_CHARS = string.ascii_uppercase + string.digits + "/-"


def validate_phno(s):
    """
    This function is not complete
    """
    return validate_str(s)


def validate_emailid(s):
    """
    This function is not complete
    """
    if not isinstance(s, str):
        return None
    if s == "":
        return None
    s1 = s.strip()
    try:
        validate_email(s1)
        return s1
    except ValidationError:
        pass
    raise ValueError(f"Invalid Email-ID '{s}'")


def convert2integer(s):
    """
    This function returns an integer
    """
    if s is None:
        return s
    if isinstance(s, str):
        s1 = "".join(c for c in s if (c in string.digits))
        if not s1:
            return None
        try:
            return int(s1)
        except ValueError:
            raise ValueErrorWithCode(f"Invalid integer/number {s}", code="z:validation:integer")
    try:
        return int(s)
    except ValueError:
        raise ValueErrorWithCode(f"Invalid integer/number {s}", code="z:validation:integer")


def validate_unit(s, default=COLUMN_MAPPING_DEFAULTS["LineItem.Unit"]["value"]):
    """
    Check if unit is available in the list of units if not, return OTH
    """
    if s is None or s == "":
        return default
    if not isinstance(s, str):
        return default
    if isinstance(s, str):
        name = s.strip().split("-")[0].strip().upper()
        if name in UNIT_SHORT_NAMES:
            return name
    return default


def validate_invtype(s, default="INV"):
    """
    Check if invoice type is INV or CRN or DBN if empty return INV
    """
    if s is None or s == "":
        return default
    if isinstance(s, str):
        c = s.strip().upper()[0]
        if c == "I":
            return "INV"
        elif c == "C":
            return "CRN"
        elif c == "D":
            return "DBN"
        elif "INVOICE" in s.upper():
            return "INV"
        elif "CREDIT" in s.upper():
            return "CRN"
        elif "DEBIT" in s.upper():
            return "DBN"
    raise ValueError(f"Invalid Invoice type '{s}'")


def validate_invoicing_gstin(s):
    if s is None or s == "":
        raise ValueError(f"GSTIN '{s}' is a mandatory field")
    if isinstance(s, str):
        s1 = "".join(c for c in s if (c in GSTIN_ALLOWED_CHARS))
        if GstinUtils.validate_gstin(s1):
            return s1
    if GstinUtils.validate_gstin(s):
        return s


def validate_invoicing_transin(s):
    if s is None or s == "":
        raise ValueError(f"TRANSIN '{s}' is a mandatory field")
    if isinstance(s, str):
        s1 = "".join(c for c in s if (c in GSTIN_ALLOWED_CHARS))
        if GstinUtils.validate_transin(s1):
            return s1
    if GstinUtils.validate_transin(s):
        return s


def validate_invoicing_optional_gstin(s):
    """
    The GSTIN can be optional of that of URP
    """
    if s is None or s == "":
        return None
    if isinstance(s, str):
        if s.strip() == "":
            return None
        if s.strip().upper().startswith("U"):
            return None
    return validate_invoicing_gstin(s)


def validate_invoicing_optional_transin(s):
    """
    The GSTIN can be optional of that of URP
    """
    if s is None or s == "":
        return None
    if isinstance(s, str):
        if s.strip() == "":
            return None
    return validate_invoicing_transin(s)


def validate_pincode(s):
    """
    Check if the pincode is within 99999 and 1000000
    """
    if not s:
        return None
    if isinstance(s, int) or isinstance(s, decimal.Decimal) or isinstance(s, float):
        i = int(s)
    elif isinstance(s, str):
        try:
            i = int("".join(c for c in s if (c in string.digits)))
        except ValueError:
            raise ValueError(f"Invalid Pincode '{s}'")
    else:
        raise ValueError(f"Invalid Pincode '{s}'")
    if 100000 <= i <= 999999:
        return i
    raise ValueErrorWithCode(f"Invalid Pincode '{s}'", code="z:validation:invalid-pincode")


TRANSPORT_MODE_MAP = {
    None: None,
    "": None,
    1: "1",
    2: "2",
    3: "3",
    4: "4",
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "ROAD": "1",
    "RAIL": "2",
    "AIR": "3",
    "SHIP": "4",
}


def validate_transport_mode(s):
    if not s:
        return None
    try:
        if isinstance(s, (int,) + (float, decimal.Decimal)):
            return TRANSPORT_MODE_MAP[int(s)]
        elif isinstance(s, str):
            return TRANSPORT_MODE_MAP[s.strip().upper()]
    except KeyError:
        pass
    raise ValueErrorWithCode(f"Invalid Transport Mode {s}", code="z:validation:ewb-transport-mode")


def validate_str(s):
    if s is None:
        return s
    if isinstance(s, datetime.date):
        return pretty_date_format(s)
    return str(s)


def parse_invoice_number_internal(s):
    if s is None:
        return ""
    if isinstance(s, str):
        return s.strip().replace(" ", "").replace("_x000D_", "")
    if isinstance(s, int):
        return force_str(s)
    if isinstance(s, float):
        if int(s) == s:
            return force_str(int(s))
        else:
            return force_str(s)
    if isinstance(s, decimal.Decimal):
        if int(s) == s:
            return force_str(int(s))
        else:
            return force_str(s)
    if isinstance(s, datetime.datetime):
        return force_str(s.date())
    return force_str(s)


def parse_invoice_number(s):
    s = parse_invoice_number_internal(s)
    return s.upper() if isinstance(s, str) else s


def validate_invnumber(s):
    """
    Check if the invoice number is within the range 0-16 and does not have non alpha-numeric characters
    """
    s = parse_invoice_number(s)
    if isinstance(s, str):
        s = re.sub(r"^[0/-]+", "", s)
    if s is None or s == "":
        raise ValueError("Invoice Number is a mandatory Field")
    if not (1 <= len(s) <= 16):
        raise ValueError(f"Invalid Invoice Number '{s}'")
    if not re.match(r"^[1-9A-Z][A-Z0-9/-]{0,15}$", s):
        raise ValueError(f"Invalid Invoice Number '{s}'")
    return s


def validate_invnumber_autocorrect(s):
    """
    Validate invoice number and ensure it is always correct. Only keep valid
    characters in the invoice number.

    Used for fields such as Purchase order number
    """
    s = parse_invoice_number(s) or ""
    return "".join(c for c in s.upper() if (c in INVOICE_NUMBER_ALLOWED_CHARS)) or None


def validate_hsncode(s):
    """
    Check if the hsn code is numeric and of length 4,6 or 8.
    """
    if s is None or s == "":
        raise ValueError("HSN code is a mandatory field")
    if isinstance(s, int):
        s = str(s)
    if not isinstance(s, str):
        raise ValueError(f"Invalid HSN code '{s}'")
    if re.match(r"[0-9]{4,8}", s) is None:
        raise ValueError(f"Invalid HSN code '{s}'")
    if len(s) != 4 and len(s) != 6 and len(s) != 8:
        raise ValueError(f"Invalid HSN code '{s}'")
    return str(s)


def qty_to_decimal_round3(v, default=int(COLUMN_MAPPING_DEFAULTS["LineItem.Qty"]["value"])):
    """
    Returns quantity value rounded to 2 decimal places or sets it to the default value if none.
    """
    if v is None or v == "":
        return default
    if not isinstance(v, str):
        return cz_round3(to_decimal(v))
    if isinstance(v, str):
        try:
            return cz_round3(to_decimal(v))
        except Exception:
            return default
    return default


def validate_date(v):
    """
    Returns quantity value rounded to 2 decimal places or sets it to the default value if none.
    """
    if v is None:
        raise ValueError("Invoice date not provided")
    elif isinstance(v, str) and not v.strip():
        raise ValueError("Invoice date not provided")
    return parse_date(v)


def validate_optional_date(v):
    if v is None:
        return None
    else:
        return validate_date(v)


def validate_revchrg_and_isexp(s, default="N"):
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
        return "Y"
    elif s_upper in ["N", "NO"]:
        return "N"
    else:
        raise ValueError(f"Invalid Yes/No value: '{s}'. Valid choices are 'Y' or 'N'.")


ALTERNATE_TRANSACTION_TYPE_MAP = {
    "SEWP": "SEZWP",
    "SEWOP": "SEZWOP",
    "WPAY": "EXPWP",
    "WOPAY": "EXPWOP",
    "DE": "DEXP",
    "R": "B2B",
    "SEZ": "SEZWOP",
    "REGULAR": "B2B",
    "REGISTERED": "B2B",
}


def validate_transaction_type(s):
    """
    Validate the type of Invoicing (Invoicing) transaction.
    """
    if not s:
        return "B2B"
    if not isinstance(s, str):
        raise ValueErrorWithCode(
            f"Invalid Invoicing Transaction Type: {s}", code="z:validation:invoicing-transaction-type"
        )
    s1 = s.strip().upper()
    if not s1:
        return "B2B"
    if s1 in ["B2B", "SEZWP", "SEZWOP", "EXPWP", "EXPWOP", "DEXP", "B2C", "B2CL"]:
        return s1
    if s1 in ALTERNATE_TRANSACTION_TYPE_MAP:
        return ALTERNATE_TRANSACTION_TYPE_MAP[s1]
    raise ValueErrorWithCode(f"Invalid Invoicing Transaction Type: {s}", code="z:validation:invoicing-transaction-type")


def absolute_value(s):
    if isinstance(s, int):
        return abs(s)
    elif isinstance(s, decimal.Decimal):
        return abs(s)
    else:
        return s


def left_16(s):
    if isinstance(s, str):
        return s[:16]
    else:
        return s


def right_16(s):
    if isinstance(s, str):
        return s[-16:]
    else:
        return s


def month_end(s):
    if isinstance(s, datetime.date):
        return month_range(s)[1]
    else:
        return s


def blank_errors(s):
    return s


USER_TRANSFORMS = {
    "absolute_value": absolute_value,
    "left_16": left_16,
    "right_16": right_16,
    "month_end": month_end,
    "blank_errors": blank_errors,
}


