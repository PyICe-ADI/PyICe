from PyICe.bench_configuration_management.bench_configuration_management import component_collection, connection_collection
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe import virtual_instruments, lab_utils
from PyICe.lab_utils.banners import print_banner
from PyICe.plugins import test_archive
from PyICe.lab_core import logger
from PyICe import lab_core
import os, inspect, importlib, datetime, socket
# import types
class Callback_logger(logger):
    '''Wrapper for the standard logger. Used to perform special actions for specific channels on a per-log basis.'''
    def __init__(self, database, special_channel_actions, test):
        super().__init__(database = database)
        self.sp_ch_actions = special_channel_actions
        self.test = test

    def log(self):
        readings = super().log()
        for channel, action in self.sp_ch_actions.items():
            action(channel, readings, self.test)
        return readings

class plugin_manager():
    def __init__(self):
        self.tests = []

    def find_plugins(self, a_test):
        '''This is called the first time a test is added to the plugin manager. An instance of a test is needed to locate the project path. This facilitates users starting from an individual test and getting all the chosen plugins.'''
        for (dirpath, dirnames, filenames) in os.walk(a_test._project_path):
            if 'plugins_registry.py' in filenames: 
                pluginpath = dirpath.replace('\\', '.')
                pluginpath = pluginpath[pluginpath.index(a_test._project_path.split('\\')[-1]):]
                module = importlib.import_module(name=pluginpath+'.plugins_registry', package=None)
                self.used_plugins = module.get_plugins()
                if self.verbose:
                    for plugin in self.used_plugins:
                        print_banner(f'PYICE PLUGIN_MANAGER Plugin found: "{plugin}".')

    def add_test(self, test):
        '''Adds a script to the list that will be operated on. If this is the first time a test is added to this instance of plugin manager, plugin manager also takes this opportunity to acquire global data from the project.'''
        a_test = test() 
        self.tests.append(a_test)
        a_test.pm=self

        (a_test._module_path, file) = os.path.split(inspect.getsourcefile(type(a_test)))
        a_test.name = a_test._module_path.split('\\')[-1]
        try:
            a_test._project_path = a_test._module_path[:a_test._module_path.index(a_test.project_folder_name)+len(a_test.project_folder_name)]
        except AttributeError as e:
            print_banner("PYICE TEST_MANAGER: User's test template requires an attribute 'project_folder_name' that names the project's topmost folder in order for this PyICe workflow to be able to find the project.")
        a_test._db_file = os.path.join(a_test._module_path, 'data_log.sqlite')
        
        if len(self.tests) == 1:
            self._project_path = a_test._project_path
            try:
                self.verbose = a_test.verbose
            except Exception:
                self.verbose = True
            self.find_plugins(a_test)
        a_test._is_crashed = False

    def run(self, temperatures=[], debug=False):
        '''This method goes through the complete data collection process the project set out. Scripts will be run once per temperature or just once if no temperature is given. Debug will be passed on to the script to be used at the script's discretion.'''
        self.collect(temperatures, debug)
        if hasattr(self, "used_plugins"):
            if 'plotting' in self.used_plugins:
                self.plot()
            if 'evaluate_tests' in self.used_plugins:
                self.evaluate()
            if 'archive' in self.used_plugins:
                self._archive()
        else:
            print_banner("No plugins registered, we're done here...")

    def add_instrument_channels(self):
        '''In this method, a master is populated by instruments and their channels.
        A file in the "benches" folder found anywhere under the head project folder should have the name of the computer associated with the current bench, and contains the get_instruments function.
        The name of the file should have underscores where the computer name may use dashes.
        Then, all the minidrivers are imported and the master is populated using the instruments from the bench file.
        The minidrivers (found in a "hardware_drivers" folder) define which instrument is expected and what channels names will be added for those instruments.
        The drivers also return "cleanup functions" that put the instruments in safe states once the test is complete.
        The cleanup functions are run in the order in which the instruments appear in the bench file.
        The special channel actions are functions that are run on each logging of data '''

        self.cleanup_fns = []
        self.temperature_channel = None
        self.special_channel_actions = {}
        thismachine = socket.gethostname().replace("-","_")
        for (dirpath1, dirnames, filenames) in os.walk(self._project_path):
            if 'benches' not in dirpath1 or self._project_path not in dirpath1: continue
            try:
                benchpath = dirpath1.replace('\\', '.')
                benchpath = benchpath[benchpath.index(self._project_path.split('\\')[-1]):]
                module = importlib.import_module(name=benchpath+'.'+thismachine, package=None)
                break
            except ImportError as e:
                print(e)
                raise Exception(f"Can't find bench file {thismachine}. Note that dashes must be replaced with underscores.")
        self.interfaces = module.get_interfaces()
        for (dirpath, dirnames, filenames) in os.walk(self._project_path):
            if 'hardware_drivers' not in dirpath: continue
            driverpath = dirpath.replace('\\', '.')
            driverpath = driverpath[driverpath.index(self._project_path.split('\\')[-1]):]
            for driver in filenames:
                driver_mod = importlib.import_module(name=driverpath+'.'+driver[:-3], package=None)
                
                # setattr(self, f'populate_{driver[:-3]}', types.MethodType(driver_mod.populate,self))
                # instrument_dict = getattr(self, f'populate_{driver[:-3]}')()

                instrument_dict = driver_mod.populate(self)
                
                if instrument_dict['instruments'] is not None:
                    for instrument in instrument_dict['instruments']:
                        self.master.add(instrument)
                    if 'cleanup_list' in instrument_dict:
                        for fn in instrument_dict['cleanup_list']:
                            self.cleanup_fns.append(fn)
                    if 'temp_control_channel' in instrument_dict:
                        if self.temperature_channel == None:
                            self.temperature_channel = instrument_dict['temp_control_channel']
                            temp_instrument = instrument_dict['instruments']
                        else:
                            raise Exception(f'BENCH MAKER: Multiple channels have been declared the temperature control! One from {temp_instrument} and one from {instrument_dict["instruments"]}.')
                    if 'special_channel_action' in instrument_dict:
                        overwrite_check = [i.get_name() for i in instrument_dict['special_channel_action'] if i in self.special_channel_actions]
                        if overwrite_check:
                            raise Exception(f'BENCH MAKER: Multiple actions have been declared for channel(s) {overwrite_check}.')
                        self.special_channel_actions.update(instrument_dict['special_channel_action'])
            break
        
        self.temperature_channel = self.master.add_channel_dummy('tdegc')
        self.temperature_channel.write(25)
    def _create_logger(self, test):
        test._logger = Callback_logger(database=test._db_file, special_channel_actions=self.special_channel_actions, test=test)
        test._logger.merge_in_channel_group(self.master.get_flat_channel_group())
        test.customize()
        test._logger.new_table(table_name=test.name, replace_table=True)

    def reconfigure(self,test, channel, value):
        '''Optional method used during customize() if changes are made to the DUT on a particular test in a suite. Unwound after test's collect at each temperature.'''
        test._channel_reconfiguration_settings.append((channel, channel.read(), value))
    def _reconfigure(self, test):
        '''save channel setting before writing to value'''
        for (ch, old, new) in test._channel_reconfiguration_settings:
            ch.write(new)
    def _restore(self, test):
        '''undo any changes made by reconfigure'''
        for (ch, old, new) in test._channel_reconfiguration_settings:
            ch.write(old)
    def cleanup(self):
        """Release the instruments from bench control."""
        for func in self.cleanup_fns:
            func()
    def close_ports(self):
        delegator_list = [ch.resolve_delegator() for ch in self.master]
        delegator_list = list(set(delegator_list))
        interfaces = []
        for delegator in delegator_list:
            for interface in delegator.get_interfaces():
                interfaces.append(interface)
        interfaces = list(set(interfaces))
        for iface in interfaces:
            try:
                iface.close()
            except AttributeError as e:
                pass
            except Exception as e:
                print(e)
        else:
            print_banner('Bench cleaned!')

    ###
    # TRACEABILITY METHODS
    ###
    def _create_metalogger(self, test):
        '''Called from the plugin_master if the 'traceability' plugin was included in the plugin_registry, this creates a master and logger separate from the test data logger, and populates them using user provided metadata gathering functions. '''
        _master = lab_core.master()
        test._metalogger = lab_core.logger(database=test._db_file)
        test._metalogger.add(_master)
        test.traceability_items = test._get_metadata_gathering_fns().get_traceability_items(test=test)
        test.traceability_items.populate_traceability_data()
        test.traceability_items.add_data_to_metalogger(test._metalogger)
    def _metalog(self, test):
        '''This is separate from the _create_metalogger method in order to give other plugins the opportunity to add to the metalogger before the channel list is commited to a table.'''
        test._metalogger.new_table(table_name=test.name+"_metadata", replace_table=True)
        test._metalogger.log()

    ###
    # EVALUATION METHODS
    ###
    def evaluate_test_result(self, test, name, data, conditions=None):
        '''TODO'''
        #data should be True/False or iterable.
        #Handle True/False here for functional tests, or pass through?
        test._test_results.test_info[name]=test.get_test_info(name)
        test._test_results._register_test_result(name=name, iter_data=data, conditions=conditions)
    def evaluate_test_query(self, test, name, value_column, grouping_columns=[], where_clause=''):
        grouping_str = ''
        for condition in grouping_columns:
            grouping_str += ','
            grouping_str += condition
        query_str = f'SELECT {value_column}{grouping_str} FROM {test.table_name} ' + ('WHERE' + where_clause if where_clause else '')
        test.db.query(query_str)
        self.evaluate_test_result(test, name, test.db)
    def get_test_results(self,test):
        res_str = ''
        all_pass = True
        res_str += f'*** Module {test.name} ***\n'
        res_str += f'{test._test_results}'
        res_str += f'*** Module {test.name} Summary {"PASS" if test._test_results else "FAIL"}. ***\n\n'
        return res_str

    ###
    # ARCHIVE METHODS
    ###
    def _archive(self):
        '''Makes a copy of the data just collected and puts it and the associated metatable (if there is one) in an archive folder. Also adds a copy of the table (and metatable) to the database with the time of collection to the test's generic database, so it will not be overwritten when the test is next run.'''
        print_banner('Archiving. . .')
        folder_suggestion = datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M")   ### Maybe have a method for users to provide a name?
        archive_folder = folder_suggestion
        archived_tables = []
        for test in self.tests:
            archiver = test_archive.database_archive(db_source_file=test._db_file)
            db_dest_file = archiver.compute_db_destination(archive_folder)
            archiver.copy_table(db_source_table=test.name, db_dest_table=test.name, db_dest_file=db_dest_file)
            archiver.copy_table(db_source_table=test.name+'_metadata', db_dest_table=test.name+'_metadata', db_dest_file=db_dest_file)
            test._logger.copy_table(old_table=test.name, new_table=test.name+'_'+folder_suggestion)
            test._logger.copy_table(old_table=test.name+'_metadata', new_table=test.name+'_'+folder_suggestion+'_metadata')
            archived_tables.append((test, test.name, db_dest_file))
            # test._add_db_indices(table_name=test.name, db_file=db_dest_file)
        if len(archived_tables):
            arch_plot_scripts = []
            for (test, db_table, db_file) in archived_tables:
                dest_file = os.path.join(os.path.dirname(db_file), f"replot_data.py")
                import_str = test._module_path[test._module_path.index(test.project_folder_name):].replace('\\','.')
                plot_script_src = "if __name__ == '__main__':\n"
                plot_script_src += f"    from {import_str}.test import test\n"
                plot_script_src += f"    test.plot_only(database='data_log.sqlite', table_name='{test.name}')\n"
                try:
                    with open(dest_file, 'a') as f: #exists, overwrite, append?
                        f.write(plot_script_src)
                except Exception as e:
                    #write locked? exists?
                    print(type(e))
                    print(e)
                
                dest_file = os.path.join(os.path.dirname(db_file), f"reeval_data.py")
                import_str = test._module_path[test._module_path.index(test.project_folder_name):].replace('\\','.')
                plot_script_src = "if __name__ == '__main__':\n"
                plot_script_src += f"    from {import_str}.test import test\n"
                plot_script_src += f"    test.evaluate_only(database='data_log.sqlite', table_name='{test.name}')\n"
                try:
                    with open(dest_file, 'a') as f: #exists, overwrite, append?
                        f.write(plot_script_src)
                except Exception as e:
                    #write locked? exists?
                    print(type(e))
                    print(e)

                arch_plot_scripts.append(dest_file)
                print_banner(f'Archiving for {test.name} complete.')

    ###
    # SCRIPT METHODS
    ###
    def collect(self, temperatures, debug):
        '''This method aggregates the channels that will be logged and calls the collect method in every test added via self.add_test over every temperature indicated via argument. If debug is set to True, this will be passed on to the script. This variable can be used in scripts to trigger shorter loops or fewer conditions under which to gather data to verify script completeness.'''
        # self.this_bench = Bench_maker(self._project_path)
        # self.this_bench.make_bench()
        self.master = lab_core.master()
        self.add_instrument_channels()
        for test in self.tests:
            test._channel_reconfiguration_settings=[]
            self._create_logger(test)
            if 'bench_config_management' in self.used_plugins: # TODO will bomb if no used_plugins list
                test_components =component_collection()
                test_connections = connection_collection(name="test_connections")
                try:
                    test._declare_bench_connections(test_components, test_connections)
                except Exception as e:
                    raise("TEST_MANAGER ERROR: This project indicated bench configuration data would be stored. Test template requires a _declare_bench_connections method that gathers the data.")
            if 'traceability' in self.used_plugins:
                self._create_metalogger(test)
                if 'bench_config_management' in self.used_plugins:
                    test.traceability_items.get_traceability_data()['bench_connections'] = test_connections.get_readable_connections()
                    test._metalogger.add_channel_dummy('bench_connections')
                    test._metalogger.write('bench_connections', test_connections.get_readable_connections())
                self._metalog(test)
        if not len(temperatures):
            for test in self.tests:
                test.debug=debug
                if not test._is_crashed:
                    try:
                        # test.test_timer.resume_timer()
                        self._reconfigure(test)
                        test.collect()
                        self._restore(test)
                    except Exception as e:
                        print(e)
                        test._is_crashed = True
                    self.cleanup()
        else:
            assert self.temperature_channel != None
            for temp in temperatures:
                print_banner(f'Setting temperature to {temp}')
                self.temperature_channel.write(temp)
                for test in self.tests:
                    if not test._is_crashed:
                        try:
                            print_banner(f'Starting {test.name}')
                            # test.test_timer.resume_timer()
                            self._reconfigure(test)
                            test.collect(test._logger, debug)
                            self._restore(test)
                        except Exception as e:
                            print(e)
                            test._is_crashed = True
                        self.cleanup()
                if all([x._is_crashed for x in self.tests]):
                    print_banner('All tests have crashed. Skipping remaining temperatures.')
                    break
        self.close_ports()
    def plot(self, database=None, table_name=None, plot_filepath=None):
        '''Run the plot method of each test in self.tests.'''
        print_banner('Plotting. . .')
        for test in self.tests:
            if database is None:
                database = test._db_file
            if table_name is None:
                test.table_name = test.name
            else:
                test.table_name=table_name
            if plot_filepath is None:
                test.plot_filepath = test._module_path + '\\plots'
            else:
                test.plot_filepath = plot_filepath
            test.db = sqlite_data(database_file=database, table_name=test.table_name)
            test.plot()
            print_banner(f'Plotting for {test.name} complete.')
    def evaluate(self, database=None, table_name=None):
        '''Run the evaluate method of each test in self.tests.'''
        from PyICe.plugins.test_results import test_results
        print_banner('Evaluating. . .')
        for test in self.tests:
            if database is None:
                database = test._db_file
            if table_name is None:
                test.table_name = test.name
            else:
                test.table_name = table_name
            test._test_results = test_results(test.name, module=test)
            test.db = sqlite_data(database_file=database, table_name=test.table_name)
            # test.evaluate_results(db, table_name)
            test.evaluate_results()
            print(self.get_test_results(test))
            t_r = test._test_results.json_report()
            dest_abs_filepath = os.path.join(os.path.dirname(database),f"test_results.json")
            if t_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(t_r.encode('utf-8'))
                    f.close()
    def correlate(self, database=None, table_name=None):
        '''Run the correlate method of each test in self.tests.'''
        from PyICe.plugins.test_results import test_results
        print_banner('Correlating. . .')
        for test in self.tests:
            if database is None:
                database = test._db_file
            if table_name is None:
                test.table_name = test.name
            else:
                test.table_name = table_name
            test._corr_results = test_results(test.name, module=test)
            test.db = sqlite_data(database_file=database, table_name=test.table_name)
            # test.evaluate_results(db, table_name)
            test.correlate_results()
            print(test.get_test_results())
            t_r = test._corr_results.json_report()
            dest_abs_filepath = os.path.join(os.path.dirname(database),f"correlation_results.json")
            if t_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(t_r.encode('utf-8'))
                    f.close()

