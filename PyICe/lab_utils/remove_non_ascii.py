"""Remove non ascii utility."""
def remove_non_ascii(text):
    """Remove a non ascii.

    Args:
        text: Text.

    Returns:
        Result value.
    """
    out = ''
    for c in text:
        # all characters 0x3A-0x40 and 0x5B-0x60 already replaced above.
        if ord(c) > 127:
            c = "(REMOVED_NON_ASCII)"
        out += c
    return out
