from PyICe                                                                  import lab_core, lab_instruments, virtual_instruments, LTC_plot
from PyICe.refid_modules.temptroller                                        import temptroller
from PyICe.bench_configuration_management.bench_configuration_management    import bench_configuration_error
from PyICe.lab_utils.banners                                                import print_banner
from PyICe.lab_utils.sqlite_data                                            import sqlite_data

import abc
import datetime
import inspect
import math
import os.path
import pdb
import re
import sqlite3 #Catch exceptions
import sys
import traceback
# import typing


def isnan(value):
    try:
        return math.isnan(float(value))
    except (TypeError,ValueError):
        return False

class regressionException(Exception):
    '''special exception class to crash not just a single test module, but the whole enchilada.'''

#TODO: Missing data (rows, not columns) is not treated as an exception now. TBD.

class test_module(abc.ABC):
    '''class template
    all test modules shall inherit from this class and implement these abstract methods.
    '''

    _is_test_module = True
    _is_multitest_module = False
    _archive_enabled = None #class variable to prevent repeatability nagging
    #@typing.final
    def __init__(self, debug=False): #, lab_bench):
        '''TODO'''
        self.name = type(self).__name__
        self.bench_name = None
        self._is_setup = False
        self._logger = None
        self._archive_table_name = None #re-set by copy_table()
        (self._module_path, file) = os.path.split(inspect.getsourcefile(type(self)))
        db_filename = 'data_log.sqlite'
        self._db_file = os.path.join(self._module_path, db_filename)
        self._channel_reconfiguration_settings = []
        self._debug = debug
        type(self)._archive_enabled = not self._debug #Class variable

        self.test_timer = virtual_instruments.timer()
        self.test_timer.add_channel_total_minutes('test_time_min')
        self.test_timer.add_channel_delta_minutes('loop_time_min')
        self._crashed = None
        self._plot_crashed = None
        self._column_indices = []
        self.max_test_temp=None
        self.min_test_temp=None
        self.excluded_temperatures=[]
        self.tt=None
        if hasattr(self, 'plugins'):            ## Hokay. Slight issue here. If there's a regression going on, how do we make each test_module get a personal instance of a plugin?.
            for plugin in self.plugins.keys():
                plug = self.plugins[plugin]['instance']
                self.plug_instances.append(plug)
                for (k,v) in plug.get_atts().items():
                    self._add_attr(k,v)                                                ## Meaning one test_module calling the method will not affect another test_module's values. Sweet!
                for (k,v) in plug.get_hooks().items():
                    try:
                        self.plugin_hooks[k].extend(v)
                    except KeyError:
                        self.plugin_hooks[k]=v
        [ploog.set_interplugs() for ploog in self.plug_instances]
    @classmethod
    def __subclasshook__(cls, C):
        if cls is test_module:
            return True
        return NotImplemented
    def abort_regression(self, reason=None):
        '''force crash not just this test, but all of them.'''
        raise regressionException(reason)
    def debug_mode(self):
        '''query to see if module debug flag is set. useful where otherwise not provided as method argument, ex in setup().'''
        return bool(self._debug)
    @classmethod
    def get_name(cls):
        return cls.__name__
    def get_max_test_temp(self):
        return self.max_test_temp
    def set_max_test_temp(self,temperature):
        self.max_test_temp=temperature
    def get_min_test_temp(self):
        return self.min_test_temp
    def set_min_test_temp(self,temperature):
        self.min_test_temp=temperature
    def in_range(self,tdegc):
        if self.get_min_test_temp() is not None:
            if self.get_min_test_temp() > tdegc:
                return False
        if self.get_max_test_temp() is not None:
            if self.get_max_test_temp() < tdegc:
                return False
        return True
    def temp_is_included(self,tdegc):
        if self.is_crashed():
            return False
        elif tdegc in self.excluded_temperatures:
            return False
        elif not self.in_range(tdegc):
            return False
        return True
    def register_plugin(self, plugin):
        if not hasattr(self, 'plugins'):
            self.plugins={}
            self.plug_instances=[]
            self.plugin_hooks={}
        key = plugin.__class__.__name__
        self.plugins[key] = {}
        self.plugins[key]['instance']      = plugin
        self.plugins[key]['description']   = str(plugin)
        self.plugins[key]['data']          = {}
    def hook_functions(self, hook_key, *args):
        for (k,v) in self.plugin_hooks.items():
            if k is hook_key:
                for f in v:
                    f(*args)
    def _add_attr(self,key,value):
        setattr(self,key,value)
    def _execute_plugin_fns(self, func):
        func(self)
    @classmethod
    # @abc.abstractmethod #Make abstract eventually
    def configure_bench(cls, components):
        # print_banner(f'{cls.__name__}: No bench configuration declared.','The AI neural net will attempt to discern all adhoc bench connections and', 'make the declarations on your behalf.')
        raise bench_configuration_error(f'Test {cls.get_name()} failed to implement configure_bench(components). This is required for inclusion into the regression system.')
    def get_import_str(self):
        abspath = os.path.abspath(inspect.getsourcefile(type(self)))
        root_path = os.path.join(inspect.getsourcefile(test_module), '../../../..')
        relpath = os.path.relpath(abspath, start=root_path)
        modpath, ext = os.path.splitext(relpath)
        dirs = []
        while True:
            (head, tail) = os.path.split(modpath)
            dirs.insert(0, tail)
            if head == '':
                break
            else:
                modpath = head
        return '.'.join(dirs)
    def _add_timer_channels(self, logger):
        ch_cat = 'eval_traceability' #is this right?
        cumulative_timer = virtual_instruments.timer()
        cumulative_timer.add_channel_total_minutes('test_cumulative_time').set_category(ch_cat)
        cumulative_timer.add_channel_delta_minutes('test_incremental_time').set_category(ch_cat)
        temperature_timer = virtual_instruments.timer()
        temperature_timer.add_channel_total_minutes('test_temperature_incremental_time').set_category(ch_cat)
        temperature_timer.stop_and_reset_timer()
        logger.add(cumulative_timer)
        logger.add(temperature_timer)
        return (cumulative_timer, temperature_timer)

    @abc.abstractmethod
    def setup(self, channels):
        '''customize logger channels and virtual instruments for test here'''
    #@typing.final
    def _setup(self, lab_bench):
        '''entrance from temptroller'''
        if not self._is_setup:
            self._is_setup = True
            self._start_time = datetime.datetime.now()
            assert self._logger is None
            self._lab_bench = lab_bench #TODO should this be stored? Should it get set to None in __init__?
            self._logger = lab_core.logger(database=self._db_file, use_threads=not self._debug) #TODO Threading!!
            self.hook_functions('tm_logger_setup', self.get_logger())
            self._logger.merge_in_channel_group(lab_bench.get_master().get_flat_channel_group())
            (self._cumulative_timer, self._temperature_timer) = self._add_timer_channels(self.get_logger())
            ret = self.setup(self.get_logger())
            # Make sure traceability channels not removed
            # for register in stowe_die_traceability.stowe_die_traceability.nvm_derived_registers:
                # if register in stowe_die_traceability.stowe_die_traceability.zero_intercept_registers:
                    # continue # Legacy unused f_die_fab and f_die_parent_child not in future Yoda map.
                # assert register in self._logger.get_all_channel_names(), f'ERROR: Die traceability register {register} removed from test {self.get_name()} logger.\n\nIf I2C communications must be disabled, consider leveraging stowe_die_traceability:\n\nfrom stowe_eval.stowe_eval_base.modules.test_module import stowe_die_traceability\ndef setup(self, channels):\n    stowe_die_traceability.stowe_die_traceability.replace_die_traceability_channels(channels, powerup_fn=powerup, powerdown_fn=powerdown)\n\n'
            # for register in stowe_die_traceability.stowe_die_traceability.traceability_registers:
                # if register not in stowe_die_traceability.stowe_die_traceability.zero_intercept_registers:
                    # self._logger[register].set_write_access(False)
            # ----
            self._logger.new_table(table_name=self.get_name(), replace_table=True)
    #@abc.abstractmethod
    def teardown(self):
        '''Any test cleanup required after all temps?'''
        # Optional in test module. Probably almost never required.
        pass
    #@typing.final
    def _teardown(self):
        '''cleanup required (module, not per-collect)'''
        ret = self.teardown()
        if self._crashed is None:
            if not self._debug:
                table_name = self.copy_table() #TODO better timestamp? beginning of test?
                print(f"Copied test results table to {table_name}")
                if not self._archive_enabled:
                    # Copy table to timestamp version, but don't allow copy to new database. Perhaps test module unversioned.
                    self._archive_table_name = None # Un-do work done by self.copy_table()
            else:
                print(f'Skipping data archive for debug test {self.get_name()}.')
        else:
            print(f'Archiving crashed test results {self.get_name()} to disposable table.')
            self.get_logger().execute(f'DROP TABLE IF EXISTS {self.get_name()}_crash') #Copy will fail if destination exists.
            self.get_logger().execute(f'DROP VIEW IF EXISTS {self.get_name()}_crash_formatted') #Copy will fail if destination exists.
            self.get_logger().execute(f'DROP VIEW IF EXISTS {self.get_name()}_crash_all') #Copy will fail if destination exists.
            self.get_logger().copy_table(old_table=self.get_name(), new_table=f"{self.get_name()}_crash")
            self.get_logger().new_table(table_name=self.get_name(), replace_table=True) #Empty table to prevent accidental recording of bad data later.
        # if self._crashed is None: #this doesn't seem to fix anything if another test has crashed logger. Not sure why. They must share the backend thread somehow.
            # #print(self.get_name())
            # #self._logger.stop() #Unsafe to mess with logger if backed thread has crashed.
            # #Maybe shouldn't stop logger. It seems to go down with bench destruction.
            # pass
        return ret
    #@typing.final
    def _collect(self):
        if self._crashed is None:
            try:
                self._temperature_timer.resume_timer()
                self._temperature_timer.reset_timer()
                self._cumulative_timer.resume_timer()
                self._reconfigure()
                print_banner(f"Running Test: {self.get_name()}")
                self.collect(channels=self.get_logger(), debug=self._debug)
                self._temperature_timer.pause_timer()
                self._cumulative_timer.pause_timer()
            except regressionException as e:
                # raised by self.abort_regression(reason)
                # for example, if it's determined that the wrong DUT is inserted, no point in spending a whole day running inappropriate tests destined for certain failure.
                # prevent local handling of this one so that the temptroller can handle the shutdown and cleanup of all the other tests too.
                raise
            except (Exception, KeyboardInterrupt) as e:
                if self._debug or isinstance(e, KeyboardInterrupt):
                    #TODO - ctrl-c events will drop here, but leave PyICe locks in an inconsistent state.
                    #Need to figure out how to unwind the stack or move forward to a sensible place in the main script loop before entering debugger.

                    traceback.print_exc()
                    # Optionally drop into debugger or gui to give a chance to examine test conditions and results.
                    # DANGER: This hangs the script, powered, forever! debug=True isn't for unattended use.
                    # Would be nice to have a timeout on the prompt, but that's complicated with threads and queues. Maybe a lab_utils project for a rainy day.
                    if input('Debug [y/n]? ').lower() in ('y', 'yes'):
                        # pdb.set_trace()
                        pdb.post_mortem()
                    else:
                        if input('GUI [y/n]? ').lower() in ('y','yes'):
                            self.get_logger().gui()
                        else:
                            # Just crash. No sense in carrying on with other tests in the regression.
                            raise e
                self._crashed = sys.exc_info()
            else:
                #test ran!
                pass
            finally:
                try:
                    self._restore()
                except Exception as e:
                    # Not much to be done if this crashes.
                    # Press on trying to clean up!
                    print(e)
                self._lab_bench.cleanup() # This might crash. If so, best effort (inside temptroller) to clean up oven and stop all tests - no sense running other tests with broken bench.
        else:
            print(f"Skipping previously crashed test: {self.get_name()}")
    @abc.abstractmethod
    def collect(self, channels, debug):
        '''perform data collection at a single temperature.'''
    def _plot(self, table_name=None, db_file=None, skip_output=False):
        '''get database loaded up first to streamline test module'''
        '''skip output to facilitate replotting to different location wihtout having to p4 check out everything. requires argument support inside each test, which no legacy tests have yet'''
        if self._crashed is not None:
            print(f'Skipping plotting for crashed test: {self.get_name()}.')
            return []
        else:
            if table_name is None:
                tn = self.get_db_table_name()
                plot_filepath = self._module_path
            else:
                tn = table_name
                plot_filepath = os.path.join(self._module_path, table_name)
            tn_base = tn
            if db_file is None:
                # db = self.get_db()
                db = sqlite_data(database_file=self._db_file, table_name=tn)
            else:
                db = sqlite_data(database_file=db_file, table_name=tn) 
                (db_root, db_filename) = os.path.split(os.path.abspath(db_file))
                if table_name is None:
                    plot_filepath = db_root
                else:
                    plot_filepath = os.path.join(db_root, table_name)
            if f'{tn}_all' in db.get_table_names():
                #If there aren't any presets or formats, the _all view never gets created by PyICe
                tn = f'{tn}_all' #Redirect to presets-joined table
                db.set_table(tn)
            self.hook_functions('tm_plot', tn, db, plot_filepath)
            try:
                plts = self.plot(database=db, table_name=tn, plot_filepath=plot_filepath, skip_output=skip_output)
            except TypeError as e:
                #skip_output argument not supported by legacy script
                print(f'WARNING: Test {self.get_name()} plot method does not support skip_output argument.')
                try:
                    plts = self.plot(database=db, table_name=tn, plot_filepath=plot_filepath)
                except Exception as e:
                    # Something else, NOS, has gone wrong with plotting. Let's try to muddle through it to avoid interrupting the other plots and still give a chance of archiving.
                    if self._debug:
                        traceback.print_exc()
                        if input('Debug [y/n]? ').lower() in ('y', 'yes'):
                            pdb.post_mortem()
                        else:
                            # Just crash. No sense in carrying on with other tests in the regression.
                            raise e
                    self._plot_crashed = sys.exc_info()
                    plts = []
            except Exception as e:
                # Something else, NOS, has gone wrong with plotting. Let's try to muddle through it to avoid interrupting the other plots and still give a chance of archiving.
                if self._debug:
                    traceback.print_exc()
                    if input('Debug [y/n]? ').lower() in ('y', 'yes'):
                        pdb.post_mortem()
                    else:
                        # Just crash. No sense in carrying on with other tests in the regression.
                        raise e
                self._plot_crashed = sys.exc_info()
                plts = []
            def convert_svg(plot):
                if isinstance(plot, LTC_plot.plot):
                    page = LTC_plot.Page(rows_x_cols = None, page_size = None, plot_count = 1)
                    page.add_plot(plot=plot)
                    return page.create_svg(file_basename=None, filepath=None)
                elif isinstance(plot, LTC_plot.Page):
                    return plot.create_svg(file_basename=None, filepath=None)
                elif isinstance(plot, (str,bytes)):
                    # Assume this is already SVG source.
                    # TODO: further type checking?
                    return plot
                else:
                    raise Exception(f'Not sure what this plot is:\n{type(plot)}\n{plot}')
            if plts is None:
                print(f'WARNING: {self.get_name()} failed to return plots.')
                return []
            elif isinstance(plts, (LTC_plot.plot, LTC_plot.Page)):
                return [convert_svg(plts)]
            elif isinstance(plts, (str,bytes)):
                return [plts]
            else:
                assert isinstance(plts, list)
                return [convert_svg(plt) for plt in plts]
    @abc.abstractmethod
    def plot(self, database, table_name, plot_filepath, skip_output):
        '''output plot from previously stored data. Static method prevents logger/instrument creation. what about self.name???
        return list of svg sources???'''

    #@typing.final
    def reconfigure(self, channel, value):
        '''save channel settings specific to a particular test. Unwound after test at each temperature.'''
        self._channel_reconfiguration_settings.append((channel, channel.read(), value))
    #@typing.final
    def _reconfigure(self):
        '''save channel setting before writing to value'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(new)
    #@typing.final
    def _restore(self):
        '''undo any changes made by reconfigure'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(old)
    #@typing.final
    def copy_table(self):
        #self.get_logger().copy_table(old_table=self.get_name(), new_table=self.get_name() + datetime.datetime.now().strftime("_%Y_%m_%d_%H_%M"))
        new_table_name = self.get_name() + self._start_time.strftime("_%Y_%m_%d_%H_%M_%S")
        self.get_logger().copy_table(old_table=self.get_name(), new_table=new_table_name) #Needs to have been through a _setup()!
        self._archive_table_name = new_table_name
        # Remove Excel output, per Steve fear of encouraging Excel usage.
        # self.export_table_xlsx(filename=f'{new_table_name}.xlsx')
        return new_table_name
    #@typing.final
    def export_table_xlsx(self, filename):
        self.get_db().xlsx(output_file=filename, elapsed_time_columns=True)
    #@typing.final
    def get_logger(self):
        if self._logger is None:
            raise Exception('No Logger setUp.')
        return self._logger
    #@typing.final
    def get_db(self):
        return sqlite_data(database_file=self._db_file, table_name=self.get_name())
    def get_db_table_name(self):
        return self.get_name()
    def get_lab_bench(self):
        # raise Exception('Is this really needed?')
        #TODO What if the lab_bench doesn't exist yet? Exception?
        return self._lab_bench

    @classmethod
    def run(cls, collect_data, temperatures=None, debug=False, lab_bench_constructor=None):
        tt = temptroller(temperatures=temperatures, debug=debug)
        # tt = cls._get_project_temptroller(cls, temperatures=temperatures, debug=debug)
        if lab_bench_constructor is not None:
            tt.set_lab_bench_constructor(lab_bench_constructor)
        tt.add_test(cls)
        tt.run(collect_data)
    @classmethod
    def run_repeatability(cls, repeat_count, temperatures=None, debug=False, lab_bench_constructor=None):
        tt = temptroller(temperatures=temperatures, debug=debug)
        if lab_bench_constructor is not None:
            tt.set_lab_bench_constructor(lab_bench_constructor)
        tt.add_test(cls, repeat_count=repeat_count)
        tt.run(collect_data=True)
        self.hook_functions('tm_post_repeatability')
        html_plotter = cls.replotter()
        for test_run in tt:
            html_plotter.add_test_run(test_class=type(test_run), table_name=test_run.get_db_table_name(), db_file=test_run._db_file)
        html_plotter.write_html('repeatability_summary.html') #TODO check permissions?
        # TODO collect up data, present repeatability summary statistics, differentiate plotting, ...
        # As a fist step, this just runs the test multiple times to see if it crashes, but not more.
        #TODO write out special JSON file to preserve results????
    def is_crashed(self):
        return bool(self._crashed)
    def crash_info(self):
        if self._crashed is None:
            return ''
        else:
            # (type, value, trace_bk) = self._crashed
            (typ, value, trace_bk) = self._crashed
            crash_str = f'Test: {self.get_name()} crashed: {typ},{value}\n'
            crash_sep = '==================================================\n'
            crash_str += crash_sep
            # crash_str += f'{traceback.print_tb(trace_bk)}\n'
            crash_str += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
            crash_str += crash_sep
            return crash_str
    def _add_db_indices(self, table_name=None, db_file=None):
        if table_name is None:
            table_name = self.get_db_table_name()
        if db_file is None:
            db_file = self._db_file
        for column_list in self._column_indices:
            self.__add_db_indices(column_list=column_list, table_name=table_name, db_file=db_file)
    def __add_db_indices(self, column_list, table_name, db_file):
        '''recursively callable on db errors'''
        db = sqlite_data(database_file=db_file, table_name=table_name)
        columns_str = f'({",".join(column_list)})'
        idx_name = f'{table_name}_{"_".join(column_list)}_idx'
        try:
            db.conn.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} {columns_str}')
            db.conn.commit()
        except sqlite3.OperationalError as e:
            # "no such column: foo"
            
            # sqlite3.OperationalError: no such column: foo
            
            
            missing_col_mat = re.match('no such column: (?P<missing_col>\w+)', str(e)) #alphanumeric column names only? prob ok.
            if missing_col_mat is not None:
                missing_col = missing_col_mat.group("missing_col")
                column_list = list(column_list) #could be tuple!
                column_list.remove(missing_col)
                print(f'WARNING: {idx_name} database index specifies missing column {missing_col}. Trying again without it.')
                if len(column_list):
                    #try again with fewer columns...
                    self.__add_db_indices(column_list=column_list, table_name=table_name, db_file=db_file)
                else:
                    print(f'{idx_name} empty residual column list. Aborting.')
            else:
                print(e)
                print('This is unexpected. Please email trace above to Dave')
                breakpoint()
                #Not sure what might go wrong here without more testing. Write locks? TBD...
                pass
    def register_db_index(self, column_list):
        self._column_indices.append(column_list)
    @classmethod
    def plot_from_table(cls, table_name=None, db_file=None, debug=False):
        self = cls(debug=debug)
        with sqlite_data(database_file=db_file, table_name=table_name) as db:
            my_bench = db.query(f'SELECT bench FROM {table_name}').fetchone()['bench']
        self.bench_name=my_bench[my_bench.find('benches')+8:my_bench.find("' from")]
        self.hook_functions('tm_plot_from_table', table_name, db_file)
        plts = self._plot(table_name=table_name, db_file=db_file)
        if self._plot_crashed is not None:
            (typ, value, trace_bk) = self._plot_crashed
            msg = f'{self.get_name()} plot crash!.\n'
            msg += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
            # Skipping the "moving on" here on replotting (vs after collection) since it doesn't affect archive, etc.
            # print(notify_message)
            raise Exception(msg)
        if plts is None:
            plts = []
        else:
            assert isinstance(plts, list), "Plot method should return a list of plot objects. See Dave"
        # for tst in self._test_results:                                                                    ### Hey Dave, what is this for?     --RHM
            # for data_group in self._test_results._test_results[tst]:
                # for tst_plt in data_group.plot:
                    # # TODO, there's only one plot inside the first entry now.
                    # # Structure this whole mess better eventually to account for the iterable results data groups.
                    # plts.append(tst_plt)
        return plts


