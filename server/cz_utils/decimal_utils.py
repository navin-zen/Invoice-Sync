import decimal
from decimal import Context, Decimal, Inexact


def validate_num_decimals(d, num_decimals):
    """
    Validate that `d` has no more than `num_decimals` decimal places.
    """
    TWOPLACES = Decimal("0.01")
    decimal.Decimal(d).quantize(TWOPLACES, context=Context(traps=[Inexact]))


def python2round(f):
    """
    The builtin function round() has different behavior in Python 2 vs
    Python 3.

    See https://stackoverflow.com/questions/21839140/python-3-rounding-behavior-in-python-2

    In python2,
        round(2.5) == 3.0
        round(3.5) == 4.0

    In python3,
        round(2.5) == 2
        round(3.5) == 5

    This function ensures uniform behavior (the one provided by Python 2)
    in both Python 2 and Python 3.
    """
    if round(f + 1) - round(f) != 1:
        return f + abs(f) / f * 0.5
    return round(f)


def cz_round_n(d, n):
    """
    Round a decimal to `n` decimal places
    """
    multiple = 10**n
    if isinstance(d, decimal.Decimal):
        return (d * multiple).to_integral(rounding=decimal.ROUND_HALF_UP) / multiple
    elif isinstance(d, float):
        return python2round(d * multiple) / multiple
    else:
        return d


def cz_round(d):
    """
    Round a decimal to the nearest integer
    """
    return cz_round_n(d, 0)


def cz_round2(d):
    """
    Round to the nearest 2-decimal places.
    """
    return cz_round_n(d, 2)


def cz_round3(d):
    """
    Round to the nearest 3-decimal places.
    """
    return cz_round_n(d, 3)
