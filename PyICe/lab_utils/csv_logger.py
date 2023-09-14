import datetime, atexit
from .csv_writer import csv_writer

class csv_logger(csv_writer):
    '''set up columns, then pass results dictionary from logger or channel group to write() method.
    Can be used to provide automated test script 'marching waves' with a program such as Live Graph (https://sourceforge.net/projects/live-graph/).
    '''
    def __init__(self, output_file, encoding='utf-8'):
        csv_writer.__init__(self)
        self.output_file = output_file
        self.encoding = encoding
        self.header_written = False
        self.f = open(self.output_file, 'wb')
        atexit.register(self.__del__)
        self._row_id = -1
    def __enter__(self):
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        print("__exit__ closing CSV filehandle: {}".format(self.output_file))
        self.f.close()
        return None
    def __del__(self):
        print("__del__ closing CSV filehandle: {}".format(self.output_file))
        self.f.close()
    def _row_count(self):
        '''private method used by rowid column.'''
        self._row_id += 1
        return self._row_id
    def add_timestamps(self):
        '''add rowid and datetime fields to output'''
        csv_writer.add_column(self,query_name=None,display_name='rowid', query_function=self._row_count)
        csv_writer.add_column(self,query_name=None,display_name='datetime',query_function=datetime.datetime.now,transform=lambda t: datetime.datetime.strftime(t,"%Y-%m-%dT%H:%M:%S.%fZ")) #2015-10-20 21:54:17
    def _add_elapsed_time(self,display_name,format,transform):
        csv_writer.add_column(self,query_name=None,display_name=display_name,format=format,query_function=datetime.datetime.now,transform=lambda t:transform((t-self._time_zero).total_seconds()))
    def add_column(self, channel):
        '''set up output to include channel object as column data source'''
        if self.header_written:
            raise Exception("Can't add column {} after header has been written.".format(channel.get_name()))
        # csv_writer.add_column(self, query_name=channel.get_name(), transform=channel.format_display) #this loses precision!
        csv_writer.add_column(self, query_name=channel.get_name(), transform=None)
    def add_columns(self, channel_list):
        '''set up output to include channel objects in channel_list as column data sources'''
        if self.header_written:
            raise Exception("Can't add columns after header has been written.")
        for channel in channel_list:
            self.add_column(channel)
    def write(self, channel_data):
        '''write selected columns with data supplied in channel_data dictionary'''
        # migrate to csv.DictWriter ?
        # https://docs.python.org/3/library/csv.html
        if not self.header_written:
            self.f.write(self._format_header().encode(self.encoding))
            self._time_zero = datetime.datetime.now() #for elapsed time computation
            self.header_written = True
        row_txt = ''
        for column in self.columns:
            if column.query_function is not None:
                row_txt += self._format_output(None, column)
            elif column.query_name in channel_data:
                row_txt += self._format_output(channel_data[column.query_name], column)
            else:
                #allow missing column data???
                row_txt += ','
                # raise Exception('Data for column: {} not provided to write() method.'.format(column.display_name))
        self.f.write((row_txt[:-1] + '\n').encode(self.encoding))
        # does flushing slow down operation too much? Make optional?
        self.f.flush() #just in case line buffering doesn't work
        return channel_data
    def register_logger_callback(self, logger):
        '''register this csv_logger instance with a lab_core.logger instance for automatic data plotting
        '''
        if not len(self.columns):
            self.add_timestamps()
            self.add_columns(logger)
        logger.add_log_callback(self.write)
    def unregister_logger_callback(self, logger, close_file=True):
        '''clean up in case lab_core.logger will be re-used for a new test.'''
        logger.remove_log_callback(self.write)
        if close_file:
            self.f.close()