"""Csv to recarray utility."""
import csv
import numpy
from .str2num import str2num
from .clean_c import clean_c


# , force_float_dtype=False, data_types=None):
def csv_to_recarray(csv_input_file):
    """Load a CSV file into a NumPy record array with float columns.

    Use this function to quickly pull CSV lab-measurement data into NumPy for
    post-processing with SciPy, ``lab_utils.transform``, ``lab_utils.decimate``,
    or any other array-based workflow.  The CSV dialect (delimiter, quoting,
    etc.) is detected automatically via ``csv.Sniffer``, so no manual format
    configuration is required.

    The first row of the file must be a header that provides column names.
    Column names are sanitised with ``clean_c`` so they form valid Python
    identifiers, which enables attribute-style column access (e.g.
    ``arr.vbat``).  All data cells are converted to ``float`` via ``str2num``;
    mixed-type or purely-string columns are not supported.  The file may be
    ASCII or UTF-8 encoded; a UTF-8 BOM on the first column name is stripped
    automatically.

    See also: https://docs.scipy.org/doc/numpy/reference/generated/numpy.recarray.html

    Args:
        csv_input_file: Path to the CSV file to read.  The file must contain
            a header row followed by one or more data rows.  All values must
            be numeric (or convertible to float).

    Returns:
        A ``numpy.recarray`` whose fields correspond to the sanitised CSV
        column names.  Rows are accessible by integer index (e.g. ``arr[2]``)
        and columns by attribute name (e.g. ``arr.vbat``).
    """
    ##########################################################################
    # It's likely this whole thing should be replaced with numpy.genfromtxt, numpy.recfromcsv or numpy.recfromtxt.   #
    # https://docs.scipy.org/doc/numpy-1.10.1/user/basics.io.genfromtxt.html                                         #
    # https://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.genfromtxt.html#numpy.genfromtxt             #
    ##########################################################################
    def process_cell(cell):
        return str2num(str(cell, 'utf-8'), except_on_error=False)

    with open(csv_input_file, 'rb') as csvfile:
        has_header = csv.Sniffer().has_header(csvfile.read(1024))
        csvfile.seek(0)
        # need to add manual dialect control???
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        csvreader = csv.reader(csvfile, dialect)
        if has_header:
            row = next(csvreader)
            # row[0] = row[0].lstrip('\xEF\xBB\xBF') #UTF-8 BOM
            column_names = [process_cell(cell) for cell in row]
            column_names[0] = column_names[0].lstrip('\uFEFF')  # Unicode BOM
        else:
            raise Exception('Data must have header row with column names.')
        data = []
        for row in csvreader:
            row = [process_cell(cell) for cell in row]
            data.append(row)
    # Data type stuff not finished.... Force float instead for now.
    # if force_float_dtype and data_types is None:
        # dtype = numpy.dtype([(column_name,type(float())) for column_name in column_names])
    # elif force_float_dtype and data_types is not None:
        # raise Exception('Specify only one of force_float_dtype, data_types arguments.')
    # elif data_types is None:
        # dtype = numpy.dtype([(column_name,type) for k,v in self.get_column_types().iteritems()])
    # else:
        # dtype = numpy.dtype([(column_name,type(example_contents)) for column_name,example_contents in data_types])
    dtypes = numpy.dtype([(clean_c(column_name).encode('ascii'), type(
        float())) for column_name in column_names])  # unicode numpy support?
    arr = numpy.array(list(map(tuple, data)), dtypes)
    return arr.view(numpy.recarray)
