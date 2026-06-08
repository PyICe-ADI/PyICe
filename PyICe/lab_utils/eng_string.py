"""Eng string utility.

>>> from PyICe.lab_utils.eng_string import eng_string

"""
import math
import numbers


def eng_string(x, fmt=':.3g', si=True, units=None):
    """Format a number using engineering notation (exponents that are multiples of 3).

    Converts raw numeric values into human-readable strings with SI prefixes
    (k, M, G, m, µ, n, etc.) — the format typically used on instrument displays
    and in datasheets.

    >>> eng_string(0.001)
    '1m'
    >>> eng_string(1230000.0)
    '1.23M'
    >>> eng_string(0)
    '0'
    >>> eng_string(4700, units='V')
    '4.7kV'
    >>> eng_string(-0.000047)
    '-47µ'
    >>> eng_string(1e-12)
    '1p'
    >>> eng_string(2.5e9, units='Hz')
    '2.5GHz'
    >>> eng_string(0.1, fmt=':.2f')
    '100.00m'
    >>> eng_string(47000, si=False)
    '47e3'
    >>> eng_string(float('inf'))
    'inf'

    Args:
        x: Numeric value to format.
        fmt: Format spec applied to the mantissa (default ':.3g').
        si: If True, use SI prefix letters; if False, use e-notation.
        units: Optional unit string appended after the SI prefix.
    """
    assert isinstance(x, numbers.Number)
    if x == 0 or not math.isfinite(x):
        return '{{{}}}'.format(fmt).format(x)
    sign = ''
    if x < 0:
        x = -x
        sign = '-'
    exp = math.floor(math.log10(x))
    exp3 = exp - (exp % 3)
    if si and exp3 >= -24 and exp3 <= 24 and exp3 != 0:
        exp3_text = 'yzafpnµm kMGTPEZY'[(exp3 - (-24)) // 3]
    elif exp3 == 0:
        exp3_text = ''
    else:
        exp3_text = f'e{exp3:d}'
    s1 = f"{sign}{{{fmt}}}"
    return f"{s1.format(x / (10 ** exp3))}{exp3_text}{units if units is not None else ''}"
