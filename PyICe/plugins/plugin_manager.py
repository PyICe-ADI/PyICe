from PyICe.plugins.bench_maker import Bench_maker
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.lab_utils.banners    import print_banner
import os
import importlib

class plugin_manager():
    def __init__(self):
        self.tests = []
        self.used_plugins=[]

    def find_plugins(self, a_test):
        '''This is called the first time a test is added to the plugin manager. An instance of a test is needed to locate the project path. This facilitates users starting from an individual test and getting all the chosen plugins.'''
        for (dirpath, dirnames, filenames) in os.walk(a_test._project_path):
            if 'plugins_registry.py' not in filenames: 
                continue
            pluginpath = dirpath.replace('\\', '.')
            pluginpath = pluginpath[pluginpath.index(a_test._project_path.split('\\')[-1]):]
            module = importlib.import_module(name=pluginpath+'.plugins_registry', package=None)
            self.used_plugins = module.get_plugins()
            if self.verbose:
                for plugin in self.used_plugins:
                    print_banner(f'PYICE PLUGIN_MANAGER: Plugin found {plugin}')
            break

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
        if 'plotting' in self.used_plugins:
            self.plot()
        if 'evaluate_tests' in self.used_plugins:
            self.evaluate()
            
            
            ## THERE WILL BE MORE POST-COLLECT PLUGINS
            
            
    def collect(self, temperatures, debug):
        '''This method aggregates the channels that will be logged and calls the collect method in every test added via self.add_test over every temperature indicated via argument. If debug is set to True, this will be passed on to the script. This variable can be used in scripts to trigger shorter loops or fewer conditions under which to gather data to verify script completeness.'''
        self.this_bench = Bench_maker(self._project_path)
        self.this_bench.make_bench()
        for test in self.tests:
            test._create_logger(self.this_bench.master, self.this_bench.special_channel_actions)
            if 'bench_config_management' in self.used_plugins:
                pass
            if 'traceability' in self.used_plugins:
                test._create_metalogger()
                if 'bench_config_management' in self.used_plugins:
                    # somehow add the readable connection to the metalogger
                    pass
                test._metalog()
        if not len(temperatures):
            for test in self.tests:
                if not test._is_crashed:
                    try:
                        test._reconfigure()
                        test.collect(test._logger, debug)
                        test._restore()
                    except Exception:
                        test._is_crashed = True
                    print('\n\nAhoy hoy!\n\n')
        else:
            assert self.this_bench.temperature_channel != None
            for temp in temperatures:
                print_banner(f'Setting temperature to {temp}')
                self.this_bench.temperature_channel.write(temp)
                for test in self.tests:
                    if not test._is_crashed:
                        try:
                            print_banner(f'Starting {test.name}')
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
                table_name = test.name
            if plot_filepath is None:
                plot_filepath = test._module_path + '\\plots'
            db = sqlite_data(database_file=database, table_name=table_name)
            test.plot(db, table_name, plot_filepath)

    def evaluate(self, database=None, table_name=None):
        '''Run the evaluate method of each test in self.tests.'''
        print_banner('Evaluating. . .')
        for test in self.tests:
            if database is None:
                database = test._db_file
            if table_name is None:
                table_name = test.name
            db = sqlite_data(database_file=database, table_name=table_name)
            test.evaluate_results(db, table_name)
