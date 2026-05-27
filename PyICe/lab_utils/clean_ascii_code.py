"""Clean ascii code utility.

>>> from PyICe.lab_utils.clean_ascii_code import clean_ascii_code

"""
import re
from .clean_unicode import clean_unicode


def clean_ascii_code(ustr):
    """Transform an arbitrary string into a valid Python/SQL identifier.

    Replaces whitespace, punctuation, and operators with mnemonic tags
    (e.g., '-' becomes '_MNS_', '+' becomes '_PLS_'). Prepends an underscore
    if the result would start with a digit. Used to convert channel names from
    instrument queries into safe attribute names for data tables.

    >>> clean_ascii_code('hello world')
    'hello_world'
    >>> clean_ascii_code('a-b')
    'a_MNS_b'
    >>> clean_ascii_code('3volts')
    '_3volts'
    >>> clean_ascii_code('x+y')
    'x_PLS_y'
    >>> clean_ascii_code('Vout(mV)')
    'Vout_OPNP_mV_CLSP_'
    >>> clean_ascii_code('1.5V')
    '_1p5V'

    Args:
        ustr: Input string (may contain unicode, which is transliterated first).

    Raises:
        Exception: If a control character (< 0x30 or > 0x7A) remains after
            all substitutions.
    """
    astr = clean_unicode(ustr)
    astr = astr.replace("\t", "_")  # 0x09
    astr = astr.replace(" ", "_")  # 0x20
    astr = astr.replace("!", "_BANG_")  # 0x21
    astr = astr.replace('"', "_DQT_")  # 0x22
    astr = astr.replace("#", "_PND_")  # 0x23
    astr = astr.replace("$", "_DOL_")  # 0x24
    astr = astr.replace("%", "_PER_")  # 0x25
    astr = astr.replace("&", "_AND_")  # 0x26
    astr = astr.replace("'", "_SQT_")  # 0x27
    astr = astr.replace("(", "_OPNP_")  # 0x28
    astr = astr.replace(")", "_CLSP_")  # 0x29
    astr = astr.replace("*", "_MUL_")  # 0x2A
    astr = astr.replace("+", "_PLS_")  # 0x2B
    astr = astr.replace(",", "_COMA_")  # 0x2C
    astr = astr.replace("-", "_MNS_")  # 0x2D
    astr = astr.replace(".", "p")  # 0x2E
    astr = astr.replace("/", "_DIV_")  # 0x2F
    astr = astr.replace(":", "_CLN_")  # 0x3A
    astr = astr.replace(";", "_SCLN_")  # 0x3B
    astr = astr.replace("<", "_LSS_THN_")  # 0x3C
    astr = astr.replace("=", "_EQLS_")  # 0x3D
    astr = astr.replace(">", "_GRTR_THN_")  # 0x3E
    astr = astr.replace("?", "_QUES_")  # 0x3F
    astr = astr.replace("@", "_AT_")  # 0x40
    astr = astr.replace("[", "_OPNS_")  # 0x5B
    astr = astr.replace("\\", "_SLSH_")  # 0x5C
    astr = astr.replace("]", "_CLSS_")  # 0x5D
    astr = astr.replace("^", "_CAR_")  # 0x5E
    # 0x5F is '_'
    astr = astr.replace("`", "_GRAVE_")  # 0x60
    astr = astr.replace("{", "_OPNC_")  # 0x7B
    astr = astr.replace("|", "_OR_")  # 0x7C
    astr = astr.replace("}", "_CLSC_")  # 0x7D
    astr = astr.replace("~", "_TIL_")  # 0x7E

    # place leading underscore if word begins with a numeric digit.
    astr = re.sub(r'\b(\d)', r'_\1', astr)

    for c in astr:
        # all characters 0x20-0x2F, 0x3A-0x40, 0x5B-0x60 and 0x7B-0x7E already
        # replaced above.
        if ord(c) < 0x30 or ord(c) > 0x7A:
            raise Exception(
                'Ascii control character code point 0x{:X} found in: {}'.format(
                    ord(c), astr))

    return astr
