def unit_least_precision(val, increasing=True):
    '''return positive increment/decrement to next representable floating point number above/below val'''
    if increasing:
        return float_next(val) - val
    else:
        return val - float_prior(val)