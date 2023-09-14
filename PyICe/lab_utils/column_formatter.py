def column_formatter(rows_of_columns, padding=3, justification="left", fist_line_justification="center"):
    '''takes data of form: [['ID:', 'REL_NOW_TIME', 'DURATION', 'FMT', 'RAW ', 'COUNT'],
                            [u'00:', '-00:00:35.290 ', ' 00:00:00.431 ', u'41.974488V', 28438, 1],
                            [u'01:', '-00:00:34.859 ', ' 00:00:07.216 ', u'-20.675808V', 51528, 1],
                            [u'02:', '-00:00:27.643 ', ' 00:00:00.586 ', u'-30.318516V', 44995, 1],
                            [u'03:', '-00:00:27.057 ', ' 00:00:17.777 ', u'38.97378V', 26405, 1],
                            [u'04:', '-00:00:09.280 ', ' 00:00:00.897 ', u'21.428568V', 14518, 1],
                            [u'05:', '-00:00:08.383 ', ' 00:00:08.383+', u'-23.781312V', 49424, 1]
                           ]
    produces formatted output of form: ID:    REL_NOW_TIME       DURATION          FMT        RAW    COUNT
                                       00:   -00:00:35.290     00:00:00.431    41.974488V    28438   1
                                       01:   -00:00:34.859     00:00:07.216    -20.675808V   51528   1
                                       02:   -00:00:27.643     00:00:00.586    -30.318516V   44995   1
                                       03:   -00:00:27.057     00:00:17.777    38.97378V     26405   1
                                       04:   -00:00:09.280     00:00:00.897    21.428568V    14518   1
                                       05:   -00:00:08.383     00:00:08.383+   -23.781312V   49424   1
    padding sets spacing between columns
    first_line_justification and justification control aligment for first and subsequent lines respectively.
        valid arguments are 'left','right' and 'center'
    '''
    #TODO: decimal alignment. Need to know decimal position apriori.
    # def dot_aligned(seq, width):
        # snums = [str(n) for n in seq]
        # dots = [len(s.split('.', 1)[0]) for s in snums]
        # m = max(dots)
        # return [' '*(m - d) + s for s, d in zip(snums, dots)]

    if justification == "left":
        sljmethod = str.ljust
    elif justification == "right":
        sljmethod = str.rjust
    elif justification == "center":
        sljmethod = str.center
    else:
        raise Exception("Valid justification arguments are 'left','right' and 'center'")
    if fist_line_justification == "left":
        fljmethod = str.ljust
    elif fist_line_justification == "right":
        fljmethod = str.rjust
    elif fist_line_justification == "center":
        fljmethod = str.center
    else:
        raise Exception("Valid fist_line_justification arguments are 'left','right' and 'center'")
    col_widths = [0] * len(rows_of_columns[0])
    for row in rows_of_columns:
        for idx, col in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(col)))
    ret_str = ''
    for idx,row in enumerate(rows_of_columns):
        jmethod = fljmethod if idx == 0 else sljmethod
        for idx,col in enumerate(row):
            ret_str += "".join(jmethod(str(col), col_widths[idx]))
            ret_str += " " * padding
        ret_str += "\n"
    return ret_str