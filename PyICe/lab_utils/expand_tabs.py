"""Expand tabs utility.

>>> from PyICe.lab_utils.expand_tabs import expand_tabs

"""
def expand_tabs(string, *column_widths, **default_column_width):
    r"""Expand tab-separated fields into fixed-width columns with per-column control.

    Unlike ``str.expandtabs`` (which uses a uniform tab stop), this allows each
    column to have its own width — useful for aligning heterogeneous instrument
    data where fields have very different natural widths.

    >>> expand_tabs('a\tb\tc', 5, 5, 5)
    'a    b    c    '
    >>> expand_tabs('hi\tthere', default_column_width=8)
    'hi      there   '
    >>> expand_tabs('Name\tValue\tUnit', 10, 8, 6)
    'Name      Value   Unit  '
    >>> expand_tabs('x\ty', 2, 2)
    'x y '

    Args:
        string: Single-line string with tab-separated fields.
        *column_widths: Width for each column (positional, one per tab field).
        **default_column_width: Fallback width if not all columns have explicit
            widths. Also accepts ``verbose=True`` to warn about undersized columns.

    Raises:
        Exception: If a column has no explicit width and no default_column_width.
    """
    for key in default_column_width:
        if key != "default_column_width" and key != "verbose":
            raise Exception(
                '"default_column_width" and "verbose" are the only allowed keyword arguments.')
    columns = string.split('\t')
    out_str = ''
    for idx, column in enumerate(columns):
        try:
            column_width = column_widths[idx]
        except IndexError:
            if "default_column_width" in default_column_width:
                column_width = default_column_width["default_column_width"]
            else:
                raise Exception(
                    'Specify width of each column or specify keyword argument "default_column_width"')
        pad = column_width - len(column)
        if pad < 1:
            if default_column_width.get("verbose", None):
                print("Column {} undersize by {}.".format(idx, 1 - pad))
            pad = 1

        space = ' ' * pad
        out_str += column + space
    return out_str
