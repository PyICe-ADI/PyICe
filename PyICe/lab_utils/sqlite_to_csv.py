import datetime, sqlite3
from .csv_writer import csv_writer

class sqlite_to_csv(csv_writer):
    '''Formats data stored in an SQLite database so that it can be browsed interactively.
       Use a program like Live Graph (https://sourceforge.net/projects/live-graph/) or KST (kst-plot.kde.org) to visualize data.'''
    def __init__(self, table_name, database_file='data_log.sqlite'):
        '''name is the chart title.
        table_name is the database table containing selected data columns.
        database_file is the sqlite file containing table_name.'''
        csv_writer.__init__(self)
        self.table_name = table_name
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()
    def __enter__(self):
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.conn.close()
        return None
    def add_timestamps(self):
        '''Add rowid and datetime columns to csv output.'''
        self.add_column('rowid')
        self.add_column('datetime')
    def _add_elapsed_time(self,display_name,format,transform):
        self.cursor.execute('SELECT strftime("%s",datetime) FROM {} LIMIT 1'.format(self.table_name))
        self.add_column(query_name='strftime("%s",datetime) - {}'.format(self.cursor.fetchone()[0]),display_name=display_name,format=format,transform=transform)
    def write(self, output_file, append=False, encoding='utf-8'):
        '''write previously selected column data to output_file.'''
        query_txt = ''
        for column in self.columns:
            query_txt += "{},".format(column.query_name)
        query_txt = query_txt[:-1]
        with open(output_file, 'a' if append else 'w') as f:
            f.write(self._format_header().encode(encoding))
            for row in self.cursor.execute('SELECT {} FROM {}'.format(query_txt,self.table_name)):
                row_txt = ''
                for cidx,column in enumerate(row):
                    row_txt += self._format_output(column, self.columns[cidx])
                f.write((row_txt[:-1] + '\n').encode(encoding))
            f.close()
        print('Output written to {}'.format(output_file))