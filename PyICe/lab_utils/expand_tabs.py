def expand_tabs(string, *column_widths, **default_column_width):
    '''like string.expandtabs, but works only on a single line and allows for varying column widths.
    accepts variable number of positional arguments for each column width.
    accepts keyword argument "default_column_width" if not all column widths are specified.
    accepts keyword argument "verbose" to warn if column width is too narrow for contents.'''
    for key in default_column_width:
        if key != "default_column_width" and key != "verbose":
            raise Exception('"default_column_width" and "verbose" are the only allowed keyword arguments.')
    columns = string.split('\t')
    out_str = ''
    for idx, column in enumerate(columns):
        try:
            column_width = column_widths[idx]
        except IndexError as e:
            if "default_column_width" in default_column_width:
                column_width = default_column_width["default_column_width"]
            else:
                raise Exception('Specify width of each column or specify keyword argument "default_column_width"')
        pad = column_width - len(column)
        if pad < 1:
            if default_column_width.get("verbose", None):
                print("Column {} undersize by {}.".format(idx, 1-pad))
            pad = 1

        space = ' ' * pad
        out_str += column + space
    return out_str