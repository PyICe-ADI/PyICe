from PyICe.bench_configuration_management.bench_configuration_management import component_collection, connection_collection
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.plugins.bench_maker import Bench_maker
from PyICe import virtual_instruments, lab_utils
from PyICe.lab_utils.banners import print_banner
from PyICe.plugins import test_archive
import os, importlib, datetime

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
        if len(self.tests) == 1:
            self._project_path = a_test._project_path
            try:
                self.verbose = a_test.verbose
            except Exception:
                self.verbose = True
            self.find_plugins(a_test)
        a_test._is_crashed = False

    def run(self, temperatures, debug):
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


            ## THERE WILL BE MORE POST-COLLECT PLUGINS


    def collect(self, temperatures, debug):
        '''This method aggregates the channels that will be logged and calls the collect method in every test added via self.add_test over every temperature indicated via argument. If debug is set to True, this will be passed on to the script. This variable can be used in scripts to trigger shorter loops or fewer conditions under which to gather data to verify script completeness.'''
        self.this_bench = Bench_maker(self._project_path)
        self.this_bench.make_bench()
        for test in self.tests:
            test._create_logger(self.this_bench.master, self.this_bench.special_channel_actions)
            if 'bench_config_management' in self.used_plugins: # TODO will bomb if no used_plugins list
                test_components =component_collection()
                test_connections = connection_collection(name="test_connections")
                test._declare_bench_connections(test_components, test_connections)
            if 'traceability' in self.used_plugins:
                test._create_metalogger()
                if 'bench_config_management' in self.used_plugins:
                    test.traceability_items.get_traceability_data()['bench_connections'] = test_connections.get_readable_connections()
                    test._metalogger.add_channel_dummy('bench_connections')
                    test._metalogger.write('bench_connections', test_connections.get_readable_connections())
                test._metalog()
        if not len(temperatures):
            for test in self.tests:
                test.debug=debug
                if not test._is_crashed:
                    try:
                        test.test_timer.resume_timer()
                        test._reconfigure()
                        test.collect()
                        test._restore()
                    except Exception as e:
                        print(e)
                        test._is_crashed = True
        else:
            assert self.this_bench.temperature_channel != None
            for temp in temperatures:
                print_banner(f'Setting temperature to {temp}')
                self.this_bench.temperature_channel.write(temp)
                for test in self.tests:
                    if not test._is_crashed:
                        try:
                            print_banner(f'Starting {test.name}')
                            test.test_timer.resume_timer()
                            test._reconfigure()
                            test.collect(test._logger, debug)
                            test._restore()
                        except Exception as e:
                            print(e)
                            test._is_crashed = True
                if all([x._is_crashed for x in self.tests]):
                    print_banner('All tests have crashed. Skipping remaining temperatures.')
                    break
        self.cleanup()

    def cleanup(self):
        """Release the instruments from bench control."""
        for func in self.this_bench.cleanup_fns:
            func()
        delegator_list = [ch.resolve_delegator() for ch in self.this_bench.master]
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
            print(test.get_test_results())
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
