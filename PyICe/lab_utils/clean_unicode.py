import unicodedata

def clean_unicode(ustr):
    '''Limited Unicode substitution to ASCII-safe equivalents.

    >>> clean_unicode('100°C')
    '100_DEG_C'
    >>> clean_unicode('10µA')
    '10_MICRO_A'
    >>> clean_unicode('50Ω')
    '50_OHM_'
    >>> clean_unicode('hello')
    'hello'
    '''
    #limited Unicode substitution
    ustr = ustr.replace("®","_REG_")   #0x00AE
    ustr = ustr.replace("°","_DEG_")   #0x00B0
    ustr = ustr.replace("²","_SQ_")    #0x00B2
    ustr = ustr.replace("µ","_MICRO_") #0x00B5
    ustr = ustr.replace("×","_MUL_")   #0x00D7
    ustr = ustr.replace("÷","_DIV_")   #0x00F7
    ustr = ustr.replace("Ω","_OHM_")   #0x03A9
    ustr = ustr.replace("β","_BETA_")  #0x03B2
    ustr = ustr.replace("≤","_LTEQ_")  #0x2264
    ustr = ustr.replace("≥","_GTEQ_")  #0x2265
    ustr = ustr.replace("─","*")  #0x2500
    ustr = ustr.replace("│","*")  #0x2502
    ustr = ustr.replace("┌","*")  #0x250C
    ustr = ustr.replace("┐","*")  #0x2510
    ustr = ustr.replace("└","*")  #0x2514
    ustr = ustr.replace("┘","*")  #0x2518
    for c in ustr:
        if ord(c) > 0x7E:
            raise Exception(f'Ascii non-alphanumeric character code point 0x{ord(c):X} ({unicodedata.name(c)}) found in: {ustr.encode("utf-8")}. Edit lab_utils.clean_unicode() translation rules to add this character.')
    return str(ustr) #force non-unicode type