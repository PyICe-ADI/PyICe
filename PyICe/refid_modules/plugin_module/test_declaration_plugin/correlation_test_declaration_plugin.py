from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.refid_modules import stdf_utils
from PyICe.refid_modules.plugin_module.plugin   import plugin
from PyICe.refid_modules.test_results           import correlation_results
from types import MappingProxyType
import abc, traceback, pdb, math, os, sqlite3, importlib

def isnan(value):
    try:
        return math.isnan(float(value))
    except (TypeError,ValueError):
        return False

class correlation_test_declaration(plugin):
    desc = "Associates collected data with named test and compares to a different set of data to assign a pass/fail status."
    def __init__(self, test_mod, correlation_data_location):
        super().__init__(test_mod)
        self.tm.interplugs['register_correlation_test__test_from_table']=[]
        self.tm.interplugs['register_correlation_test_get_correlation_data']=[]
        self.correlation_data_location=correlation_data_location
        self._one_result_print = True
        # self.supplemental_thing = importlib.import_module(name=self.tm.plugins[self.__class__.__name__]['dependencies']['correlation_supplements'], package=None).correlation_plugin_supp(self.tm)
        # self.tm=[]

    def __str__(self):
        return "Associates collected data with named test and compares to a different set of data to assign a pass/fail status."

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                   'get_correlation_declarations':self.get_correlation_declarations,
                   'register_correlation_test':self.register_correlation_test,
                   'register_correlation_result':self.register_correlation_result,
                   'register_correlation_failure':self.register_correlation_failure,
                   '_get_ate_population_data':self._get_ate_population_data,
                   '_get_correlation_data':self._get_correlation_data,
                   'get_correlation_data_scalar':self.get_correlation_data_scalar,
                   'get_correlation_data':self.get_correlation_data,
                   'get_ate_population_data':self.get_ate_population_data,
                   'reg_ate_result':self.reg_ate_result,
                   'display_correlation_results':self.display_correlation_results,
                   'register_test_get_pass_fail':self.register_test_get_pass_fail,
                   'register_test_get_test_results':self.register_test_get_test_results,
                   'register_test_run_repeatability_results':self.register_test_run_repeatability_results,
                   'register_test_set_tm':self.register_test_set_tm,
                   'register_test__test_from_table_2':self.register_test__test_from_table_2,
                   'set_corr_traceability':self.set_corr_traceability,
                    })

    def get_atts(self):
        return self.att_dict

    def get_hooks(self):
        plugin_dict={
                    }
        return plugin_dict

    def set_interplugs(self):
        try:
            self.tm.interplugs['register_test__compile_test_results'].extend([self.reg_ate_result])
            self.tm.interplugs['register_test_tt_compile_test_results_2'].extend([self.display_correlation_results])
            self.tm.interplugs['register_test_get_test_results'].extend([self.register_test_get_test_results])
            self.tm.interplugs['register_test_get_pass_fail'].extend([self.register_test_get_pass_fail])
            self.tm.interplugs['register_test_run_repeatability_results'].extend([self.register_test_run_repeatability_results])
            self.tm.interplugs['register_test_set_tm'].extend([self.register_test_set_tm])
            self.tm.interplugs['register_test__test_from_table'].extend([self.set_table_name, self.set_db_filepath])
            self.tm.interplugs['register_test__test_from_table_2'].extend([self.display_correlation_results,self.register_test__test_from_table_2])
        except KeyError:
            raise Exception('This plugin requires the register_test_plugin to be included as well.')
        try:
            self.tm.interplugs['die_traceability_set_traceability'].extend([self.set_corr_traceability])
        except KeyError:
            raise Exception('This plugin requires the die_traceability_plugin to be included as well.')

    def get_correlation_declarations(self):
        return self._correlation_results.get_correlation_declarations()
    def register_correlation_test(self, name):
        
        ## They data needs to be provided somehow. We look at our imported refids, but the next group might not. So, import supplemental project specific script. 
        ##     corr_reg_inputs = self._get_corr_inputs(self, name, test_module)
        ## This will return a dictionary of the arguments for the self.tm._correlation_results._register_correlation_test, which will just be called with (**corr_reg_inputs)
        ## self.supplemental_thing.
        
        if name not in self.tm.REFIDs.keys():
            raise Exception(f'ERROR: Correlation test {name} registered from {self.tm.get_name()} not found in REFID master spec.')
        if self.tm.REFIDs[name]['CORRELATION SPEC'] != 'Δ' and self.tm.REFIDs[name]['CORRELATION SPEC'] != '%':
            raise Exception(f"ERROR: Correlation test {name} registered from {self.tm.get_name()} appears to have invalid correlation column type {self.tm.REFIDs[name]['CORRELATION SPEC']}. Contact support.")
        self.tm._correlation_results._register_correlation_test(refid_name=name,
                                                             ATE_test=self.tm.REFIDs[name]['ATE TEST #'],
                                                             ATE_subtest=self.tm.REFIDs[name]['ATE SUBTEST #'],
                                                             owner=self.tm.REFIDs[name]['OWNER'],
                                                             assignee=self.tm.REFIDs[name]['ASSIGNEE'],
                                                             lower_limit=self.tm.REFIDs[name]['MIN'] if not isnan(self.tm.REFIDs[name]['MIN']) else None,
                                                             upper_limit=self.tm.REFIDs[name]['MAX'] if not isnan(self.tm.REFIDs[name]['MAX']) else None,
                                                             unit=self.tm.REFIDs[name]['UNIT'],
                                                             description=self.tm.REFIDs[name]['DESCRIPTION'],
                                                             notes=f"{self.tm.REFIDs[name]['CONDITIONS']}\n{self.tm.REFIDs[name]['COMMENTS / METHOD']}",
                                                             limits_units_percentage=(self.tm.REFIDs[name]['CORRELATION SPEC'] == '%')
                                                            )
    def register_correlation_result(self, name, data_temp_pairs, conditions=None):
        '''register correlation results against corr REFIDs. Each data point must also contain a temperature setpoint for matching to ATE data.'''
        self.tm._correlation_results._register_correlation_result(refid_name=name, iter_data=data_temp_pairs, conditions=conditions)
    def register_correlation_failure(self, name, reason, temperature, conditions=None):
        '''mark test failed, without submitting test data'''
        self.tm._correlation_results._register_correlation_failure(name, reason, temperature, conditions)

    # def get_correlation_data(self, REFID, *args, **kwargs):
        # return supplemental_thing._get_correlation_data(REFID, *args, **kwargs)
    def get_correlation_data(self, REFID, temperature=None, strict=False, extra_columns=[]):
        self.execute_interplugs('register_correlation_test_get_correlation_data', REFID, temperature, strict, extra_columns)
        try:
            self.tm.REFIDs[REFID]
        except KeyError:
            # TODO more than printed warning???? Exception?
            if strict:
                raise ATETestException(f'{REFID} not found in REFID worksheet.')
            else:
                print(f'''WARNING: {REFID} lookup from worksheet failed. This is either a "fake" REFID or there's a typo. Correlation data won't be found.''')
                return [] # Fake REFID
        try:
            if temperature.upper() == 'NULL':
                temperature = 25 #correlate bench data without oven; tdegc=NULL. TODO 25 vs "25".
        except AttributeError:
            pass #can't upper() a number. Better to ask for forgiveness....
        try:
            if math.isnan(self.tm.REFIDs[REFID]['ATE TEST #']) or math.isnan(self.tm.REFIDs[REFID]['ATE SUBTEST #']):
                # Blank cells in worksheet
                if strict:
                    raise ATEBlankException(f'{REFID} ATE number lookup from worksheet failed. Found blank cell(s) for test number.')
                else:
                    # print(f'''WARNING: {REFID} ATE number lookup from worksheet failed. Correlation data won't be found.''') # DJS remove? Probably too naggy...
                    return []
        except TypeError as e:
            # It's not blank, and it's not a number either. Probably a string
            if not strict:
                return []
            elif self.tm.REFIDs[REFID]['ATE TEST #'] == 'NA' or self.tm.REFIDs[REFID]['ATE SUBTEST #'] == 'NA':
                raise ATENAException(f'{REFID}')
            elif self.REFIDs[REFID]['ATE TEST #'] == 'TBD' or self.tm.REFIDs[REFID]['ATE SUBTEST #'] == 'TBD':
                raise ATETBDException(f'{REFID}')
            else:
                raise ATELinkageException(f'{REFID}')

        try:
            return self.tm._get_correlation_data(ate_test_number=(self.tm.REFIDs[REFID]['ATE TEST #'],self.tm.REFIDs[REFID]['ATE SUBTEST #']), temperature=temperature, extra_columns=extra_columns)
        except stdf_utils.testNumberException as e:
            if strict:
                raise ATETestException(f'{REFID}') from e
            else:
                print(e)
                return []
    def get_correlation_data_scalar(self, REFID, temperature):
        if temperature is None: temperature = 'NULL'#Database queries from ambient data forced to 25C correlation.
        result = self.get_correlation_data(REFID, temperature, strict=True, extra_columns=['FLOW_ID','STDF_file'])
        # assert len(result) <= 1, 'Temperature not available or mutiple rows found in ATE data at the temperature requested'
        if len(result) > 2:
            raise ATEDataException(f'Multiple rows found in ATE data at temperature {temperature} for DuT {self._traceability_hash_table}. Contact PyICe Support at PyICe-developers@analog.com.\n{[row["STDF_file"] for row in result]}')
        elif len(result) == 2:
            flows = set([row['FLOW_ID'] for row in result])
            if flows == set(('FT TRIM', 'QA ROOM')):
                # Specific exemption to favor QAR data over FTR data when both exist. Other cases not handled (deliberately, for now).
                result = [row for row in result if row['FLOW_ID'] == 'QA ROOM']
                assert len(result) == 1
                return result[0]['ate_data']
            raise ATEDataException(f'Multiple rows found in ATE data at temperature {temperature} for DuT {self._traceability_hash_table}. Contact PyICe Support at PyICe-developers@analog.com.\n{[row["STDF_file"] for row in result]}')
        elif len(result) == 0:
            # Old:
            ########################
            # Differentiate between missing data (maybe ok) and missing link to data (less ok).
            # This method is less tolerant of the missing link than get_correlation_data() because it's called manually and therefore deliberately. The other one is called in the normal flow of every test even when correlation is not planned.
            #try:
            #    if isnan(self.REFIDs[REFID]['ATE TEST #']) or isnan(self.REFIDs[REFID]['ATE SUBTEST #']):
            #        raise Exception(f'Missing REFID worksheet link between {REFID} and ATE test number.')
            #except TypeError as e:
            #    raise Exception(f'Invalid REFID worksheet link between {REFID} and ATE test number.')
            ########################
            # Data is missing; ok.
            return None                     #If there is no ATE Data at the requested temperature, return None
        elif len(result) == 1:
            return result[0]['ate_data']    #Unpack the scalar data in the 'ate_data' entry of the dictionary in the list returned by get_correlation_data
        else:
            raise ATEDataException('How did I get here? Contact support at PyICe-developers@analog.com.')
    def _get_correlation_data(self, ate_test_number, temperature=None, extra_columns=[]):
        if not hasattr(self.tm, '_traceability_hash_table'):
            raise Exception(f'WARNING: get_correlation_data() called before _traceability_hash_table computed from database. Contact support. ({self.tm.get_name()})')
        elif self.tm._traceability_hash_table is None:
            # Problem getting traceability data from database. Perhaps it was never logged?
            raise Exception(f'WARNING: get_correlation_data() unable to determine uniqe DUT ID. Were f_die_<> registers logged?. ({self.tm.get_name()})')
        else:
            if temperature is None:
                where_clause = ''
                temp_message = ''
            else:
                where_clause = f'AND CAST(TST_TEMP AS NUMERIC) == {temperature}'
                temp_message = f' at temperature {temperature}C'
            if len(extra_columns):
                extra_columns_clause = f", {', '.join(extra_columns)}"
            else:
                extra_columns_clause = ''
            ate_test_number = stdf_utils.test_number(ate_test_number).to_string()
            query_str = f'SELECT "{ate_test_number}" as ate_data, CAST(TST_TEMP AS INTEGER) AS tdegc{extra_columns_clause} FROM population_data WHERE TRACEABILITY_HASH == "{self.tm._traceability_hash_table}" {where_clause}'
            correlation_db_filename = os.path.join(os.path.dirname(__file__), f'../../../../../{self.correlation_data_location}')

            try:
                db = sqlite_data(database_file=correlation_db_filename)
                db.query(query_str)
                rows = db.to_list()
                if not len(rows):
                    # print(f'WARNING: Correlation data rows not found for DUT {self._traceability_hash_table}{temp_message}.') #TODO too many warnings!!!
                    pass
                return [{k: r[k] for k in r.keys()} for r in db.to_list()]
            except sqlite3.OperationalError as e:
                # OperationalError('no such table: 0xC6A857A5')
                # TODO: check error more carefully with regular expression or examination of exception object??
                print(f'WARNING: Correlation database not found for DUT {self.tm._traceability_hash_table}.{e}')
                # raise e
                return []

    def get_ate_population_data(self, REFID, temperature=None):
        try:
            self.REFIDs[REFID]
        except KeyError:
            # TODO print warning????
            return [] # Fake REFID
        try:
            if isnan(self.REFIDs[REFID]['ATE TEST #']) or isnan(self.REFIDs[REFID]['ATE SUBTEST #']):
                return [] # None #no test number reference. skip. Todo: exception instead of None??
        except TypeError as e:
            return [] # probably a string
        try:
            return self._get_ate_population_data(ate_test_number=(self.REFIDs[REFID]['ATE TEST #'],self.REFIDs[REFID]['ATE SUBTEST #']), temperature=temperature)
        except stdf_utils.testNumberException as e:
            print(e)
            return []
        except sqlite3.OperationalError as e:
            # OperationalError('no such table: 0xC6A857A5')
            # TODO: check error more carefully with regular expression or examination of exception object??
            print(f'WARNING: ATE data not found for REFID: {REFID}, ATE test {(self.REFIDs[REFID]["ATE TEST #"],self.REFIDs[REFID]["ATE SUBTEST #"])}.')
            return []

    def _get_ate_population_data(self, ate_test_number, temperature=None):
        if not hasattr(self, '_traceability_hash_table'):
            raise Exception(f'WARNING: get_correlation_data() called before _traceability_hash_table computed from database. Contact support. ({self.get_name()})')
        elif self._traceability_hash_table is None:
            # Problem getting traceability data from database. Perhaps it was never logged?
            raise Exception(f'WARNING: get_correlation_data() unable to determine uniqe DUT ID. Were f_die_<> registers logged?. ({self.get_name()})')
        else:
            if temperature is None:
                where_clause = f''
            else:
                where_clause = f'WHERE CAST(TST_TEMP AS NUMERIC) == "{temperature}"'
            ate_test_number = stdf_utils.test_number(ate_test_number).to_string()
            # Double quotes are SQL for "identifier". Unfortunately, SQLite implementation allowes them to revert to strong literal if unmatched, which breaks the query. Use non-standard square braces (MS Access) compatibility, which has no such fallback
            query_str = f'SELECT min([{ate_test_number}]) as ate_min, avg([{ate_test_number}]) as ate_mean, max([{ate_test_number}]) as ate_max, CAST(TST_TEMP AS INTEGER) AS tdegc FROM population_data {where_clause} GROUP BY tdegc'
            # query_str = f'SELECT min("{ate_test_number}") as ate_min, avg("{ate_test_number}") as ate_mean, max("{ate_test_number}") as ate_max, CAST(TST_TEMP AS INTEGER) AS tdegc FROM population_data {where_clause} GROUP BY tdegc'
            # query_str = f"SELECT '{ate_test_number}', TST_TEMP AS tdegc FROM '{self._traceability_hash_table}' {where_clause}" #No good. A keyword in single quotes is a string literal. A keyword in double-quotes is an identifier.
            #Magic number alert:
            correlation_db_filename = os.path.join(os.path.dirname(__file__), '../../correlation/stdf_data.sqlite')
            try:
                db = sqlite_data(database_file=correlation_db_filename)
                db.query(query_str)
                return [{k: r[k] for k in r.keys()} for r in db.to_list()]
            except sqlite3.OperationalError as e:
                raise

    def reg_ate_result(self):
        for test in self.tm.get_test_declarations():
            c_d = self.tm.get_correlation_data(test)
            for ate_record in c_d:
                self.tm._test_results._register_ate_result(name=test, result=ate_record['ate_data'], temperature=ate_record['tdegc'])

    def set_corr_traceability(self,test=None):
        self.tm._correlation_results._set_traceability_info(**self.tm._get_traceability_info(table_name=None, db_file=None))

    def register_test_get_test_limits(self, test_name):
        return self.tm._correlation_results._correlation_declarations[test_name]

    def register_test_get_test_results(self, res_str):
        pass
         # res_str+= self._correlation_results

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
        self.tm = test_module
        self.tm._correlation_results = correlation_results(self.tm.get_name(), module=self.tm)
        for (key,value) in self.get_atts().items():
            self.tm._add_attr(key,value)
    def set_table_name(self, table_name, *args,**kwargs):
        self.tm._correlation_results.set_table_name(table_name)
    def set_db_filepath(self, db_file, *args, **kwargs):
        self.tm._correlation_results.set_db_filepath(os.path.abspath(db_file))