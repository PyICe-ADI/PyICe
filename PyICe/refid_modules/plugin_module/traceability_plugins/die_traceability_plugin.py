from PyICe.refid_modules.plugin_module.traceability_plugins.traceability_plugin  import traceability_plugin
from PyICe.refid_modules.plugin_module.traceability_plugins                      import die_traceability as dt
from PyICe.lab_core import instrument, channel
import sqlite3

class die_traceability_plugin(traceability_plugin):
    def __init__(self, test_mod):
        self.instrument=None
        self.die_tra = dt
        super().__init__(test_mod)
        self.tm.die_id=None

    def get_atts(self):
        att_dict = {
                   'get_die_id':self.get_die_id,
                    }
        att_dict.update(super().get_atts())
        return att_dict

    def get_hooks(self):
        plugin_dict = super().get_hooks()
        plugin_dict['begin_collect'] = [self._set_die_id_instrument]
        plugin_dict['tm_plot_from_table']= [self._get_die_id_from_table]
        return plugin_dict

    def _set_die_id(self, *args, **kwargs):
        self.tm.die_id=input("What is the unique id of this dut? ")
        
    def get_die_id(self):
        return self.tm.die_id

    def _get_die_id_from_table(self, table_name=None, db_file=None):
        conn = sqlite3.connect(db_file)
        dut = conn.execute(f"SELECT dut_id FROM {table_name}").fetchone()[0]
        return dut

    def _set_die_id_instrument(self):
        '''Sets self.die_id to a unique identifier, provided by the user. Default is a simple query to the user. Can be replaced in a child class.'''
        self._set_die_id()
        self.instrument = instrument(name="dut_id")
        self.instrument._add_channel(channel("dut_id")).write(self.tm.die_id)

    def get_traceability_channels(self):
        return ['dut_id']
