from PyICe.lab_utils.sqlite_data                import sqlite_data
from PyICe.lab_utils.banners                    import build_banner
from PyICe.refid_modules                        import stdf_utils
from PyICe.refid_modules.test_results           import test_results
from PyICe.refid_modules.plugin_module.plugin   import plugin
from types import MappingProxyType
import traceback, pdb, os, sys, collections

class ATEDataException(Exception):
    '''Superclass of errors related to fetching ATE data.'''
class ATETraceabilityException(ATEDataException):
    '''Can't uniquely identify DUT to find data.'''
class ATELinkageException(ATEDataException):
    '''Superclass of problems matching a REFID to an ATE test.'''
class ATENAException(ATELinkageException):
    '''Can't fetch ATE data because the test number is listed "NA".'''
class ATETBDException(ATELinkageException):
    '''Can't fetch ATE data because the test number is listed "TBD".'''
class ATEBlankException(ATELinkageException):
    '''Can't fetch ATE data because the test number is unlisted.'''
class ATETestException(ATELinkageException):
    '''Can't fetch ATE data because the test number is invalid.'''

class limit_test_declaration(plugin):
    desc = "Associates data collected with a named test and a compares to set limits to assign a pass/fail status."
    def __init__(self, test_mod):
        super().__init__(test_mod)
        self.registered_tests = set()
        self.tm.interplugs['register_test__test_from_table']=[]
        self.tm.interplugs['register_test__test_from_table_2']=[]
        self.tm.interplugs['register_test__compile_test_results']=[]
        self.tm.interplugs['register_test_tt_compile_test_results']=[]
        self.tm.interplugs['register_test_tt_compile_test_results_2']=[]
        self.tm.interplugs['register_test_get_test_results']=[]
        self.tm.interplugs['register_test_get_pass_fail']=[]
        self.tm.interplugs['register_test_run_repeatability_results']=[]
        self.tm.interplugs['register_test_set_tm']=[]
        self.tm._test_results = test_results(self.tm.get_name(), module=self.tm)
        self._single_results_print = True

    def __str__(self):
        return "Associates data collected with a named test and a compares to set limits to assign a pass/fail status."

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                        'get_test_limits':self.get_test_limits,
                        'get_test_upper_limit':self.get_test_upper_limit,
                        'get_test_lower_limit':self.get_test_lower_limit,
                        'get_test_declarations':self.get_test_declarations,
                        'get_exclude_reason':self.get_exclude_reason,
                        'set_exclude':self.set_exclude,
                        'is_included':self.is_included,
                        '_register_test':self._register_test,
                        'register_test_functional':self.register_test_functional,
                        'register_test_exact':self.register_test_exact,
                        'register_test_abs_limits':self.register_test_abs_limits,
                        'register_test_abs_tol':self.register_test_abs_tol,
                        'register_test_rel_tol':self.register_test_rel_tol,
                        'register_test_abs_tol_asym':self.register_test_abs_tol_asym,
                        'register_test_rel_tol_asym':self.register_test_rel_tol_asym,
                        'register_test_result':self.register_test_result,
                        'register_test_failure':self.register_test_failure,
                        '_compile_test_results':self._compile_test_results,
                        'get_test_results':self.get_test_results,
                        'get_pass_fail':self.get_pass_fail,
                        'test_from_table':self.test_from_table,
                        '_test_from_table':self._test_from_table,
                        'tt_compile_test_results':self.tt_compile_test_results,
                        'add_registration':self.add_registration,
                        'run_repeatability_results':self.run_repeatability_results,
                        'register_refids':self.register_refids,
                        })

    def get_atts(self):
        return self.att_dict

    def get_hooks(self):
        plugin_dict={
                    'pre_collect':[self.register_refids, self.add_registration],
                    'post_collect':[self.tt_compile_test_results],
                    'tm_plot_from_table':[self.register_refids,self.set_table_name, self.set_db_filepath, self._test_from_table],
                    'post_repeatability':[self.run_repeatability_results],
                    }
        return plugin_dict

    def set_interplugs(self):
        pass

    def register_refids(self, *args):
        """
        Executes the register_tests method of the test script after providing an opening for interplugs to interact.
        
        Args:
            *args - completely ignored. Only included to make it easy for whatever is calling this method. 
        """
        self.tm._compile_crashed = None
        self.execute_interplugs('register_test_set_tm', self.tm)
        if self.tm._is_multitest_module:
            for multitest_unit in self.tm._multitest_units:
                multitest_unit.register_tests()
        else:
            self.tm.register_tests()

    def set_table_name(self, table_name, *args, **kwargs):
        """
        Establishes the database table to be used for the test.

        Args:
            table_name  - String. Name to be given to the table.
            *args       - Unused. Provided for ease of method call.
            **kwargs    - Unused. Provided for ease of method call.
        """
        self.tm._test_results.set_table_name(table_name)
    def set_db_filepath(self, db_file, *args,**kwargs):
        """
        Establishes the database location to be used for the test.

        Args:
            db_file     - Any identifying method of the database location that can be recognized by os.path.abspath.
            *args       - Unused. Provided for ease of method call.
            **kwargs    - Unused. Provided for ease of method call.
        """
        self.tm._test_results.set_db_filepath(os.path.abspath(db_file))

    def add_registration(self):
        """
        Adds to the set of declared test names. Each name must be unique, or an Error will occur.
        """
        for decl in self.tm.get_test_declarations():
            if decl in self.registered_tests:
                raise Exception(f'Duplicated test name {decl} across modules {self.tm.tt._tests[-1].get_name()}!')
            else:
                self.registered_tests.add(decl)

    def tt_compile_test_results(self):
        """
        Produces a pass/fail/crash string for all results. Will pass the string to those affected by temptroller's notify method.
        
        Returns:
            A string that contains a pass/fail/crash verdict on registered tests.
        """
        res_str = ''
        all_pass = True
        try:
            if self.tm._crashed is None:
                self.execute_interplugs('register_test_tt_compile_test_results', self)
            self._compile_test_results()
            if self.tm._compile_crashed is not None:
                (typ, value, trace_bk) = self.tm._compile_crashed
                notify_message = f'{self.tm.get_name()} compile test result crash! Moving on.\n'
                notify_message += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
                self.tm.tt.notify(f'{self.tm.tt.get_bench_identity()["user"]} on {self.tm.tt.get_bench_identity()["host"]}\n'+notify_message)
            res_str = f'{res_str}\n{self.get_test_results()}'
            all_pass &= self.get_pass_fail()

            res_str += '***********************\n'
            res_str += f'*   Summary: {"PASS" if all_pass else "FAIL"}     *\n'
            res_str += '***********************\n'
            self.tm.tt.notify(res_str, subject='Test Results')
            self._single_results_print = False
            self.execute_interplugs('register_test_tt_compile_test_results_2', self)
        except AttributeError as e:
            print(e)
        return res_str
        #TODO check for duplicated results reporting. By REFID?

    def get_test_limits(self, test_name):
        """
        Returns a tuple of the upper and lower limits of the given test_name.
        
        Args:
            test_name   - String. The name of the test which has the limits requested.
        
        Returns
            Tuple. Lower limit first, then upper limit.
        """
        try:
            tst_decl = self.tm._test_results._test_declarations[test_name]
        except KeyError:
            tst_decl = self.execute_interplugs('register_test_get_test_limits', test_name)
        #test_declaration(test_name='CH0_VDROOP', requirement_reference=None, lower_limit=-0.15, upper_limit=0.15, description='CH0 droop due to load step', notes=None)
        return (tst_decl.lower_limit, tst_decl.upper_limit)
    def get_test_upper_limit(self, test_name):
        """
        Returns just the upper limit of the given test_name.
        
        Args:
            test_name   - String. The name of the test which has the limit requested.
        
        Returns
            The value of the upper limit. Type is the same as what was initially provided at registration.
        """
        return self.get_test_limits(test_name)[1]
    def get_test_lower_limit(self, test_name):
        """
        Returns just the lower limit of the given test_name.
        
        Args:
            test_name   - String. The name of the test which has the limit requested.
        
        Returns
            The value of the lower limit. Type is the same as what was initially provided at registration.
        """
        return self.get_test_limits(test_name)[0]
    def get_test_declarations(self):
        """
        Returns a list of the registered test_names.
        
        Returns
            List. All the tests registered during register_tests().
        """
        return self.tm._test_results.get_test_declarations()
    def set_exclude(self, reason):
        '''call from inside register_tests or register_multitest_units to exclude from audit and regressions. ie, debug, WIP, boneyard, alternate implementation, etc.'''
        self._exclude_reason = reason
    def get_exclude_reason(self):
        """
        Returns the scripts provided excuse for being excluded from audits, if any.
        
        Returns
            String or NoneType. Reason provided when test was declared excluded. Returns NoneType if it is not excluded.
        """
        try:
            return self._exclude_reason
        except AttributeError:
            return
    def is_included(self):
        """
        A check to see if a script is included in audits.
        
        Returns
            Bool. True if no reason for exclusion was provided, else False.
        """
        try:
            self._exclude_reason
            return False
        except AttributeError:
            return True

    #@typing.final
    def _register_test(self, name, lower_limit, upper_limit, **kwargs):
        #need some consitent vocabulary. What is a test? What is a sweep?
        #should tests and test results be linked back to their collection sweep more explicitly through this data model?
        '''
        The basic form of registering tests. Should not be called itself. All arguments are passed on to the test_results and made into attributes.
        
        Args:
            name        - String. Name to be used for this test.
            lower_limit - Lower limit against which all result data will be compared.
            upper_limit - Upper limit against which all result data will be compared.
            **kwargs    - Attributes that will be linked to the test.
        '''
        if self.is_included():
            if name not in self.tm.REFIDs.keys():
                print(f'WARNING! Test {name} registered from {self.tm.get_name()} not found in REFID master spec.') 
        self.tm._test_results._register_test(name=name, lower_limit=lower_limit, upper_limit=upper_limit, **kwargs)

    #@typing.final
    def register_test_functional(self, name, **kwargs):
        """
        Registers a test which will only be looking at boolean results.
        
        Args:
            name        - String. Name to be used for this test.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=True, upper_limit=True, **kwargs)
    #@typing.final
    def register_test_exact(self, name, expect, **kwargs):
        """
        Registers a test which does not allow for a window.
        
        Args:
            name        - String. Name to be used for this test.
            expect      - Int, Float, String, Bool. Value against which all result data will be compared.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=expect, upper_limit=expect, **kwargs)
    #@typing.final
    def register_test_abs_limits(self, name, min_abs=None, max_abs=None, **kwargs):
        """
        Registers a test that will pass if all submitted result values are within the provided limits.
        
        Args:
            name        - String. Name to be used for this test.
            min_abs     - Int, Float, None. Minimum Value against which all result data will be compared. If None, there is no lower limit.
            max_abs     - Int, Float, None. Maximum Value against which all result data will be compared. If None, there is no upper limit.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=min_abs, upper_limit=max_abs, **kwargs)
    #@typing.final    
    def register_test_abs_tol(self, name, expect, abs_tolerance, **kwargs):
        """
        Registers a test that will pass if all submitted result values are within the given tolerance of the given expected value.
        
        Args:
            name        - String. Name to be used for this test.
            expect      - Int, Float. Value against which all result data will be compared.
            abs_tolerance- Int, Float. Maximum distance from which all result data can be from expected value.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=expect-abs_tolerance, upper_limit=expect+abs_tolerance, **kwargs)
    #@typing.final
    def register_test_rel_tol(self, name, expect, rel_tolerance, **kwargs):
        """
        Registers a test that will pass if all submitted result values are within the given percentage of the given expected value.
        
        Args:
            name        - String. Name to be used for this test.
            expect      - Int, Float. Value against which all result data will be compared.
            rel_tolerance- Int, Float. Percent off a passing result can be from the expected value.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=expect*(1-rel_tolerance), upper_limit=expect*(1+rel_tolerance), **kwargs)
    #@typing.final    
    def register_test_abs_tol_asym(self, name, expect, min_abs_tolerance=None, max_abs_tolerance=None, **kwargs):
        """
        Registers a test that will pass if all submitted result values are within the given tolerance of the given expected value.
        
        Args:
            name        - String. Name to be used for this test.
            expect      - Int, Float. Value against which all result data will be compared.
            min_abs_tolerance- Int, Float. Maximum Value from which all result data can be below expected value.
            max_abs_tolerance- Int, Float. Maximum Value from which all result data can be above expected value.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=expect-min_abs_tolerance, upper_limit=expect+max_abs_tolerance, **kwargs)
    #@typing.final
    def register_test_rel_tol_asym(self, name, expect, min_rel_tolerance=None, max_rel_tolerance=None, **kwargs):
        """
        Registers a test that will pass if all submitted result values are within the given percentage of the given expected value.
        
        Args:
            name        - String. Name to be used for this test.
            expect      - Int, Float. Value against which all result data will be compared.
            min_rel_tolerance- Int, Float. Percent off a passing result can be below the expected value. If None, there will be no lower limit.
            max_rel_tolerance- Int, Float. Percent off a passing result can be above the expected value. If None, there will be no upper limit.
            **kwargs    - Attributes that will be linked to the test.
        """
        self._register_test(name=name, lower_limit=expect*(1-min_rel_tolerance), upper_limit=expect*(1+max_rel_tolerance), **kwargs)
    ###store limit type for each test, or discard?
    #@typing.final
    def register_test_result(self, name, data, conditions=None):
        '''
        Submit data to be considered.
        
        Args:
            name    - String. Name of the registered test the data is for.
            data    - Boolean, or any iterable. Data to be compared to the upper and lower limits of the named test.
            conditions - Dictionary. Only used if the iterable is a sqlite database. Groups the data provided by the channel names provided in the values.
        '''
        #data should be True/False or iterable.
        #Handle True/False here for functional tests, or pass through?
        self.tm._test_results._register_test_result(name=name, iter_data=data, conditions=conditions)
    def register_test_failure(self, name, reason='', conditions=None):
        '''mark test failed, without submitting test data
        
        Args:
            name        - String. Name of the test that failed.
            reason      - Optional. String. Reason for the failure. Will be logged in the database.
            conditions  - Optional. None, String. Conditions under which the test reached the failure.           
        '''
        self.tm._test_results._register_test_failure(name, reason, conditions)

    def _compile_test_results(self, table_name=None, db_file=None):
        '''get database loaded up first to streamline test module'''
        if self.tm._crashed is not None:
            print(f'Skipping test result compilation for crashed test {self.tm.get_name()}.')
        else:
            if table_name is None:
                table_name = self.tm.get_db_table_name()
            if db_file is None:
                # db = self.tm.get_db()
                db = sqlite_data(database_file=self.tm._db_file, table_name=table_name)
            else:
                db = sqlite_data(database_file=db_file, table_name=table_name)
            if f'{table_name}_all' in db.get_table_names():
                table_name = f"{table_name}_all" #Redirect to presets-joined table
                db.set_table(table_name)
            # print(table_name)
            if self.tm.bench_name == None:
                my_bench=db.query(f'SELECT bench FROM {table_name}').fetchone()['bench']
                self.tm.bench_name=my_bench[my_bench.find('benches')+8:my_bench.find("' from")]
            try:
                self.tm.compile_test_results(database=db, table_name=table_name)
                self.execute_interplugs('register_test__compile_test_results')
                self.tm._test_results._plot()
            except Exception as e:
                # Something else, NOS, has gone wrong with REFID result plotting. Let's try to muddle through it to avoid interrupting the other plots and still give a chance of archiving.
                if self.tm._debug:
                    traceback.print_exc()
                    if input('Debug [y/n]? ').lower() in ('y', 'yes'):
                        pdb.post_mortem()
                    else:
                        # Just crash. No sense in carrying on with other tests in the regression.
                        raise e
                self.tm._compile_crashed = sys.exc_info()
                for t in self.get_test_declarations():
                    self.register_test_failure(t)

    def get_test_results(self):
        # moved crashing bench name stuff up to _compile_test_results where it has access to database table name.
        res_str =  f'\nTested on {self.tm.bench_name}\n'
        res_str += f'*** Module {self.tm.get_name()} ***\n'
        res_str += f'{self.tm._test_results}{self.tm.crash_info()}'
        passes = self.tm._test_results
        res_str += f'*** Module {self.tm.get_name()} Summary {"PASS" if passes else "FAIL"}. ***\n\n'
        self.execute_interplugs('register_test_get_test_results', res_str)
        return res_str
    def get_pass_fail(self):
        # self.execute_interplugs('register_test_get_pass_fail')
        return not self.tm.is_crashed() and bool(self.tm._test_results)

    def run_repeatability_results(self):
        results = collections.OrderedDict() #De-tangle runs
        for test_run in self.tm.tt:
            for test_name in test_run._test_results:
                try:
                    results[test_name].append(test_run._test_results[test_name])
                except KeyError as e:
                    results[test_name] = []
                    results[test_name].append(test_run._test_results[test_name])
            self.execute_interplugs('register_test_run_repeatability_results', test_run)
        for test_name in results:
            print('TODO FIXME to factor trials')

