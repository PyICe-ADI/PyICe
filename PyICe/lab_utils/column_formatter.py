"""Column formatter utility."""
def column_formatter(rows_of_columns, padding=3,
                     justification="left", fist_line_justification="center"):
    """Format tabular data into aligned fixed-width columns.

    Typically used to display measurement logs or register dumps where each row
    has the same number of fields but field widths vary. The first row is treated
    as a header (centered by default) while subsequent rows use left-justification.

    >>> data = [['Name', 'Value', 'Unit'],
    ...         ['Vout', '3.30', 'V'],
    ...         ['Idd', '12.5', 'mA']]
    >>> print(column_formatter(data, padding=2))
    Name   Value   Unit
    Vout   3.30    V
    Idd    12.5    mA
    <BLANKLINE>

    >>> print(column_formatter(data, padding=2, justification="right"))
    Name   Value   Unit
    Vout    3.30      V
     Idd    12.5     mA
    <BLANKLINE>

    >>> column_formatter([['A']], padding=0)
    'A\\n'

    Args:
        rows_of_columns: List of rows, each row a list of column values.
            All rows must have the same number of columns.
        padding: Number of spaces between columns.
        justification: Alignment for data rows — 'left', 'right', or 'center'.
        fist_line_justification: Alignment for the first (header) row.

    Raises:
        Exception: If justification is not 'left', 'right', or 'center'.
    """
    # TODO: decimal alignment. Need to know decimal position apriori.
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
        raise Exception(
            "Valid justification arguments are 'left','right' and 'center'")
    if fist_line_justification == "left":
        fljmethod = str.ljust
    elif fist_line_justification == "right":
        fljmethod = str.rjust
    elif fist_line_justification == "center":
        fljmethod = str.center
    else:
        raise Exception(
            "Valid fist_line_justification arguments are 'left','right' and 'center'")
    col_widths = [0] * len(rows_of_columns[0])
    for row in rows_of_columns:
        for idx, col in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(col)))
    ret_str = ''
    for idx, row in enumerate(rows_of_columns):
        jmethod = fljmethod if idx == 0 else sljmethod
        for idx, col in enumerate(row):
            ret_str += "".join(jmethod(str(col), col_widths[idx]))
            ret_str += " " * padding
        ret_str += "\n"
    return ret_str
