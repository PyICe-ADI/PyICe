import csv, numpy
from .str2num import str2num

def csv_to_recarray(csv_input_file): #, force_float_dtype=False, data_types=None):
    '''return NumPy record array containing data from CSV input file.
        CSV data can be ASCII or UTF-8 encoded, but Unicode support inside Numpy is lacking.
        Rows can be accessed by index, ex arr[2].
        Columns can be accessed by column name attribute, ex arr.vbat.
        Use with data filtering, smoothing, compressing, etc matrix operations provided by SciPy and lab_utils.transform, lab_utils.decimate.
        Use automatic column names, but force data type to float with force_float_dtype boolean argument.
        Override automatic column names and data types (first row) by specifying data_type iterable of (column_name,example_contents) for each column matching query order.
        http://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.recarray.html
        '''
     ##################################################################################################################
     # It's likely this whole thing should be replaced with numpy.genfromtxt, numpy.recfromcsv or numpy.recfromtxt.   #
     # https://docs.scipy.org/doc/numpy-1.10.1/user/basics.io.genfromtxt.html                                         #
     # https://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.genfromtxt.html#numpy.genfromtxt             #
     ##################################################################################################################
    def process_cell(cell):
        return str2num(str(cell, 'utf-8'), except_on_error=False)

    with open(csv_input_file, 'rb') as csvfile:
        has_header = csv.Sniffer().has_header(csvfile.read(1024))
        csvfile.seek(0)
        dialect = csv.Sniffer().sniff(csvfile.read(1024)) #need to add manual dialect control???
        csvfile.seek(0)
        csvreader = csv.reader(csvfile, dialect)
        if has_header:
            row = next(csvreader)
            #row[0] = row[0].lstrip('\xEF\xBB\xBF') #UTF-8 BOM
            column_names = [process_cell(cell) for cell in row]
            column_names[0] = column_names[0].lstrip('\uFEFF') #Unicode BOM
        else:
            raise Exception('Data must have header row with column names.')
        data = []
        for row in csvreader:
            row = [process_cell(cell) for cell in row]
            data.append(row)
    #Data type stuff not finished.... Force float instead for now.
    # if force_float_dtype and data_types is None:
        # dtype = numpy.dtype([(column_name,type(float())) for column_name in column_names])
    # elif force_float_dtype and data_types is not None:
        # raise Exception('Specify only one of force_float_dtype, data_types arguments.')
    # elif data_types is None:
        # dtype = numpy.dtype([(column_name,type) for k,v in self.get_column_types().iteritems()])
    # else:
        # dtype = numpy.dtype([(column_name,type(example_contents)) for column_name,example_contents in data_types])
    dtypes = numpy.dtype([(clean_c(column_name).encode('ascii'),type(float())) for column_name in column_names]) #unicode numpy support?
    arr = numpy.array(list(map(tuple,data)), dtypes)
    return arr.view(numpy.recarray)