class multitest_module(test_module):
    '''class template
    all test modules shall inherit from this class and implement these abstract methods.
    '''
    _is_multitest_module = True
    def __init__(self, debug=False):
        self._multitest_units = []
        self.add_multitest_units()
        super().__init__(debug)
    @abc.abstractmethod
    def add_multitest_units(self):
        '''Implement with repeated calls to self.add_multitest_unit(multitest_unit_class)'''
    def add_multitest_unit(self, multitest_unit_class):
        self._multitest_units.append(multitest_unit_class(parent_module=self))
        # Perforce checks?? Here or in setup?
    def register_tests(self):
        '''todo docs'''
        for multitest_unit in self._multitest_units:
            multitest_unit.register_tests()
            #TODO collect return value?
    def _add_attr(self,key,value):
        setattr(self,key,value)
        for multitest_unit in self._multitest_units:
            setattr(multitest_unit,key,value)
    def _execute_plugin_fns(self, func):
        for multitest_unit in self._multitest_units:
            func(multitest_unit)
    # def plot(self, database, table_name, plot_filepath, db_file=None, skip_output=False):
    def plot(self, database, table_name, plot_filepath, skip_output=False):
        '''output plot from previously stored data. Static method prevents logger/instrument creation. what about self.get_name()???
        return list of svg sources???'''
        plts = []
        for multitest_unit in self._multitest_units:
            if plot_filepath == self._module_path:
                pfp = multitest_unit._module_path
            elif self._archive_enabled:
                pfp = plot_filepath
            else:
                print("Russell failed to forsee this possibility. Please tell him what you did to get here.")
                breakpoint()
            # if db_file is not None: #Archive!
                # # Plotting non-standard db file
                # # Just accept filepath that came in, for lack of a better behavior spec
                # # This puts plots together with database/table/module name rather than in specific multitest locations
                # # ...which might just be the right thing to do?
                # # TODO revisit later!
                # pfp = plot_filepath
            # elif table_name == self.get_name():
                # # Normal
                # pfp = multitest_unit._module_path
            # else: #elif db_file is None:                          ## RUSSELL ISN'T SURE WHAT THIS WAS TO CATCH, AND SO DOESN'T KNOW HOW TO REPLACE IT IN THIS SIMPLIFIED MODEL! 04/11/2023
                # # Plotting non-standard table
                # pfp = os.path.join(multitest_unit._module_path, table_name)
            try:
                unit_plts = multitest_unit.plot(database, table_name, plot_filepath=pfp, skip_output=skip_output) #Ignore multitest_module location. Place plot in multitest_unit location.
            except TypeError as e:
                #skip_output argument not supported by legacy script
                print(f'WARNING: Multitest {self.get_name()} unit {multitest_unit.get_name()} plot method does not support skip_output argument.')
                unit_plts = multitest_unit.plot(database, table_name, plot_filepath=pfp) #Ignore multitest_module location. Place plot in multitest_unit location.
            if isinstance(unit_plts, (str,bytes)):
                unit_plts = [unit_plts]
            elif unit_plts is None:
                print(f'WARNING: {self.get_name()} module returned no plots.')
                continue
            assert isinstance(unit_plts, list), f'Multitest module {self.get_name()} expected plot list, but got {type(unit_plts)}.'
            plts.extend(unit_plts)
        return plts
    def compile_test_results(self, database, table_name):
        '''inspect previously collected data. Check against parametic limits or functional specification to return Pass/Fail aggregated result.'''
        for multitest_unit in self._multitest_units:
            multitest_unit.compile_test_results(database, table_name)
            #TODO collect return value?
        # need to create and return an instance of sweep_results()

