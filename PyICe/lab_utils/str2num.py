def str2num(str_in, except_on_error=True):
    '''Convert string to numeric type with automatic base detection.

    >>> str2num('42')
    42
    >>> str2num('0xFF')
    255
    >>> str2num('3.14')
    3.14
    >>> str2num('True')
    True
    >>> str2num(None) is None
    True
    >>> str2num('hello', except_on_error=False)
    'hello'
    '''
    if isinstance(str_in, int) or isinstance(str_in, float) or str_in is None:
        return str_in
    if str_in == 'True':
        return True
    if str_in == 'False':
        return False
    try:
        return int(str_in, 0)  # automatically select base
    except ValueError:
        try:
            return float(str_in)
        except ValueError as e:
            if except_on_error:
                print(
                    "string failed to convert both to integer (automatic base selection) and float: {}".format(str))
                raise e
            else:
                # just return original string
                return str_in
