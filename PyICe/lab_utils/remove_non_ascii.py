"""Remove non ascii utility."""
def remove_non_ascii(text):
    """Replace characters above code point 127 with a placeholder marker.

    Used to sanitize instrument responses or filenames that may contain
    unexpected non-ASCII bytes before writing to logs or constructing paths.

    >>> remove_non_ascii('hello')
    'hello'
    >>> remove_non_ascii('100°C')
    '100(REMOVED_NON_ASCII)C'
    >>> remove_non_ascii('Résumé')
    'R(REMOVED_NON_ASCII)sum(REMOVED_NON_ASCII)'
    >>> remove_non_ascii('')
    ''

    Args:
        text: Input string potentially containing non-ASCII characters.
    """
    out = ''
    for c in text:
        # all characters 0x3A-0x40 and 0x5B-0x60 already replaced above.
        if ord(c) > 127:
            c = "(REMOVED_NON_ASCII)"
        out += c
    return out
