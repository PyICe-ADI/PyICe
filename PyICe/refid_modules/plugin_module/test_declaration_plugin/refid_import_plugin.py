from PyICe.refid_modules.plugin_module.test_declaration_plugin.limit_test_declaration_plugin import limit_test_declaration
from PyICe.refid_modules.test_results           import correlation_results
import importlib, math, os, sqlite3

def isnan(value):
    try:
        return math.isnan(float(value))
    except (TypeError,ValueError):
        return False

class refid_import_plugin(limit_test_declaration):
    def __init__(self, test_mod):
        super().__init__(test_mod)
        self.reg_inputs={}
        self.tm.interplugs['register_correlation_test__test_from_table']=[]
        self.tm.interplugs['register_correlation_test_get_correlation_data']=[]
        self._one_result_print = True

    def get_atts(self):
        att_dict = {
                   'register_test_abs':self.register_test_abs,
                   'get_correlation_declarations':self.get_correlation_declarations,
                   'register_correlation_test':self.register_correlation_test,
                   'register_correlation_result':self.register_correlation_result,
                   'register_correlation_failure':self.register_correlation_failure,
                   'get_correlation_data_scalar':self.get_correlation_data_scalar,
                   'get_correlation_data':self.get_correlation_data,
                   'reg_ate_result':self.reg_ate_result,
                   'display_correlation_results':self.display_correlation_results,
                   'register_test_get_pass_fail':self.register_test_get_pass_fail,
                   'register_test_run_repeatability_results':self.register_test_run_repeatability_results,
                   'register_test_set_tm':self.register_test_set_tm,
                   'register_test__test_from_table_2':self.register_test__test_from_table_2,
                   'set_corr_traceability':self.set_corr_traceability,
                    }
        att_dict.update(super().get_atts())
        return att_dict

    def get_hooks(self):
        plugin_dict = super().get_hooks()
        plugin_dict['pre_collect'].insert(0,self.import_refids)
        plugin_dict['tm_plot_from_table'].insert(0,self.import_refids)
        plugin_dict['tm_set'] = [self._set_refids_once]
        return plugin_dict

    def set_interplugs(self):
        self.tm.interplugs['register_test__compile_test_results'].extend([self.reg_ate_result])
        self.tm.interplugs['register_test_tt_compile_test_results_2'].extend([self.display_correlation_results])
        self.tm.interplugs['register_test_get_pass_fail'].extend([self.register_test_get_pass_fail])
        self.tm.interplugs['register_test_run_repeatability_results'].extend([self.register_test_run_repeatability_results])
        self.tm.interplugs['register_test_set_tm'].extend([self.register_test_set_tm])
        self.tm.interplugs['register_test__test_from_table'].extend([self.set_table_name, self.set_db_filepath])
        self.tm.interplugs['register_test__test_from_table_2'].extend([self.display_correlation_results,self.register_test__test_from_table_2])
        try:
            self.tm.interplugs['die_traceability_set_traceability'].extend([self.set_corr_traceability])
        except Exception:
            pass # This feature requires the die_traceability_plugin to be imported in the test_module.')

    def _set_refids_once(self, *args):
        self.tm.tt._need_to_get_refids=True

    def get_refids(self):
        '''Return a panda database containing the names and details of the project's refids.'''
        pass

    def import_refids(self, *args):
        if not self.tm.tt:
            self.tm.REFIDs = self.get_refids()
            return
        elif self.tm.tt._need_to_get_refids:
            self.tm.tt.refids = self.get_refids()
            self.tm.tt._need_to_get_refids = False
        self.tm.REFIDs = self.tm.tt.refids

    def get_reg_inputs(self, name):
        return self.reg_inputs[name]

    def register_test_abs(self, name):
        '''Pull test limits directly from REFID document automagically.'''
        if not hasattr(self.tm, 'REFIDs'):
            self.import_refids()
        self._set_reg_inputs(name)
        self._register_test(**self.get_reg_inputs(name))
    def register_correlation_test(self, name):
        """With any luck, this should be redundant sometime soon, and we will just be able to 'register_test_ab' for everything imported."""
        if not hasattr(self.tm, 'REFIDs'):
            self.import_refids()
        self._set_reg_inputs(name)
        self.tm._correlation_results._register_correlation_test(**self.get_reg_inputs(name))

    def get_correlation_declarations(self):
        return self._correlation_results.get_correlation_declarations()
    
    def register_correlation_result(self, name, data_temp_pairs, conditions=None):
        '''register correlation results against corr REFIDs. Each data point must also contain a temperature setpoint for matching to ATE data.'''
        self.tm._correlation_results._register_correlation_result(refid_name=name, iter_data=data_temp_pairs, conditions=conditions)

    def register_correlation_failure(self, name, reason, temperature, conditions=None):
        '''mark test failed, without submitting test data'''
        self.tm._correlation_results._register_correlation_failure(name, reason, temperature, conditions)

    def get_correlation_data(self, REFID, *args, **kwargs):
        self.execute_interplugs('register_correlation_test_get_correlation_data', REFID, *args, **kwargs)
        return self.get_correlation_data(REFID, *args, **kwargs)

    def get_correlation_data_scalar(self, REFID, *args, **kwargs):
        return self.get_correlation_data_scalar(REFID, *args, **kwargs)

    def reg_ate_result(self):
        for test in self.tm.get_test_declarations():
            c_d = self.tm.get_correlation_data(test)
            for ate_record in c_d:
                self.tm._test_results._register_ate_result(name=test, result=ate_record['ate_data'], temperature=ate_record['tdegc'])

    def set_corr_traceability(self,test=None):
        self.tm._correlation_results._set_traceability_info(**self.tm._get_traceability_info(table_name=None, db_file=None))

    def register_test_get_test_limits(self, test_name):
        return self.tm._correlation_results._correlation_declarations[test_name]

    def register_test_get_pass_fail(self):
        return bool(self.tm._correlation_results)

    def register_test_run_repeatability_results(self, test_run):
        for corr_name in test_run._correlation_results:
            try:
                # TODO shared results dict???
                results[corr_name].append(test_run._correlation_results[corr_name])
            except KeyError as e:
                results[corr_name] = []
                results[corr_name].append(test_run._correlation_results[corr_name])
            # TODO THEN WHAT with CORR??
    def register_test__test_from_table_2(self, table_name, db_file):
        if db_file==None:
            db_file=self._db_file
        c_r = self.tm._correlation_results.json_report()
        dest_abs_filepath = os.path.join(os.path.dirname(db_file),f"correlation_results.json")
        try:
            if c_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(c_r.encode('utf-8'))
                    f.close()
        except PermissionError as e:
            print(f'ERROR: Unable to write {dest_abs_filepath}')
    def display_correlation_results(self, table_name, db_file=None):
        if len(self.tm._correlation_results):
            if self._one_result_print:
                res_str = f'{self.tm._correlation_results}'
                passes = self.tm._correlation_results
                res_str += f'*** Module {self.tm.get_name()} Correlation Summary {"PASS" if passes else "FAIL"}. ***\n\n'
                print(res_str)
                self._one_result_print = False
    def register_test_set_tm(self,test_module, *args, **kwargs):
        self.tm._correlation_results = correlation_results(self.tm.get_name(), module=self.tm)
    def set_table_name(self, table_name, *args,**kwargs):
        self.tm._correlation_results.set_table_name(table_name)
    def set_db_filepath(self, db_file, *args, **kwargs):
        self.tm._correlation_results.set_db_filepath(os.path.abspath(db_file))
