"""Ordinalize utility.

>>> from PyICe.lab_utils.ordinalize import ordinalize

"""
def ordinalize(num):
    """Format a non-negative integer with its English ordinal suffix (st, nd, rd, th).

    Handles the irregular teens (11th, 12th, 13th) correctly.

    >>> ordinalize(1)
    '1st'
    >>> ordinalize(2)
    '2nd'
    >>> ordinalize(3)
    '3rd'
    >>> ordinalize(11)
    '11th'
    >>> ordinalize(112)
    '112th'
    >>> ordinalize(122)
    '122nd'
    >>> ordinalize(0)
    '0th'
    >>> ordinalize(1001)
    '1001st'

    Args:
        num: Non-negative integer to format.
    """
    assert num >= 0 and isinstance(num, int)
    rem_10, rem_100 = num % 10, num % 100
    if rem_100 >= 20 or rem_100 <= 10:
        result = '{}{}'.format(
            num, ['th', 'st', 'nd', 'rd'][rem_10] if rem_10 <= 3 else 'th')
    else:
        result = '{}th'.format(num)
    return result
