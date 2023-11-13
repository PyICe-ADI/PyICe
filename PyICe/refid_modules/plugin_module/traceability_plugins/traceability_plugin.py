from PyICe.refid_modules.plugin_module.plugin import plugin
from PyICe.refid_modules.plugin_module.plugin_data_repo import plugin_data_repo as pdr
from types import MappingProxyType
import abc, sqlite3,collections

class byte_ord_dict(collections.OrderedDict):
    '''Ordered dictionary for channel results reporting with pretty print addition.'''
    def __str__(self):
        s = ''
        max_channel_name_length = 0
        for k,v in self.items():
            max_channel_name_length = max(max_channel_name_length, len(k))
            # s += f'{k}:\t{v[0]:02X}\n'
            s += f'{k}:\t{v:02X}\n'
        s = s.expandtabs(max_channel_name_length+2).replace(' ','.')
        return s

class traceability_plugin(plugin):
    desc = "Adds traceability channels to the bench master and keeps the channel names on hand."
    def __init__(self, test_mod):
        super().__init__(test_mod)
        if not hasattr(self.tm, 'plugin_data_repo'):
            self.tm.plugin_data_repo = pdr()
        self.tm._need_to_add_to_repo = True

    def __str__(self):
        return 'Hi.'

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                        'read_traceability_sqlite':self.read_traceability_sqlite,
                        'get_all_traceability_channels':self.get_all_traceability_channels,
                        })

    def get_atts(self):
        return self.att_dict

    def get_hooks(self):
        plugin_dict={
                    'tm_logger_setup':[self._add_to_bench],
                    'tm_plot_from_table':[self.read_traceability_sqlite]
                    }
        return plugin_dict

    def set_interplugs(self):
        pass

    def _add_to_bench(self, logger):
        logger.add(self.instrument)

    @abc.abstractmethod
    def get_traceability_channels(self):
        '''Returns a list of the channel names that will be added to the json report.'''
        pass

    def get_all_traceability_channels(self):
        traceability_channels=[]
        for plugin in self.tm.plugins.keys():
            if hasattr(self.tm.plugins[plugin]['instance'],'get_traceability_channels'):
                traceability_channels.extend(self.tm.plugins[plugin]['instance'].get_traceability_channels())
        return traceability_channels

    def read_traceability_sqlite(self, db_table, db_file):
        '''pull relevant traceability data from first row of sqlite database file/table'''
        if not hasattr(self.tm.plugin_data_repo, 'traceability_results'):
            conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) #automatically convert datetime column to Python datetime object
            conn.row_factory = sqlite3.Row #index row data tuple by column name
            traceability_channel_list = self.get_all_traceability_channels()
            if not traceability_channel_list:
                return []
            traceability_channel_list.append('datetime')
            column_query_str = ', '.join(traceability_channel_list)
            row = conn.execute(f"SELECT {column_query_str} FROM {db_table}").fetchone()
            if row is None:
                raise EmptyTableError()
            results = byte_ord_dict()
            for k in row.keys():
                results[k] = row[k]
                if results[k] is None:
                    raise InvalidDataError()
            self.tm.plugin_data_repo.add_to_repo('traceability_results', results)
            return results
        else:
            return self.tm.plugin_data_repo.traceability_results
