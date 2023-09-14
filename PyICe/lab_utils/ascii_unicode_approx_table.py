#
# ASCII approximate translations for use in unicode.translate()
#
# print u"Ω = 2.8 µV/°C × β² ± 12nV".translate(ascii_unicode_approx_table).encode("ascii")
# produces:
#    _ohm = 2.8 uV/_deg_C x Beta^2 +/- 12nV
#
ascii_unicode_approx_table =  \
       { ord('\N{DEGREE SIGN}'):                 '_deg_',
         ord('\N{MULTIPLICATION SIGN}'):         'x',
         ord('\N{GREEK SMALL LETTER MU}'):       'u',    # preferred micro sign
         ord('\N{MICRO SIGN}'):                  'u',    # deprecated micro sign
         ord('\N{REGISTERED SIGN}'):             '(R)',
         ord('\N{PLUS-MINUS SIGN}'):             '+/-',
         ord('\N{SUPERSCRIPT TWO}'):             '^2',
         ord('\N{GREEK CAPITAL LETTER OMEGA}'):  '_ohm', # preferred ohm symbol
         ord('\N{OHM SIGN}'):                    '_ohm', # deprecated ohm symbol
         ord('\N{GREEK SMALL LETTER BETA}'):     'Beta'  }