import math, numbers

def eng_string(x, fmt=':.3g', si=True, units=None):
    '''
    Returns float/int value <x> formatted in a simplified engineering format -
    using an exponent that is a multiple of 3.

    format: printf-style string used to format the value before the exponent.

    si: if true, use SI suffix for exponent, e.g. k instead of e3, n instead of
    e-9 etc.

    E.g. with format='%.2f':
        1.23e-08 => 12.30e-9
             123 => 123.00
          1230.0 => 1.23e3
      -1230000.0 => -1.23e6

    and with si=True:
          1230.0 => 1.23k
      -1230000.0 => -1.23M
    '''
    assert isinstance(x,numbers.Number)
    if x == 0 or not math.isfinite(x):
        return '{{{}}}'.format(fmt).format(x)
    sign = ''
    if x < 0:
        x = -x
        sign = '-'
    exp = math.floor(math.log10(x))
    exp3 = exp - ( exp % 3)
    if si and exp3 >= -24 and exp3 <= 24 and exp3 != 0:
        exp3_text = 'yzafpnµm kMGTPEZY'[ ( exp3 - (-24)) // 3]
    elif exp3 == 0:
        exp3_text = ''
    else:
        exp3_text = f'e{exp3:d}'
    s1 = f"{sign}{{{fmt}}}"
    return f"{s1.format(x / ( 10 ** exp3))}{exp3_text}{units if units is not None else ''}"