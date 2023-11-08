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
                   'get_corr_pass_fail':self.get_corr_pass_fail,
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
        pass

    def _set_refids_once(self, *args):
        self.tm.tt._need_to_get_refids=True

    def get_refids(self):
        '''Return a dictionary containing details of the project's refids with the names being the keys.'''
        raise AttributeError("This method needs to be overwritten in the project specific child class of this plugin and return a dictionary containing details of the project's refids with the names being the keys.")

    def import_refids(self, *args):
        if not self.tm.tt:
            self.REFIDs = self.get_refids()
            return
        elif self.tm.tt._need_to_get_refids:
            self.tm.tt.refids = self.get_refids()
            self.tm.tt._need_to_get_refids = False
        self.REFIDs = self.tm.tt.refids

    def _set_reg_inputs(self, name):
        if name not in self.REFIDs.keys():
            raise Exception(f'ERROR: Test {name} registered from {test_module.get_name()} not found in REFID master spec.')
        if not all([att in self.REFIDs[name].keys() for att in ['name','upper_limit','lower_limit']]):
            raise Exception(f'The refid {name} needs at least a name, an upper limit, and a lower limit assigned to them in the dataFrame returned by the refid_import_plugin.')
        self.reg_inputs[name]={x:self.REFIDs[name][x] for x in self.REFIDs[name].keys()}
        self.reg_inputs[name]['name']=name

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
        return self.tm._correlation_results.get_correlation_declarations()
    
    def register_correlation_result(self, name, data_temp_pairs, conditions=None):
        '''register correlation results against corr REFIDs. Each data point must also contain a temperature setpoint for matching to ATE data.'''
        self.tm._correlation_results._register_correlation_result(refid_name=name, iter_data=data_temp_pairs, conditions=conditions)

    def register_correlation_failure(self, name, reason, temperature, conditions=None):
        '''mark test failed, without submitting test data'''
        self.tm._correlation_results._register_correlation_failure(name, reason, temperature, conditions)

    def get_correlation_data(self, REFID, *args, **kwargs):
        '''
        The collection of correlation data is very project specific, but not absolutely needed in every project, so abstract method seems overly demanding.
        '''
        # self.execute_interplugs('register_correlation_test_get_correlation_data', REFID, *args, **kwargs)
        return self.get_correlation_data(REFID, *args, **kwargs)

    def get_correlation_data_scalar(self, REFID, *args, **kwargs):
        return self.get_correlation_data_scalar(REFID, *args, **kwargs)

    def reg_ate_result(self):
        for test in self.tm.get_test_declarations():
            c_d = self.tm.get_correlation_data(test)
            for ate_record in c_d:
                self.tm._test_results._register_ate_result(name=test, result=ate_record['ate_data'], temperature=ate_record['tdegc'])

    def set_corr_traceability(self,*args, **kwargs):
        self.tm._correlation_results._set_traceability_info(**getattr(self.tm.plugin_data_repo,'traceability_results', {}))

    def register_test_get_test_limits(self, test_name):
        return self.tm._correlation_results._correlation_declarations[test_name]

    def get_corr_pass_fail(self):
        return bool(self.tm._correlation_results)

    def run_repeatability_results(self):
        super().run_repeatability_results()
        results = collections.OrderedDict() #De-tangle runs
        for test_run in self.tm.tt:
            for corr_name in test_run._correlation_results:
                try:
                    # TODO shared results dict???
                    results[corr_name].append(test_run._correlation_results[corr_name])
                except KeyError as e:
                    results[corr_name] = []
                    results[corr_name].append(test_run._correlation_results[corr_name])
                # TODO THEN WHAT with CORR??

    def generate_json(self, db_file=None):
        if len(self.tm._correlation_results):
            if self._one_result_print:
                res_str = f'{self.tm._correlation_results}'
                passes = self.tm._correlation_results
                res_str += f'*** Module {self.tm.get_name()} Correlation Summary {"PASS" if passes else "FAIL"}. ***\n\n'
                print(res_str)
                self._one_result_print = False
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
        super().generate_json(db_file=db_file)
    def tt_compile_test_results(self):
        res_str = super().tt_compile_test_results()
        if len(self.tm._correlation_results):
            if self._one_result_print:
                res_str_corr = f'{self.tm._correlation_results}'
                passes = self.tm._correlation_results
                res_str_corr += f'*** Module {self.tm.get_name()} Correlation Summary {"PASS" if passes else "FAIL"}. ***\n\n'
                self._one_result_print = False
                print(res_str_corr)
                res_str += res_str_corr
        return res_str

    def display_correlation_results(self, table_name, db_file=None):
        if len(self.tm._correlation_results):
            if self._one_result_print:
                res_str = f'{self.tm._correlation_results}'
                passes = self.tm._correlation_results
                res_str += f'*** Module {self.tm.get_name()} Correlation Summary {"PASS" if passes else "FAIL"}. ***\n\n'
                print(res_str)
                self._one_result_print = False
    def _test_from_table(self, table_name=None, db_file=None, *args, **kwargs):
        if not hasattr(self.tm, '_correlation_results'):
            self.tm._correlation_results = correlation_results(self.tm.get_name(), module=self.tm)
        self.tm._correlation_results.set_table_name(table_name)
        self.tm._correlation_results.set_db_filepath(os.path.abspath(db_file))
        self.set_corr_traceability()
        super()._test_from_table(table_name=table_name, db_file=db_file,*args,**kwargs)
    def register_refids(self, *args):
        self.tm._correlation_results = correlation_results(self.tm.get_name(), module=self.tm)
        super().register_refids(*args)
