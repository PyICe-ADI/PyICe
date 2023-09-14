import collections

class csv_writer(object):
    '''shared functions for higher level interfaces'''
    def __init__(self):
        self.column_data_t = collections.namedtuple('column_setup',['query_name','display_name','transform','format','query_function'])
        self.no_transform = lambda x: x
        self.columns = []
        self.comments = []
    def _format_header(self):
        header_txt = ''
        for comment in self.comments:
            header_txt += comment + '\n'
        for column in self.columns:
            header_txt += "{},".format(column.display_name)
        return header_txt[:-1] + '\n'
    def _format_output(self, data, column_setup_tuple):
        '''give just one element of a data row'''
        if column_setup_tuple.query_function is not None:
            data = column_setup_tuple.query_function()
        data = column_setup_tuple.transform(data)
        # stringify data
        data = '{}'.format(column_setup_tuple.format).format(data)
        # escape rules:
        if '"' in data:
            # doubled double quotes escape all double quotes
            data = data.replace('"', '""')
        if ',' in data:
            # double quotes enclose all fields containing commas
            data = '"{}"'.format(data)
        return '{},'.format(data)
    def add_comment(self, comment_str, comment_character='#'):
        '''add comment line(s) to the top of the output file.
        Live Graph treats '@' as a 'description line' and '#' as a 'comment line'.
        Neither has any effect on the data interpretation.'''
        self.comments.append('{}{}'.format(comment_character,comment_str))
    def add_elapsed_seconds(self,display_name='elapsed_seconds', format=''):
        '''computes elapsed seconds since first row of table'''
        self._add_elapsed_time(display_name=display_name,format=format,transform=self.no_transform)
    def add_elapsed_minutes(self,display_name='elapsed_minutes', format=''):
        '''computes elapsed minutes since first row of table'''
        self._add_elapsed_time(display_name=display_name,format=format,transform=lambda x: x/60.0)
    def add_elapsed_hours(self,display_name='elapsed_hours', format=''):
        '''computes elapsed hours since first row of table'''
        self._add_elapsed_time(display_name=display_name,format=format,transform=lambda x: x/3600.0)
    def add_elapsed_days(self,display_name='elapsed_days', format=''):
        '''computes elapsed days since first row of table'''
        self._add_elapsed_time(display_name=display_name,format=format,transform=lambda x: x/86400.0)
    def _add_elapsed_time(self, *args, **kwargs):
        raise NotImplementedError('Elapsed time not implemented')
    def add_column(self, query_name, display_name=None, format='',transform=None,query_function=None):
        '''add single column to output file.
        provides more customization options than addign a list of columns
        transform is a python function applied to the query results before formatting
        format is a format string to alter the column data.  Ex: 3.2f.
        query function is a function that returns data directly from Python rather than from external data source. Ex: time
        '''
        if display_name is None:
            display_name = query_name
        format = format = '{{:{}}}'.format(format)
        if transform is None:
            transform = self.no_transform
        self.columns.append(self.column_data_t(display_name=display_name,query_name=query_name,transform=transform,format=format,query_function=query_function))
    def add_columns(self, column_list, format=''):
        '''Shortcut method to add multiple data columns at once.
        column_list selects additional data columns to output.
        format is a format string to alter the column data.  Ex: 3.2f.
        For more flexibility, add columns individually using add_column() method.'''
        for column in column_list:
            self.add_column(column, format=format)