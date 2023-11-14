from PyICe.refid_modules.plugin_module.traceability_plugins.traceability_plugin              import traceability_plugin
from PyICe.refid_modules.bench_identifier              import get_bench_module
from PyICe.lab_core import instrument, channel
import inspect
import os
import sqlite3

class bench_traceability_plugin(traceability_plugin):
    def __init__(self, test_mod, include_bench_file=True, include_operator=True, include_instruments=True):
        self.include_bench_file = include_bench_file
        self.include_operator   = include_operator
        self.include_instruments = include_instruments
        self.traceability_channel_names = []
        if self.include_bench_file:
            self.traceability_channel_names.append('bench')
        if self.include_operator:
            self.traceability_channel_names.append('bench_operator')
        if self.include_instruments:
            self.traceability_channel_names.append('bench_instruments')
        super().__init__(test_mod)

    def get_hooks(self):
        plugin_dict = super().get_hooks()
        plugin_dict['tm_logger_setup'].insert(0,self._set_bench_info_instrument)
        plugin_dict['tm_plot_from_table'].insert(0, self._report_bench_used)
        plugin_dict['post_collect']=[self._report_bench_used]
        return plugin_dict

    def _set_bench_info_instrument(self, logger, *args, **kwargs):
        self.instrument = instrument(name='bench_info')
        ch_cat = 'traceability_info'
        if self.include_bench_file:
            self.instrument._add_channel(channel('bench')).write(get_bench_module(self.tm.project_folder_name).__name__)
            self.instrument['bench'].set_category(ch_cat)
            self.instrument['bench'].set_write_access(False)
        if self.include_operator:
            self.instrument._add_channel(channel('bench_operator')).write(os.getlogin())
            self.instrument['bench_operator'].set_category(ch_cat)
            self.instrument['bench_operator'].set_write_access(False)
        if self.include_instruments:
            self.instrument._add_channel(channel('bench_instruments')).write(self.get_ch_group_info(self.tm.get_lab_bench().get_master()))
            self.instrument['bench_instruments'].set_category(ch_cat)
            self.instrument['bench_instruments'].set_write_access(False)

    def get_ch_group_info(self, ch_group, ident_level=0):
        ret_str = ''
        tabs = '\t' * ident_level
        try:
            idn = ch_group.identify()
        except AttributeError:
            idn = "No Information Available."
        ret_str = f'{tabs}{ch_group.get_name()}:  {idn}\n'
        for ch_subgrp in ch_group.get_channel_groups():
            ret_str += self.get_ch_group_info(ch_subgrp, ident_level+1)
        return ret_str

    def _report_bench_used(self, db_table=None, db_file=None, *args, **kwargs):
        if db_table is None:
            db_table = self.tm.get_db_table_name()
        if db_file is None:
            db_file=self.tm._db_file
        conn = sqlite3.connect(db_file)
        bench = conn.execute(f"SELECT bench FROM {db_table}").fetchone()[0]
        print(f'\nTested on {bench[bench.index("benches")+8:]}\n')

    def get_traceability_channels(self):
        traceability_channel_names=[]
        if self.include_bench_file:
            traceability_channel_names.append('bench')
        if self.include_operator:
            traceability_channel_names.append('bench_operator')
        if self.include_instruments:
            traceability_channel_names.append('bench_instruments')
        return traceability_channel_names