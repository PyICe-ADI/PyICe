def bounded(value, min_value=None, max_value=None, key=None):
    kwargs = {}
    if key is not None:
        kwargs['key'] = key
    if min_value is not None and max_value is not None:
        return max(min(value, max_value, **kwargs), min_value, **kwargs)
    elif min_value is None and max_value is not None:
        return min(value, max_value, **kwargs)
    elif min_value is not None and max_value is None:
        return max(value, min_value, **kwargs)
    return value