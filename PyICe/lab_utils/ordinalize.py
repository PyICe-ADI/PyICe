"""Ordinalize utility."""
def ordinalize(num):
    """Convert positive integer to ordinal number.

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

    Args:
        num: Count or number.

    Returns:
        Result value.
    """
    assert num >= 0 and isinstance(num, int)
    rem_10, rem_100 = num % 10, num % 100
    if rem_100 >= 20 or rem_100 <= 10:
        result = '{}{}'.format(
            num, ['th', 'st', 'nd', 'rd'][rem_10] if rem_10 <= 3 else 'th')
    else:
        result = '{}th'.format(num)
    return result
