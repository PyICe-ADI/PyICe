import re
from .clean_ascii_code import clean_ascii_code

def clean_c(str):
    str = clean_ascii_code(str)

    c_reserved = [
    # https://en.wikipedia.org/wiki/C_syntax#Reserved_keywords
    'auto',
    '_Bool',
    'break',
    'case',
    'char',
    '_Complex',
    'const',
    'continue',
    'default',
    'do',
    'double',
    'else',
    'enum',
    'extern',
    'float',
    'for',
    'goto',
    'if',
    '_Imaginary',
    'inline',
    'int',
    'long',
    'register',
    'restrict',
    'return',
    'short',
    'signed',
    'sizeof',
    'static',
    'struct',
    'switch',
    'typedef',
    'union',
    'unsigned',
    'void',
    'volatile',
    'while'
    ]

    #YODA not yet checked.
    yoda_reserved = [
    # https://www.secad.analog.com/dek/sites/default/files/reservedWords_0.txt
    'ABS',
    'AND',
    'AS',
    'ASC',
    'ATN',
    'BASE',
    'BOOLEAN',
    'BYREF',
    'BYVAL',
    'CALL',
    'CASE',
    'CBOOL',
    'CBYTE',
    'CCUR',
    'CDATE',
    'CDBL',
    'CDEC',
    'CHDIR',
    'CHDRIVE',
    'CHOOSE',
    'CHR',
    'CINT',
    'CLNG',
    'COMPARE',
    'CONST',
    'COS',
    'CSNG',
    'CSTR',
    'CURDIR',
    'CVAR',
    'DATABASE',
    'DATE',
    'DATEADD',
    'DATEDIFF',
    'DATEPART',
    'DATESERIAL',
    'DATEVALUE',
    'DAY',
    'DDB',
    'DEBUG',
    'DECLARE',
    'DEFBOOL',
    'DEFBYTE',
    'DEFDATE',
    'DEFDEC',
    'DEFDOUBLE',
    'DEFINT',
    'DEFLNG',
    'DEFLNGLNG',
    'DEFLNGPTR',
    'DEFOBJ',
    'DEFSNG',
    'DEFSTR',
    'DIM',
    'DIR',
    'DO',
    'DOUBLE',
    'EACH',
    'ELSE',
    'ELSEIF',
    'END',
    'ENUM',
    'ENVIRON',
    'ERROR',
    'EVENT',
    'EXIT',
    'EXP',
    'EXPLICIT',
    'FILEDATETIME',
    'FILELEN',
    'FIX',
    'FOR',
    'FRIEND',
    'FUNCTION',
    'FV',
    'GET',
    'GETATTR',
    'GOTO',
    'HOUR',
    'IF',
    'IIF',
    'IMPLEMENTS',
    'INSTR',
    'INSTRREV',
    'INT',
    'IPMT',
    'IRR',
    'ISDATE',
    'ISEMPTY',
    'ISERROR',
    'ISNULL',
    'ISNUMERIC',
    'LBOUND',
    'LCASE',
    'LEFT',
    'LEN',
    'LET',
    'LIB',
    'LOG',
    'LONG',
    'LONGLONG',
    'LOOP',
    'LTRIM',
    'ME',
    'MID',
    'MINUTE',
    'MIRR',
    'MKDIR',
    'MONTH',
    'MONTHNAME',
    'NEW',
    'NEXT',
    'NOTHING',
    'NOW',
    'NPER',
    'NPV',
    'NULL',
    'OBJECT',
    'ON',
    'OPTION',
    'OPTIONAL',
    'OR',
    'PMT',
    'PPMT',
    'PRESERVE',
    'PRIVATE',
    'PROPERTY',
    'PUBLIC',
    'PV',
    'RANDOMIZE',
    'RATE',
    'REDIM',
    'REPLACE',
    'RESUME',
    'RETURN',
    'RIGHT',
    'RND',
    'ROUND',
    'RSET',
    'RTRIM',
    'SELECT',
    'SET',
    'SETATTR',
    'SGN',
    'SIN',
    'SINGLE',
    'SLN',
    'SPACE',
    'SPLIT',
    'SQR',
    'STATIC',
    'STOP',
    'STR',
    'STRCOMP',
    'STRCONV',
    'STRREVERSE',
    'SUB',
    'SWITCH',
    'SYD',
    'TAN',
    'TEXT',
    'THEN',
    'TIMESERIAL',
    'TIMEVALUE',
    'TO',
    'TRIM',
    'TYPE',
    'TYPEOF',
    'UCASE',
    'UNTIL',
    'VAL',
    'WEEKDAY',
    'WEEKDAYNAME',
    'WEND',
    'WHILE',
    'WITH',
    'YEAR',
    'RESERVED',
    'SPARE',
    'UNUSED',
    'ERROR',
    'REGISTER',
    'BITFIELD',
    'ENUMERATION',
    'VALUE',
    ]

    for res in c_reserved:
        if re.search(r'\b{}\b'.format(res), str) is not None:
            raise Exception('Found "{}" reserved keyword in c cleaned string: "{}"'.format(res,str))


    #if re.search(r'\b_', str) is not None: # external identifiers
    if re.search(r'\b__?[A-Z]', str) is not None: # internal identifiers
        err_msg = 'Found illegal leading underscore followed by capital letter in C cleaned string: "{}"\n'.format(str)
        err_msg += 'http://www.gnu.org/s/libc/manual/html_node/Reserved-Names.html\n'
        err_msg += '# In addition to the names documented in this manual, reserved names include all external identifiers (global functions and variables) that begin with an underscore and all identifiers regardless of use that begin with either two underscores or an underscore followed by a capital letter are reserved names. This is so that the library and header files can define functions, variables, and macros for internal purposes without risk of conflict with names in user programs.'
        raise Exception(err_msg)

    '''
    http://www.gnu.org/s/libc/manual/html_node/Reserved-Names.html'''
    err_msg = 'WARNING: Found reserved pattern ({{}}) in c cleaned string: "{}"'.format(str)
    '''
    Names beginning with a capital ‘E’ followed a digit or uppercase letter may be used for additional error code names. See Error Reporting.'''
    pattern = r'\bE[A-Z0-9]'
    if re.search(pattern, str) is not None:
        print(err_msg.format(pattern))

    '''
    Names that begin with either ‘is’ or ‘to’ followed by a lowercase letter may be used for additional character testing and conversion functions. See Character Handling.'''
    pattern = r'\b(?:is|to)[a-z]'
    if re.search(pattern, str) is not None:
        print(err_msg.format(pattern))

    '''
    Names that begin with ‘LC_’ followed by an uppercase letter may be used for additional macros specifying locale attributes. See Locales.'''
    pattern = r'\bLC_[A-Z]'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))

    '''
    Names of all existing mathematics functions (see Mathematics) suffixed with ‘f’ or ‘l’ are reserved for corresponding functions that operate on float and long double arguments, respectively.'''

    '''
    Names that begin with ‘SIG’ followed by an uppercase letter are reserved for additional signal names. See Standard Signals.
    Names that begin with ‘SIG_’ followed by an uppercase letter are reserved for additional signal actions. See Basic Signal Handling.'''
    pattern = r'\bSIG_?[A-Z]'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))

    '''
    Names beginning with ‘str’, ‘mem’, or ‘wcs’ followed by a lowercase letter are reserved for additional string and array functions. See String and Array Utilities.'''
    pattern = r'\bstr[a-z]'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))
    pattern = r'\bmem[a-z]'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))
    pattern = r'\bwcs[a-z]'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))

    '''
    Names that end with ‘_t’ are reserved for additional type names.'''
    pattern = r'_t\b'
    if re.search(pattern, str) is not None:
        raise Exception(err_msg.format(pattern))

    '''
    The header file dirent.h reserves names prefixed with ‘d_’.
    The header file fcntl.h reserves names prefixed with ‘l_’, ‘F_’, ‘O_’, and ‘S_’.
    The header file grp.h reserves names prefixed with ‘gr_’.
    The header file limits.h reserves names suffixed with ‘_MAX’.
    The header file pwd.h reserves names prefixed with ‘pw_’.
    The header file signal.h reserves names prefixed with ‘sa_’ and ‘SA_’.
    The header file sys/stat.h reserves names prefixed with ‘st_’ and ‘S_’.
    The header file sys/times.h reserves names prefixed with ‘tms_’.
    The header file termios.h reserves names prefixed with ‘c_’, ‘V’, ‘I’, ‘O’, and ‘TC’; and names prefixed with ‘B’ followed by a digit.
    '''
    return str