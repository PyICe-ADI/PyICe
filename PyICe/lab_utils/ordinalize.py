def ordinalize(num):
    "Convert positive integer to ordinal number, e.g. 1 -> 1st, 2 -> 2nd, 112 -> 112th, 122 -> 122nd."
    assert num >= 0 and isinstance(num, int)
    rem_10, rem_100 = num % 10, num % 100
    if rem_100 >= 20 or rem_100 <= 10:
        result = '{}{}'.format(num, ['th', 'st', 'nd', 'rd'][rem_10] if rem_10 <= 3 else 'th')
    else:
        result = '{}th'.format(num)
    return result