class multitest_unit(abc.ABC):
    '''class template
    all test modules shall inherit from this class and implement these abstract methods.
    '''
    def __init__(self, parent_module):
        self._parent_module = parent_module
        (self._module_path, file) = os.path.split(inspect.getsourcefile(type(self)))
        # self._plot_crashed = None Maybe some day make multitest unit crashed independent. TBD!
        # For now, the crash recovery and reporting works, but the first unit to crash will prevent execution of the others, resulting in a possibly iterative debug.
    def get_name(self):
        return type(self).__name__
    def get_revid(self):
        try:
            return self._parent_module._revid # only set after self._get_die_traceability_hash
        except AttributeError as e:
            print('Problem retrieving revid information. Ask Dave for help')
            return -1 #???
    def get_variant_id(self):
        try:
            return self._parent_module._variant_id # only set after self._get_die_traceability_hash
        except AttributeError as e:
            print('Problem retrieving variant id information. Ask Dave for help')
            return -1 #???
    def debug_mode(self):
        '''query to see if module debug flag is set. useful where otherwise not provided as method argument, ex in setup().'''
        return bool(self._parent_module._debug)
    def get_die_traceability_hash_table(self):
        return self._parent_module._die_traceability_hash
    def get_correlation_data(self, REFID, temperature=None):
        return self._parent_module.get_correlation_data(REFID, temperature)
    def get_correlation_data_scalar(self, REFID, temperature):
        return self._parent_module.get_correlation_data_scalar(REFID, temperature)
    def get_test_limits(self, test_name):
        try:
            tst_decl = self._parent_module._test_results._test_declarations[test_name]
        except KeyError:
            tst_decl = self._parent_module._correlation_results._correlation_declarations[test_name]
        #test_declaration(test_name='CH0_VDROOP', requirement_reference=None, lower_limit=-0.15, upper_limit=0.15, description='CH0 droop due to load step', notes=None)
        return (tst_decl.lower_limit, tst_decl.upper_limit)
    @abc.abstractmethod
    def register_tests(self):
        '''enumerate measurments to be taken, limits, etc before writing test or collcting results
        make repeated calls to self.register_test_*()'''
    @abc.abstractmethod
    def plot(self, database, table_name, plot_filepath, skip_output):
        '''output plot from previously stored data. Static method prevents logger/instrument creation. what about self.name???
        return list of svg sources???
        if skip_output, return svg source without writing to files'''
    @abc.abstractmethod
    def compile_test_results(self, database, table_name):
        '''inspect previously collected data. Check against parametic limits or functional specification to return Pass/Fail aggregated result.'''

    def _add_attr(self,key,value):
        setattr(self,key,value)