# 
# 
#             for condition_hash, condition_orig in results[t_d].get_conditions().items():
#                 filter_results = results[t_d].filter(condition_hash)
#                 cond_dict =  {'conditions': condition_orig, #TODO put back to dictionary!
#                               'case_results': [{k:v for k,v in t_r._asdict().items() if k not in ['test_name', 'conditions', 'plot']} for t_r in filter_results], 
# 
# 
#                               for temperature in results[t_d].get_temperatures():
#                         temperature_dict = {'temperature': temperature,
#                                             'cases': [],
#                                             # 'summary': {},
#                                            }
#                         res_dict['tests'][t_d]['results']['temperatures'].append(temperature_dict)
#                         temp_group = results[t_d].filter_temperature(temperature)
#                         for condition_hash, condition_orig in temp_group.get_conditions().items():
#                             cond_group = temp_group.filter_conditions(condition_hash)
#                             cond_dict =  {'conditions': condition_orig,
#                                           'case_results': [{k:v for k,v in cond._asdict().items() if k not in ['refid_name', 'temperature', 'conditions']} for cond in cond_group],
#                                           'summary': {'min_error': cond_group._min_error(),
#                                                       'max_error': cond_group._max_error(),
#                                                       'passes':    bool(cond_group),
#                                                      },
#                                          }
#                             temperature_dict['cases'].append(cond_dict)
#                     
# 
# 
#             
#             print(f'{test_name} meanmean:{statistics.mean([trial.mean for trial in results[test_name]])}, meansigma:{statistics.stdev([trial.mean for trial in results[test_name]])}')
#             for trial in results[test_name]:
#                 print(f'\tmean:{trial.mean}, min:{trial.min_data}, max:{trial.max_data}')

    @classmethod
    def test_from_table(cls, table_name=None, db_file=None, debug=False):
        """
        Creates an instance of the script test, then calls and returns _test_from_table.
        
        Returns
            The return of _test_from_table.
        """
        self.tm = cls(debug=debug)
        return self._test_from_table(table_name, db_file)
    def _test_from_table(self, table_name=None, db_file=None):
        """
        Drawing upon a database, produces plots, compiles results, and creates a json.
        
        Args:
            table_name  -Optional. String. Name of the table from which data is drawn.
            db_file     -Optional. Any identifying method of the database location that can be recognized by os.path.abspath.
        """
        if not hasattr(self.tm, '_test_results'):
            self.tm._test_results = test_results(self.tm.get_name(), module=self.tm)
            self.execute_interplugs('register_test_set_tm', self.tm)
        self.tm._test_results.set_table_name(table_name)
        self.tm._test_results.set_db_filepath(os.path.abspath(db_file))
        self.execute_interplugs('register_test__test_from_table', table_name=table_name, db_file=db_file)
        self._compile_test_results(table_name, db_file)
        if self.tm._compile_crashed is not None:
            (typ, value, trace_bk) = self.tm._compile_crashed
            msg = f'{self.tm.get_name()} compile test results crash!.\n'
            msg += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
            # Skipping the "moving on" here on replotting (vs after collection) since it doesn't affect archive, etc.
            # print(notify_message)
            raise Exception(msg)
        res_str = self.tm.get_test_results()
        banner_str = [f'Summary: {"PASS" if self.tm.get_pass_fail() else "FAIL"}']
        if table_name is not None:
            banner_str.append(f'    {table_name}{" " * (38-len(table_name))}')
        res_str += build_banner(*banner_str)
        if self._single_results_print:
            print(res_str)
            self._single_results_print = False
        self.execute_interplugs('register_test__test_from_table_2', table_name, db_file)
        # JSON OUTPUT WIP
        if db_file==None:
            db_file=self.tm._db_file
        t_r = self.tm._test_results.json_report()
        dest_abs_filepath = os.path.join(os.path.dirname(db_file),f"test_results.json")
        try:
            if t_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(t_r.encode('utf-8'))
                    f.close()
        except PermissionError as e:
            print(f'ERROR: Unable to write {dest_abs_filepath}')
        # ######################
        return res_str


### From here on in, it's the test_result.py stuff.




















