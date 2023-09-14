def safe_divide(a, b):
    '''try to divide a by b, returning None for ZeroDivision and Type errors'''
    try:
        return a/b
    except (ZeroDivisionError, TypeError):
        return None
    except:
        raise