import re
from .clean_unicode import clean_unicode

def clean_ascii_code(ustr):
    astr = clean_unicode(ustr)
    astr = astr.replace("\t","_") #0x09
    astr = astr.replace(" ","_") #0x20
    astr = astr.replace("!","_BANG_") #0x21
    astr = astr.replace('"',"_DQT_") #0x22
    astr = astr.replace("#","_PND_") #0x23
    astr = astr.replace("$","_DOL_") #0x24
    astr = astr.replace("%","_PER_") #0x25
    astr = astr.replace("&","_AND_") #0x26
    astr = astr.replace("'","_SQT_") #0x27
    astr = astr.replace("(","_OPNP_") #0x28
    astr = astr.replace(")","_CLSP_") #0x29
    astr = astr.replace("*","_MUL_") #0x2A
    astr = astr.replace("+","_PLS_") #0x2B
    astr = astr.replace(",","_COMA_") #0x2C
    astr = astr.replace("-","_MNS_") #0x2D
    astr = astr.replace(".","p") #0x2E
    astr = astr.replace("/","_DIV_") #0x2F
    astr = astr.replace(":","_CLN_") #0x3A
    astr = astr.replace(";","_SCLN_") #0x3B
    astr = astr.replace("<","_LSS_THN_") #0x3C
    astr = astr.replace("=","_EQLS_") #0x3D
    astr = astr.replace(">","_GRTR_THN_") #0x3E
    astr = astr.replace("?","_QUES_") #0x3F
    astr = astr.replace("@","_AT_") #0x40
    astr = astr.replace("[","_OPNS_") #0x5B
    astr = astr.replace("\\","_SLSH_") #0x5C
    astr = astr.replace("]","_CLSS_") #0x5D
    astr = astr.replace("^","_CAR_") #0x5E
    #0x5F is '_'
    astr = astr.replace("`","_GRAVE_") #0x60
    astr = astr.replace("{","_OPNC_") #0x7B
    astr = astr.replace("|","_OR_") #0x7C
    astr = astr.replace("}","_CLSC_") #0x7D
    astr = astr.replace("~","_TIL_") #0x7E

    astr = re.sub(r'\b(\d)', r'_\1', astr) #place leading underscore if word begins with a numeric digit.

    for c in astr:
        #all characters 0x20-0x2F, 0x3A-0x40, 0x5B-0x60 and 0x7B-0x7E already replaced above.
        if ord(c) < 0x30 or ord(c) > 0x7A:
            raise Exception('Ascii control character code point 0x{:X} found in: {}'.format(ord(c),astr))

    return astr