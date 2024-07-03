from PyICe.bench_configuration_management.bench_configuration_management import component_collection, connection_collection
from PyICe.bench_configuration_management import bench_visualizer
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe import virtual_instruments, lab_utils
from PyICe.lab_utils.banners import print_banner
from PyICe.plugins import test_archive
from PyICe.lab_core import logger
from PyICe import lab_core, LTC_plot
import os, inspect, importlib, datetime, socket, traceback, sys, cairosvg
from email.mime.image import MIMEImage


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

class Plugin_Manager():
    def __init__(self, debug=False):
        self._debug = debug
        self.tests = []
        self.operator = os.getlogin().lower()
        self.thismachine = socket.gethostname().replace("-","_")

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
            if 'notifications' in self.used_plugins:
                self._find_notifications(a_test._project_path)
        a_test._is_crashed = False

    def run(self, temperatures=[]):
        '''This method goes through the complete data collection process the project set out. Scripts will be run once per temperature or just once if no temperature is given. Debug will be passed on to the script to be used at the script's discretion.'''
        self.collect(temperatures, self._debug)
        self.plot()
        if 'evaluate_tests' in self.used_plugins:
            self.evaluate()
        if 'correlate_tests' in self.used_plugins:
            self.correlate()
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
        Drivers should return a dictionary with needed key 'instruments', which returns a list of channels and channel objects to be added to the master, and optional keys 'cleanup functions', 'temp_control_channel' ,and 'special_channel_action'.
        The value for "cleanup functions" is a list of functions that put the instruments in safe states once the test is complete.
        The cleanup functions are run in the order in which the instruments appear in the bench file.
        The special channel actions are functions that are run on each logging of data and the value is a dicionary with a channel object or the string name of a channel as key, and the value the function to be run. The function requires the arguments channel_name, readings, and test.'''

        self.cleanup_fns = []
        self.temperature_channel = None
        self.special_channel_actions = {}
        
        for (dirpath1, dirnames, filenames) in os.walk(self._project_path):
            if 'benches' not in dirpath1 or self._project_path not in dirpath1: continue
            try:
                benchpath = dirpath1.replace('\\', '.')
                benchpath = benchpath[benchpath.index(self._project_path.split('\\')[-1]):]
                module = importlib.import_module(name=benchpath+'.'+self.thismachine, package=None)
                break
            except ImportError as e:
                print(e)
                raise Exception(f"Can't find bench file {self.thismachine}. Note that dashes must be replaced with underscores.")
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
        if hasattr(test, 'customize'):
            test.customize()
        test._logger.new_table(table_name=test.name, replace_table=True)
        test._logger.write_html(file_name=test.project_folder_name+'.html')

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
    # NOTIFICATION METHODS
    ###
    def notify(self, msg, subject=None, attachment_filenames=[], attachment_MIMEParts=[]):
        if 'notifications' in self.used_plugins:
            if not self._debug:
                try:
                    for fn in self._notification_functions:
                        try:
                            fn(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
                        except TypeError:
                            # Function probably doesn't accept subject or attachments
                            try:
                                fn(msg)
                            except Exception as e:
                                # Don't let a notiffication crash a more-important cleanup/shutdown.
                                print(e)
                        except Exception as e:
                            # Don't let a notiffication crash a more-important cleanup/shutdown.
                            print(e)
                except AttributeError as e:
                    if not len(attachment_filenames) and not len(attachment_MIMEParts):
                        print(msg)
            else:
                if not len(attachment_filenames) and not len(attachment_MIMEParts):
                    print(msg)
    def _find_notifications(self, project_path):
        self._notification_functions = []
        for (dirpath, dirnames, filenames) in os.walk(project_path):
            if self.operator+'.py' in filenames: 
                usernotificationpath = dirpath.replace('\\', '.')
                usernotificationpath = usernotificationpath[usernotificationpath.index(project_path.split('\\')[-1]):]
                module = importlib.import_module(name=usernotificationpath+f'.{self.operator}', package=None)
                module.init(test_manager=self)
    def add_notification(self, fn):
        self._notification_functions.append(fn)
    def _convert_svg(self, plot):
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
    def email_plots(self, plot_svg_source):
        msg_body = ''
        attachment_MIMEParts=[]
        for (i,plot_src) in enumerate(plot_svg_source):
            plot_png = cairosvg.svg2png(bytestring=plot_src)
            plot_mime = MIMEImage(plot_png, 'image/png')
            plot_mime.add_header('Content-Disposition', 'inline')
            plot_mime.add_header('Content-ID', f'<plot_{i}>')
            msg_body += f'<img src="cid:plot_{i}"/>'
            attachment_MIMEParts.append(plot_mime)
        self.notify(msg_body, subject='Plot Results', attachment_MIMEParts=attachment_MIMEParts)
    def crash_info(self, test):
        (typ, value, trace_bk) = test._crash_info
        crash_str = f'Test: {test.name} crashed: {typ},{value}\n'
        crash_sep = '==================================================\n'
        crash_str += crash_sep
        # crash_str += f'{traceback.print_tb(trace_bk)}\n'
        crash_str += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
        crash_str += crash_sep
        return crash_str

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
    # CORRELATION METHODS
    ###
    def correlate_test_result(self, test, name, data, conditions=None):
        pass
    def get_corr_results(self, test):
        pass
    ###
    # ARCHIVE METHODS
    ###
    def _archive(self):
        '''Makes a copy of the data just collected and puts it and the associated metatable (if there is one) in an archive folder. Also adds a copy of the table (and metatable) to the database with the time of collection to the test's generic database, so it will not be overwritten when the test is next run.'''
        print_banner('Archiving. . .')
        try:
            archive_folder = self.tests[0].get_archive_folder_name()
        except AttributeError:
            archive_folder = datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M")
        archived_tables = []
        for test in self.tests:
            archiver = test_archive.database_archive(db_source_file=test._db_file)
            if not archiver.has_data(tablename=test.name):
                print(f'No data logged for {test.name}. Skipping archive.')
                return
            if test._is_crashed:
                this_archive_folder = archive_folder + '_CRASHED'
            else:
                this_archive_folder = archive_folder
            db_dest_file = archiver.compute_db_destination(this_archive_folder)
            archiver.copy_table(db_source_table=test.name, db_dest_table=test.name, db_dest_file=db_dest_file)
            archiver.copy_table(db_source_table=test.name+'_metadata', db_dest_table=test.name+'_metadata', db_dest_file=db_dest_file)
            test._logger.copy_table(old_table=test.name, new_table=test.name+'_'+archive_folder)
            test._logger.copy_table(old_table=test.name+'_metadata', new_table=test.name+'_'+archive_folder+'_metadata')
            archived_tables.append((test, test.name, db_dest_file))
            # test._add_db_indices(table_name=test.name, db_file=db_dest_file)
        if len(archived_tables):
            arch_plot_scripts = []
            for (test, db_table, db_file) in archived_tables:
                dest_file = os.path.join(os.path.dirname(db_file), f"replot_data.py")
                import_str = test._module_path[test._module_path.index(test.project_folder_name):].replace('\\','.')
                plot_script_src = "if __name__ == '__main__':\n"
                plot_script_src += f"    from PyICe.plugins.plugin_manager import plugin_manager\n"
                plot_script_src += f"    from {import_str}.test import test\n"
                plot_script_src += f"    pm = plugin_manager()\n"
                plot_script_src += f"    pm.add_test(test)\n"
                plot_script_src += f"    pm.plot(database='data_log.sqlite', table_name='{test.name}')\n"
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
                plot_script_src += f"    from PyICe.plugins.plugin_manager import plugin_manager\n"
                plot_script_src += f"    from {import_str}.test import test\n"
                plot_script_src += f"    pm = plugin_manager()\n"
                plot_script_src += f"    pm.add_test(test)\n"
                plot_script_src += f"    pm.evaluate(database='data_log.sqlite', table_name='{test.name}')\n"
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
        self.master = lab_core.master()
        self.add_instrument_channels()
        if 'bench_config_management' in self.used_plugins:
            self.test_components =component_collection()
            self.test_connections = connection_collection(name="test_connections")
        for test in self.tests:
            test._channel_reconfiguration_settings=[]
            self._create_logger(test)
            if 'bench_config_management' in self.used_plugins:
                try:
                    test._declare_bench_connections()
                except Exception as e:
                    raise("TEST_MANAGER ERROR: This project indicated bench configuration data would be stored. Test template requires a _declare_bench_connections method that gathers the data.")
            if 'traceability' in self.used_plugins:
                self._create_metalogger(test)
                if 'bench_config_management' in self.used_plugins:
                    test.traceability_items.get_traceability_data()['bench_connections'] = self.test_connections.get_readable_connections()
                    test._metalogger.add_channel_dummy('bench_connections')
                    test._metalogger.write('bench_connections', self.test_connections.get_readable_connections())
                self._metalog(test)
        if 'bench_config_management' in self.used_plugins and self.verbose:
            print(self.test_connections.print_connections())
        if 'bench_image_creation' in self.used_plugins:
            visualizer = bench_visualizer.visualizer(connections=self.test_connections.connections, locations=test.get_bench_image_locations())
            visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')
        summary_msg = f'{self.operator} on {self.thismachine}\n'
        if not len(temperatures):
            for test in self.tests:
                test.debug=debug
                summary_msg += f'\t* {test.name}*\n'
                if not test._is_crashed:
                    try:
                        # test.test_timer.resume_timer()
                        self._reconfigure(test)
                        test.collect()
                        self._restore(test)
                    except (Exception, BaseException) as e:
                        traceback.print_exc()
                        test._is_crashed = True
                        test._crash_info = sys.exc_info()
                        self.notify(self.crash_info(test), subject='CRASHED!!!')
                    self.cleanup()
        else:
            assert self.temperature_channel != None
            for temp in temperatures:
                print_banner(f'Setting temperature to {temp}')
                self.temperature_channel.write(temp)
                for test in self.tests:
                    if not test._is_crashed:
                        try:
                            print_banner(f'Starting {test.name} at {temp}C')
                            # test.test_timer.resume_timer()
                            self._reconfigure(test)
                            test.collect(test._logger, debug)
                            self._restore(test)
                        except (Exception, BaseException) as e:
                            traceback.print_exc()
                            test._is_crashed = True
                            test._crash_info = sys.exc_info()
                            self.notify(test._crash_info, subject='CRASHED!!!')
                        self.cleanup()
                if all([x._is_crashed for x in self.tests]):
                    print_banner('All tests have crashed. Skipping remaining temperatures.')
                    break
        self.close_ports()
    def plot(self, database=None, table_name=None, plot_filepath=None):
        '''Run the plot method of each test in self.tests.'''
        self._plots=[]
        for test in self.tests:
            if not hasattr(test, 'plot'):
                continue
            print_banner(f'{test} Plotting. . .')
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
            plts = test.plot()
            if plts is None:
                print(f'WARNING: {self.get_name()} failed to return plots.')
                plts = []
            elif isinstance(plts, (LTC_plot.plot, LTC_plot.Page)):
                plts = [self._convert_svg(plts)]
            elif isinstance(plts, (str,bytes)):
                plts = [plts]
            else:
                assert isinstance(plts, list)
                plts = [self._convert_svg(plt) for plt in plts]
            self._plots.extend(plts)
            print_banner(f'Plotting for {test.name} complete.')
        if len(self._plots): #Don't send empty emails
            self.email_plots(self._plots)
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
            test.evaluate_results()
            if test._test_results._test_results:
                print(self.get_test_results(test))
                self.notify(self.get_test_results(test), subject='Test Results')
            elif self.verbose:
                print(f'No results submitted for {test.name}.')
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
            test.correlate_results()
            print(test.get_test_results())
            t_r = test._corr_results.json_report()
            dest_abs_filepath = os.path.join(os.path.dirname(database),f"correlation_results.json")
            if t_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(t_r.encode('utf-8'))
                    f.close()

