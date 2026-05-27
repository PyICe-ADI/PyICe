"""Clean unicode utility.

>>> from PyICe.lab_utils.clean_unicode import clean_unicode

"""
import unicodedata


def clean_unicode(ustr):
    """Replace common engineering Unicode symbols with ASCII mnemonic tags.

    Handles degree (°→_DEG_), micro (µ→_MICRO_), ohm (Ω→_OHM_), multiply
    (×→_MUL_), and other symbols frequently seen in instrument channel names
    and datasheet notation. Raises if an unrecognized non-ASCII character remains.

    >>> clean_unicode('100°C')
    '100_DEG_C'
    >>> clean_unicode('10µA')
    '10_MICRO_A'
    >>> clean_unicode('50Ω')
    '50_OHM_'
    >>> clean_unicode('hello')
    'hello'
    >>> clean_unicode('R²')
    'R_SQ_'
    >>> clean_unicode('β=100')
    '_BETA_=100'

    Args:
        ustr: Input string potentially containing Unicode engineering symbols.

    Raises:
        Exception: If a non-ASCII character above 0x7E remains after all
            substitution rules are applied. Edit this function to add the
            missing character mapping.
    """
    # limited Unicode substitution
    ustr = ustr.replace("®", "_REG_")  # 0x00AE
    ustr = ustr.replace("°", "_DEG_")  # 0x00B0
    ustr = ustr.replace("²", "_SQ_")  # 0x00B2
    ustr = ustr.replace("µ", "_MICRO_")  # 0x00B5
    ustr = ustr.replace("×", "_MUL_")  # 0x00D7
    ustr = ustr.replace("÷", "_DIV_")  # 0x00F7
    ustr = ustr.replace("Ω", "_OHM_")  # 0x03A9
    ustr = ustr.replace("β", "_BETA_")  # 0x03B2
    ustr = ustr.replace("≤", "_LTEQ_")  # 0x2264
    ustr = ustr.replace("≥", "_GTEQ_")  # 0x2265
    ustr = ustr.replace("─", "*")  # 0x2500
    ustr = ustr.replace("│", "*")  # 0x2502
    ustr = ustr.replace("┌", "*")  # 0x250C
    ustr = ustr.replace("┐", "*")  # 0x2510
    ustr = ustr.replace("└", "*")  # 0x2514
    ustr = ustr.replace("┘", "*")  # 0x2518
    for c in ustr:
        if ord(c) > 0x7E:
            raise Exception(
                f'Ascii non-alphanumeric character code point 0x{ord(c):X} ({unicodedata.name(c)}) found in: {ustr.encode("utf-8")}. Edit lab_utils.clean_unicode() translation rules to add this character.')
    return str(ustr)  # force non-unicode type
