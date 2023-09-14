import datetime, sqlite3, re, ast, numpy, pandas, collections
from .time_zones import UTC
from .str2num import str2num

class sqlite_data(collections.abc.Sequence): #collections.Iterable to disable slicing?
    '''Produce iterable object returning row sequence, where each column within each row is accessible by either column name or position.
    table_name can be an expression returning a synthetic non-table relation.
    '''
    def __init__(self, table_name=None, database_file='data_log.sqlite', timezone=None):
        if timezone is None:
            self.timezone = UTC()
        else:
            self.timezone = timezone
        sqlite3.register_converter("DATETIME", self.convert_timestring)
        sqlite3.register_converter("NUMERIC", self.convert_vector)
        sqlite3.register_converter("PyICeDict", self.convert_vector) #TODO
        sqlite3.register_converter("PyICeTuple", self.convert_vector) #TODO
        sqlite3.register_converter("PyICeList", self.convert_vector) #TODO
        sqlite3.register_converter("PyICeBLOB", self.convert_ndarray)
        sqlite3.register_converter("PyICeFloatList", lambda d: numpy.fromstring(d[1:-1], sep=',', dtype=numpy.dtype('<d')))
        sqlite3.register_converter("PyICeIntList", lambda d: numpy.fromstring(d[1:-1], sep=',', dtype=numpy.dtype('int')))
        self.conn = sqlite3.connect(database_file, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) #automatically convert datetime column to Python datetime object
        self.conn.row_factory = sqlite3.Row #index row data tuple by column name
        self.set_table(table_name)
        self.sql_query = None
        self.params = []
        if table_name is not None:
            self.sql_query = "SELECT * from {}".format(table_name) #remove rowid because it's now an explicitly stored column from the logger
    def set_table(self, table_name):
        self.table_name = table_name
    def convert_timestring(self, time_bytes):
        time_string = time_bytes.decode('ascii')
        return datetime.datetime.strptime(time_string,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=UTC()).astimezone(self.timezone)
    @classmethod
    def convert_vector(cls, col_data_bytes):
        col_data_str = col_data_bytes.decode('utf-8')
        if re.match(r'^\[.*\]$', col_data_str):
            return ast.literal_eval(col_data_str) # This is slow!
        elif re.match(r'^\{.*\}$', col_data_str):
            return ast.literal_eval(col_data_str)
        elif re.match(r'^\(.*\)$', col_data_str):
            return ast.literal_eval(col_data_str)
        else:
            return str2num(col_data_str, except_on_error=False)
    def convert_ndarray(self, col_data_bytes):
        #Expect flat (1d) array of homogeneous dtype
        fmt_str_size = col_data_bytes[0] # uint8; support up to 255 format string characters to follow
        fmt_str = col_data_bytes[1:fmt_str_size+1] # ascii dtype format string, ex "<d" little endian double precision float 64.
        return numpy.frombuffer(col_data_bytes, offset=1+fmt_str_size, dtype=numpy.dtype(fmt_str))
    def __getitem__(self,key):
        '''implement sequence behavior.'''
        subs = {}
        if isinstance(key, slice):
            if key.start is None:
                subs['start'] = 0
            else:
                subs['start'] = key.start
            if key.stop is None:
                subs['limit'] = -1 #no limit
            else:
                if subs['start'] >= key.stop:
                    raise Exception('Reverse iteration not supported.')
                subs['limit'] = key.stop - subs['start']
            if key.step is not None:
                raise Exception('Slice step not supported.')
            fetch = sqlite3.Cursor.fetchall
        else:
            subs['start'] = key
            subs['limit'] = 1
            fetch = sqlite3.Cursor.fetchone
        return fetch(self.conn.execute(self.sql_query + " LIMIT {limit} OFFSET {start};".format(**subs), self.params))
    def __iter__(self):
        '''implement iterable behavior.'''
        return self.conn.execute(self.sql_query, self.params)
    def __len__(self):
        '''return number of rows returned by SQL query.
        WARNING: Inefficient.
        '''
        #this is hard because the iterable doesn't actually know its length
        #self.cursor.rowcount doesn't work; returns -1 when database isn't modified.
        #not very efficient for big dataset!
        return len(self.conn.execute(self.sql_query, self.params).fetchall())
    def __enter__(self):
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.conn.close()
    def get_table_names(self, include_views=True):
        view_where = "OR type == 'view'" if include_views else ''
        tables = self.conn.execute(f"SELECT name FROM sqlite_master WHERE type == 'table'{view_where}").fetchall()
        if tables is None:
            return []
        else:
            return [r[0] for r in tables]
    def get_column_names(self):
        '''return tuple of column names.
        Column names can be used for future queries or used to select column from query row results.
        '''
        if self.sql_query is None:
            raise Exception('table_name not specified')
        first_row = self.conn.execute(self.sql_query, self.params).fetchone()
        if first_row is None:
            return None
        return list(first_row.keys())
    def get_column_types(self):
        '''Return dictionary of data types stored in each column.
        Note that SQLite does not enforce types within a column, nor does the PyICe logger.
        The types of data stored in the first row will be returned, which may not match data stored elsewhere in the relation.
        Used by numpy array conversion to define data stride.
        '''
        cursor = self.conn.execute(self.sql_query, self.params).fetchone()
        return collections.OrderedDict([(k,type(cursor[k])) for k in list(cursor.keys())])
    def get_distinct(self, column_name, table_name=None, where_clause=None, force_tuple=False):
        '''return one copy of each value (set) in specified column
        table_name can be an expression returning a synthetic non-table relation.
        '''
        if isinstance(column_name, (list, tuple)):
            column_names = ', '.join(column_name)
            column_count = len(column_name)
            column_list = list(column_name)
        else:
            column_names = column_name
            column_count = 1
            column_list = [column_name]
        nt_type = collections.namedtuple('distincts',column_list)
        if table_name is None:
            table_name = self.table_name
            if table_name is None:
                raise Exception('table_name not specified')
        if where_clause is None:
            where_clause = ""
        data = self.conn.execute(f"SELECT DISTINCT {column_names} from {table_name} {where_clause};").fetchall()
        if column_count > 1 or force_tuple:
            try:
                distincts = sorted(nt_type._make(row) for row in data)
            except TypeError:
                distincts = (nt_type._make(row) for row in data)
            ## Sorted will sort distincts by the first distinct column name requested, then by the 2nd column name, and so on. e.g  get_distinct((x,y)) will sort by x then by y
        else:
            try:
                distincts = sorted(row[0] for row in data)
            except TypeError:
                distincts = (row[0] for row in data)
        return tuple(distincts)
    def query(self, sql_query, *params):
        '''return iterable with query results.
        columns within each row can be accessed by column name or by position
        '''
        self.sql_query = sql_query
        self.params = params
        return self.conn.execute(self.sql_query, self.params)
    def zip(self):
        '''return query data transposed into column_list of row_lists.'''
        return list(zip(*self))
    def csv(self, output_file, elapsed_time_columns=False, append=False, encoding='utf-8'):
        '''write data to CSV output_file.
        set output_file to None to just return CSV string.'''
        # migrate to csv.DictWriter ?
        # https://docs.python.org/3/library/csv.html
        output_txt = ""
        datetime_col = None
        for pos,column in enumerate(self.get_column_names()):
                output_txt += '{},'.format(column)
                if elapsed_time_columns and column == 'datetime':
                    output_txt += 'elapsed_time,'
                    output_txt += 'elapsed_seconds,'
                    datetime_col = pos
        output_txt = '{}\n'.format(output_txt[:-1])
        start_time = None
        for row in self:
            for pos,column in enumerate(row):
                # stringify data
                esc_data = str(column)
                # escape rules:
                if '"' in esc_data:
                    # doubled double quotes escape all double quotes
                    esc_data = esc_data.replace('"', '""')
                if ',' in esc_data:
                    # double quotes enclose all fields containing commas
                    esc_data = '"{}"'.format(esc_data)
                output_txt += '{},'.format(esc_data)
                if start_time is None and pos == datetime_col:
                    start_time = column
                if elapsed_time_columns and pos == datetime_col:
                    output_txt += '{},'.format(column - start_time) #elapsed_time
                    output_txt += '{},'.format((column-start_time).total_seconds()) #elapsed_seconds
            output_txt = '{}\n'.format(output_txt[:-1])
        if output_file is not None:
            with open(output_file, 'a' if append else 'w') as f:
                f.write(output_txt.encode(encoding))
                f.close()
            print('Output written to {}'.format(output_file))
        return output_txt
    def xlsx(self, output_file, elapsed_time_columns=False):
        '''write data to excel output_file.'''
        with sqlite_to_xlsx(output_file) as writer:
            writer.add_worksheet(self, elapsed_time_columns)
            writer.close()
    def to_list(self):
        '''return copy of data in list object'''
        return [row for row in self]
    def numpy_recarray(self, force_float_dtype=False, data_types=None):
        '''return NumPy record array containing data.
        Rows can be accessed by index, ex arr[2].
        Columns can be accessed by column name attribute, ex arr.vbat.
        Use with data filtering, smoothing, compressing, etc matrix operations provided by SciPy and lab_utils.transform, lab_utils.decimate.
        Use automatic column names, but force data type to float with force_float_dtype boolean argument.
        Override automatic column names and data types (first row) by specifying data_type iterable of (column_name,example_contents) for each column matching query order.
        http://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.recarray.html
        '''
        if force_float_dtype and data_types is None:
            dtype = numpy.dtype([(key,type(float())) for key in self.get_column_types()])
        elif force_float_dtype and data_types is not None:
            raise Exception('Specify only one of force_float_dtype, data_types arguments.')
        elif data_types is None:
            dtype = numpy.dtype([(k,v) for k,v in self.get_column_types().items()])
        else:
            dtype = numpy.dtype([(column_name,type(example_contents)) for column_name,example_contents in data_types])
        arr = numpy.array([tuple(row) for row in self], dtype)
        return arr.view(numpy.recarray)
    def pandas_dataframe(self):
        '''return Pandas dataframe based on stored sql_query'''
        return pandas.read_sql_query(self.sql_query,
                                     self.conn,
                                     params=self.params,
                                     # index_col='rowid',
                                     # parse_dates={'datetime': '%Y-%m-%dT%H:%M:%S.%fZ'}) #date parsing not necessary with SQLite3 registered converter
                                    )
    def column_query(self, column_list):
        '''return partial query string separating column names with comma characters.'''
        str = ''
        for column in column_list:
            str += '{},'.format(column)
        return str[:-1]
    def time_delta_query(self, time_div=1, column_name=None):
        '''return partial query string which will compute fractional delta seconds from first entry in the table as a column.
        Feed back into query to get elapsed time column.
        Ex "SELECT rowid, {}, * FROM ...".format(sqlite_data_obj.time_delta_query())
        Use time_div to convert from second to your choice of time scales, example: time_div=3600 would be hours.
        '''
        if column_name is None:
            if time_div == 0.001:
                column_name = "elapsed_milliseconds"
            elif time_div == 1:
                column_name = "elapsed_seconds"
            elif time_div == 60:
                column_name = "elapsed_minutes"
            elif time_div == 3600:
                column_name = "elapsed_hours"
            elif time_div == 86400:
                column_name = "elapsed_days"
            elif time_div == 31536000:
                column_name = "elapsed_years"
            else:
                column_name = "elapsed_time"
        frac_s_str = "strftime('%s',datetime)+strftime('%f',datetime)-strftime('%S',datetime)"
        if self.table_name is None:
                raise Exception('table_name not specified')
        first_time = self.conn.execute("SELECT {} FROM {} ORDER BY rowid ASC;".format(frac_s_str,self.table_name)).fetchone()[0]
        return "({}-{})/{} AS {}".format(frac_s_str,first_time,time_div,column_name)
    def filter_change(self, column_name_list, table_name=None, first_row=False, preceding_row=False):
        '''return tuple of rowid values where any column in column_name_list changed value.
        result tuple can be fed into a new query("SELECT ... WHERE rowid in {}".format(sqlite_data_obj.filter_change())).
        it table_name is omitted, instance default will be used.
        setting preceding_row to True will also return the rowid before the change occurred.
        '''
        if table_name is None:
            table_name = self.table_name
            if table_name is None:
                raise Exception('table_name not specified')
        if first_row:
            first_row = (1,)
        else:
            first_row = tuple()
        sql_query = 'SELECT delay.rowid from {table_name} as orig JOIN {table_name} as delay ON orig.rowid = delay.rowid-1 WHERE '.format(table_name=table_name)
        for column_name in column_name_list:
            sql_query += 'orig.{column_name} IS NOT delay.{column_name} OR '.format(column_name=column_name)
        sql_query = sql_query[:-4]
        try:
            row_ids = list(zip(*self.conn.execute(sql_query)))[0]
        except IndexError as e:
            #no changes
            return first_row
        if preceding_row:
            preceding_row_ids = tuple(row -1 for row in row_ids)
            return tuple(sorted(first_row + row_ids + preceding_row_ids))
        return tuple(sorted(first_row + row_ids))
    def optimize(self):
        '''Defragment database file, reducing file size and speeding future queries.
        Also re-runs query plan optimizer to speed future queries.
        WARNING: May take a lot time to complete when operating on a large database.
        WARNING: May re-order rowid's
        '''
        self.conn.execute("VACUUM;")
        self.conn.execute("ANALYZE;")
    def expand_vector_data(self, csv_filename=None, csv_append=False, csv_encoding='utf-8'):
        '''Expand vector list data (from oscilloscope, network analyzer, etc) to full row-rank.
        Scalar data will be expanded to vector length.
        Returns numpy record array.
        Optionally write output to comma separated file if csv_filname argument is specified.
        '''
        columns = []
        dtypes = []
        data_length = None
        column_names = self.get_column_names()
        for column in column_names:
            columns.append([])
            for i,row in enumerate(self):
                try:
                    if row[column].startswith('[') and row[column].endswith(']'):
                        column_data = [float(x) for x in row[column].strip("[]").split(",")]
                        if data_length is None and len(column_data) > 1:
                            data_length = len(column_data)
                        elif len(column_data) != 1 and len(column_data) != data_length:
                            raise Exception('Inconsistent data length in vector expansion: {} and {}'.format(len(columns[-1]),data_length))
                    else:
                        column_data = [row[column]]
                except AttributeError:
                    column_data = [row[column]]
                columns[-1].append(column_data)
        if data_length is None:
            print("WARNING: No vector data found.")
            data_length = 1
        for i,column in enumerate(columns):
            if len(column[0]) == 1:
                dtypes.append((column_names[i], type(column[0][0])))
            else:
                dtypes.append((column_names[i], float))
            for rowcount,rowcoldata in enumerate(column):
                if len(rowcoldata) == 1:
                    #expand scalar data to vector length
                    column[rowcount] = rowcoldata * data_length
        #flatten row data
        data = []
        for rowid in range(rowcount+1):
            rowdata = []
            for columnid in range(i+1):
                rowdata.append(columns[columnid][rowid])
            data.extend(list(zip(*rowdata)))
        #csv output
        if csv_filename is not None:
            csv_txt = ""
            for column in column_names:
                    csv_txt += '{},'.format(column)
            csv_txt = '{}\n'.format(csv_txt[:-1])
            for row in data:
                for column in row:
                    csv_txt += '{},'.format(column)
                csv_txt = '{}\n'.format(csv_txt[:-1])
            with open(csv_filename, 'a' if csv_append else 'w') as f:
                f.write(csv_txt.encode(csv_encoding))
                f.close()
            print('Output written to {}'.format(csv_filename))
        array = numpy.array(data, dtype=dtypes)
        return array.view(numpy.recarray)
