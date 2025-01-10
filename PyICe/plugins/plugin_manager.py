from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection, connection_collection
import os, inspect, importlib, datetime, socket, traceback, sys, json, getpass, contextlib, io
from PyICe.plugins.bench_configuration_management import bench_visualizer
from PyICe.plugins.traceability_items import Traceability_items
from PyICe.lab_utils.communications import email, sms
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.plugins.test_results import Test_Results
from PyICe.lab_utils.banners import print_banner
from PyICe.lab_core import logger, master
from PyICe.plugins import test_archive
from email.mime.image import MIMEImage
from PyICe import LTC_plot

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
    def __init__(self, scratch_folder='scratch'):
        self.tests = []
        self.operator = getpass.getuser().lower()
        self.thismachine = socket.gethostname().replace("-","_").split(".")[0]
        self.scratch_folder = scratch_folder

    def find_plugins(self, a_test):
        '''This is called the first time a test is added to the plugin manager. An instance of a test is needed to locate the project path. This facilitates users starting from an individual test and getting all the chosen plugins.'''
        for (dirpath, dirnames, filenames) in os.walk(a_test._project_path):
            if 'plugins.json' in filenames: 
                pluginpath = dirpath.replace(os.sep, '.')
                pluginpath = pluginpath[pluginpath.index(a_test._project_path.split(os.sep)[-1]):]
                with open(dirpath+os.sep+'plugins.json') as f:
                    self.used_plugins = json.load(f)
                if self.verbose:
                    if self.used_plugins:
                        plugin_str=f'PyICe Plugin Manager, plugins found:\n'
                        for plugin in self.used_plugins:
                            plugin_str+=f'"{plugin}"\n'
                        print_banner(plugin_str)
        self._send_notifications = "notifications" in self.used_plugins
        if self._send_notifications:
            try:
                import cairosvg
                self._cairosvg = cairosvg
            except Exception as e:
                print_banner("*** PLUGIN MANAGER WARNING ****", "", "You elected to use the 'Notifications' Plugin.", "Unable to import cairosvg's Python package or compiled dll.", "Try installing the Glade/Gtk+ for Windows development environment.", "Otherwise suggest you opt out of the 'Notifications' plugin.", "Write to pyice-developers@analog.com for more information.", "", "*** Expect a crash when generating plots ****", "")

    def add_test(self, test, debug=False, skip_plot=False, skip_eval=False):
        '''Adds a script to the list that will be operated on. If this is the first time a test is added to this instance of plugin manager, plugin manager also takes this opportunity to acquire the list of plugins used for the project.
        args: test - class object. A test that contains the methods necessary for data collection and processing in the project.
        args: debug - Boolean. This will be passed into all run tests to be used for abbreviating data collection loops. Default value is False.'''
        a_test = test()
        a_test._debug = debug
        self.tests.append(a_test)
        a_test.pm=self
        a_test._skip_plot=skip_plot
        a_test._skip_eval=skip_eval
        (a_test._module_path, file) = os.path.split(inspect.getsourcefile(type(a_test)))
        a_test._name = a_test._module_path.split(os.sep)[-1]
        os.makedirs(os.path.join(a_test._module_path,self.scratch_folder), exist_ok=True)
        try:
            a_test._project_path = a_test._module_path[:a_test._module_path.index(a_test.project_folder_name)+len(a_test.project_folder_name)]
        except AttributeError as e:
            print_banner("PyICe TEST_MANAGER: User's test template requires an attribute 'project_folder_name' that names the project's topmost folder in order for this PyICe workflow to be able to find the project.")
        a_test._db_file = os.path.join(a_test._module_path, self.scratch_folder, 'data_log.sqlite')
        if len(self.tests) == 1:
            self._project_path = a_test._project_path
            try:
                self.verbose = a_test.get_verbose()
            except Exception:
                self.verbose = True
            self.find_plugins(a_test)
            if 'notifications' in self.used_plugins:
                self._find_notifications(a_test._project_path)
        a_test._is_crashed = False

    def run(self, temperatures=[]):
        '''This method goes through the complete data collection process the project set out. Scripts will be run once per temperature or just once if no temperature is given. Debug will be passed on to the script to be used at the script's discretion.
        args: temperatures- list. The list consists of values that will be set to the 'temp_control_channel' assigned by the instrument drivers. Default value is an empty list.'''
        self.collect(temperatures)
        self.plot()
        if 'evaluate_tests' in self.used_plugins:
            self.evaluate()
        if 'correlate_tests' in self.used_plugins:
            self.correlate()
        for test in self.tests:
            if hasattr(test, '_test_results') and test._test_results._test_results:
                self.notify(test.get_test_results(), subject='Test Results')
            if len(self._plots) and self._send_notifications: #Don't send empty emails
                self.email_plots(self._plots)
            if len(self._linked_plots) and self._send_notifications: #Don't send empty emails
                self.email_plot_dictionary(self._linked_plots)
        if 'archive' in self.used_plugins:
            self._archive()

    def add_instrument_channels(self):
        '''In this method, a master is populated by instruments and their channels.
        A file in the "benches" folder found anywhere under the head project folder should have the name of the computer associated with the current bench, and contains the get_instruments function.
        The name of the file should have underscores where the computer name may use dashes.
        Then, all the minidrivers are imported and the master is populated using the instruments from the bench file.
        The minidrivers (found in a "hardware_drivers" folder) define which instrument is expected and what channels names will be added for those instruments.
        Drivers should return a dictionary with needed key 'instruments', which returns a list of channels and channel objects to be added to the master, and optional keys 'cleanup functions', 'temp_control_channel' ,and 'special_channel_action'.
        The value for "cleanup functions" is a list of functions that put the instruments in safe states once the test is complete.
        The cleanup functions are run in the order in which the instruments appear in the bench file.
        The 'temp_control_channel' is a channel object. The values provided in the temperature list will be written to it.
        The special channel actions are functions that are run on each logging of data and the value is a dicionary with a channel object or the string name of a channel as key, and the value the function to be run. The function requires the arguments channel_name, readings, and test.'''

        self.cleanup_fns = []
        self.startup_fns = []
        self.shutdown_fns = []
        self.temperature_channel = None
        self.special_channel_actions = {}
        for (dirpath1, dirnames, filenames) in os.walk(self._project_path):
            if 'benches' not in dirpath1 or self._project_path not in dirpath1: continue
            try:
                benchpath = dirpath1.replace(os.sep, '.')
                benchpath = benchpath[benchpath.index(self._project_path.split(os.sep)[-1]):]
                module = importlib.import_module(name=benchpath+'.'+self.thismachine, package=None)
                break
            except ImportError as e:
                print(e)
                raise Exception(f"Can't find bench file {self.thismachine}. Note that dashes must be replaced with underscores.")
        self.interfaces = module.get_interfaces()
        for (dirpath, dirnames, filenames) in os.walk(self._project_path):
            if 'hardware_drivers' not in dirpath: continue
            driverpath = dirpath.replace(os.sep, '.')
            driverpath = driverpath[driverpath.index(self._project_path.split(os.sep)[-1]):]
            for driver in filenames:
                driver_mod = importlib.import_module(name=driverpath+'.'+driver[:-3], package=None)
                instrument_dict = driver_mod.populate(self)
                if instrument_dict['instruments'] is not None:
                    for instrument in instrument_dict['instruments']:
                        self.master.add(instrument)
                    if 'cleanup_list' in instrument_dict:
                        for fn in instrument_dict['cleanup_list']:
                            self.cleanup_fns.append(fn)
                    if 'startup_list' in instrument_dict:
                        for fn in instrument_dict['startup_list']:
                            self.startup_fns.append(fn)
                    if 'temp_control_channel' in instrument_dict:
                        if self.temperature_channel == None:
                            self.temperature_channel = instrument_dict['temp_control_channel']
                            temp_instrument = instrument_dict['instruments']
                        else:
                            raise Exception(f'BENCH MAKER: Multiple channels have been declared the temperature control! One from {temp_instrument} and one from {instrument_dict["instruments"]}.')
                    if 'shutdown_list' in instrument_dict:
                        for fn in instrument_dict['shutdown_list']:
                            self.shutdown_fns.append(fn)
                    if 'special_channel_action' in instrument_dict:
                        overwrite_check = [i for i in instrument_dict['special_channel_action'] if i in self.special_channel_actions]
                        if overwrite_check:
                            raise Exception(f'BENCH MAKER: Multiple actions have been declared for channel(s) {overwrite_check}.')
                        self.special_channel_actions.update(instrument_dict['special_channel_action'])
            break
        if self.temperature_channel == None:
            self.temperature_channel = self.master.add_channel_dummy("tdegc")
            self.temperature_channel.write(25)

    def _create_logger(self, test):
        '''Each test add to the plugin manager will have its own logger with which it shall store the data collected by their collect method. The channels will be determined by the drivers added to the driver, and a sqlite database and table will be automatically created and linked to the tests.'''
        test._logger = Callback_logger(database=test.get_db_file(), special_channel_actions=self.special_channel_actions, test=test)
        test._logger.merge_in_channel_group(self.master.get_flat_channel_group())
        if hasattr(test, 'customize'):
            test.customize()
        test._logger.new_table(table_name=test.get_name(), replace_table=True)
        test._logger.write_html(file_name=test.get_module_path()+os.sep+'scratch'+os.sep+test.get_project_folder_name()+'.html')

    def startup(self):
        for func in self.startup_fns:
            try:
                func()
            except:
                print("\n\PyICE Plugin Manager: One or more startup functions not executable. See list below.\n")
                for function in self.startup_fns:
                    print(function)
                exit()
        
    def cleanup(self):
        """Runs the functions found in cleanup_fns. Resets the intstruments to predetermined "safe" settings as given by the drivers. Does so in the reverse order in which the channels were created whereas startups go in forward order of which created."""
        for func in reversed(self.cleanup_fns):
            try:
                func()
            except:
                print("\n\PyICE Plugin Manager: One or more cleanup functions not executable. See list below.\n")
                for function in self.cleanup_fns:
                    print(function)
                exit()

    def shutdown(self):
        for func in self.shutdown_fns:
            try:
                func()
            except:
                print("\n\PyICE Plugin Manager: One or more shutdown functions not executable. See list below.\n")
                for function in self.shutdown_fns:
                    print(function)
                exit()

    def close_ports(self):
        """Release the instruments from bench control."""
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
        '''Sends the provided message to all emails and phone numbers found in the variable self.notification_targets.
        args:
            msg - str. The body of the email or the complete text.
            subject - str. Default None. The subject given to any email sent. No affect on texts.
            attachment filenames - list. Default empty list. A list of strings denoting the names of files that will be attached to any emails sent.
            attachment_MIMEParts - list. Default empty list. A list of MIME (Multipurpose Internet Mail Extensions) objects that will be added to the body of any email sent.'''
        if 'notifications' in self.used_plugins:
            for signal_type in self.notification_targets:
                if signal_type == 'emails':
                    for email_address in self.notification_targets['emails']:
                        mail = email(email_address)
                        mail.send(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
                elif signal_type == 'texts':
                    for txt_number, carrier in self.notification_targets['texts']:
                        text = sms(txt_number, carrier)
                        text.send(msg)
                else:
                    print(f"Plugin Manager Warning: Unrecognized key {signal_type} found in the notification target dictionary. Please only use 'emails' and 'texts'.")
            try:
                for fn in self._notification_functions:
                    try:
                        fn(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
                    except TypeError:
                        # Function probably doesn't accept subject or attachments
                        try:
                            fn(msg)
                        except Exception as e:
                            # Don't let a notification crash a more-important cleanup/shutdown.
                            print(e)
                    except Exception as e:
                        # Don't let a notification crash a more-important cleanup/shutdown.
                        print(e)
            except AttributeError as e:
                if not len(attachment_filenames) and not len(attachment_MIMEParts):
                    print(msg)

    def _find_notifications(self, project_path):
        self._notification_functions = []
        self.notification_targets = {'emails':[], 'texts':[]}
        for (dirpath, dirnames, filenames) in os.walk(project_path):
            if self.operator+'.py' in filenames: 
                usernotificationpath = dirpath.replace(os.sep, '.')
                usernotificationpath = usernotificationpath[usernotificationpath.index(project_path.split(os.sep)[-1]):]
                module = importlib.import_module(name=usernotificationpath+f'.{self.operator}', package=None)
                if hasattr(module, 'add_notifications_to_test_manager'):
                    module.add_notifications_to_test_manager(test_manager=self)
                if hasattr(module, 'get_notification_targets'):
                    self.notification_targets = module.get_notification_targets()
                break

    def add_notification(self, fn):
        '''Add a function that will be run whenever a notification is sent. Arguments for the provided function are either the standard for lab_utils.communications.email.send(self, body, subject=None, attachment_filenames=[], attachment_MIMEParts=[]) or a simple text string.'''
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
            plot_png = self._cairosvg.svg2png(bytestring=plot_src)
            plot_mime = MIMEImage(plot_png, 'image/png')
            plot_mime.add_header('Content-Disposition', 'inline')
            plot_mime.add_header('Content-ID', f'<plot_{i}>')
            msg_body += f'<img src="cid:plot_{i}"/>'
            attachment_MIMEParts.append(plot_mime)
        self.notify(msg_body, subject='Plot Results', attachment_MIMEParts=attachment_MIMEParts)

    def email_plot_dictionary(self, plot_svg_source):
        msg_body = ''
        attachment_MIMEParts=[]
        for plot_group in plot_svg_source:
            msg_body+=plot_group
            msg_body+='\n'
            for (i,plot) in enumerate(plot_svg_source[plot_group]):
                plot_png = self._cairosvg.svg2png(bytestring=plot)
                plot_mime = MIMEImage(plot_png, 'image/png')
                plot_mime.add_header('Content-Disposition', 'inline')
                plot_mime.add_header('Content-ID', f'<plot_{plot_group}_{i}>')
                msg_body += f'<img src="cid:plot_{plot_group}_{i}"/>'
                attachment_MIMEParts.append(plot_mime)
            msg_body+='\n'
        self.notify(msg_body, subject='Plot Results', attachment_MIMEParts=attachment_MIMEParts)

    def crash_info(self, test):
        (typ, value, trace_bk) = test._crash_info
        crash_str = f'Test: {test.get_name()} crashed: {typ},{value}\n'
        crash_sep = '==================================================\n'
        crash_str += crash_sep
        crash_str += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
        crash_str += crash_sep
        return crash_str

    ###
    # TRACEABILITY METHODS
    ###
    def _create_metalogger(self, test):
        '''Called from the plugin_master if the 'traceability' plugin was included in the plugin_registry, this creates a master and logger separate from the test data logger, and populates them using user provided metadata gathering functions.'''
        _master = master()
        test._metalogger = logger(database=test.get_db_file())
        test._metalogger.add(_master)
        test._traceabilities = Traceability_items(test)
        test._traceabilities.populate_traceability_data(test.traceability_items)
        test._traceabilities.add_data_to_metalogger(test._metalogger)
    def _metalog(self, test):
        '''This is separate from the _create_metalogger method in order to give other plugins the opportunity to add to the metalogger before the channel list is commited to a table.'''
        test._metalogger.new_table(table_name=test.get_name() + "_metadata", replace_table=True)
        test._metalogger.log()

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
        '''Makes a copy of the data just collected and puts it and the associated metatable (if there is one) in an archive folder. Also adds a copy of the table (and metatable) to the database with the time of collection to the test's generic database, so it will not be overwritten when the test is next run. Will also generate scripts to rerun plotting (if the script has a plot method) and evaluation (if the evaluation feature is used).'''
        print_banner('Archiving. . .')
        try:
            archive_folder = self.tests[0].get_archive_folder_name()
        except AttributeError:
            archive_folder = datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M")
        archived_tables = []
        for test in self.tests:
            archiver = test_archive.database_archive(test_script_file=test.get_module_path(), db_source_file=test.get_db_file())
            if not archiver.has_data(tablename=test.get_name()):
                print(f'No data logged for {test.get_name()}. Skipping archive.')
                continue
            if test._is_crashed:
                this_archive_folder = archive_folder + '_CRASHED'
            else:
                this_archive_folder = archive_folder
            db_dest_file = archiver.compute_db_destination(this_archive_folder)
            archiver.copy_table(db_source_table=test.get_name(), db_dest_table=test.get_name(), db_dest_file=db_dest_file)
            test._logger.copy_table(old_table=test.get_name(), new_table=test.get_name()+'_'+archive_folder)
            if 'traceability' in self.used_plugins:
                archiver.copy_table(db_source_table=test.get_name()+'_metadata', db_dest_table=test.get_name()+'_metadata', db_dest_file=db_dest_file)
                test._logger.copy_table(old_table=test.get_name()+'_metadata', new_table=test.get_name()+'_'+archive_folder+'_metadata')
            archived_tables.append((test, test.get_name(), db_dest_file))
            # test._add_db_indices(table_name=test.get_name(), db_file=db_dest_file)
        if len(archived_tables):
            arch_plot_scripts = []
            for (test, db_table, db_file) in archived_tables:
                if hasattr(test, 'plot'):
                    dest_file = os.path.join(os.path.dirname(db_file), f"replot_data.py")
                    import_str = test._module_path[test._module_path.index(test.project_folder_name):].replace(os.sep,'.')
                    plot_script_src = "if __name__ == '__main__':\n"
                    plot_script_src += f"    from PyICe.plugins.plugin_manager import Plugin_Manager\n"
                    plot_script_src += f"    from {import_str}.test import Test\n"
                    plot_script_src += f"    pm = Plugin_Manager()\n"
                    plot_script_src += f"    pm.add_test(Test)\n"
                    plot_script_src += f"    pm.plot(database='data_log.sqlite', table_name='{test.get_name()}')\n"
                    try:
                        with open(dest_file, 'a') as f: #exists, overwrite, append?
                            f.write(plot_script_src)
                    except Exception as e:
                        #write locked? exists?
                        print(type(e))
                        print(e)
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.plot(database=os.path.relpath(db_file), table_name=db_table)
                if 'evaluate_tests' in self.used_plugins:
                    dest_file = os.path.join(os.path.dirname(db_file), f"reeval_data.py")
                    import_str = test._module_path[test._module_path.index(test.project_folder_name):].replace(os.sep,'.')
                    plot_script_src = "if __name__ == '__main__':\n"
                    plot_script_src += f"    from PyICe.plugins.plugin_manager import Plugin_Manager\n"
                    plot_script_src += f"    from {import_str}.test import Test\n"
                    plot_script_src += f"    pm = Plugin_Manager()\n"
                    plot_script_src += f"    pm.add_test(Test)\n"
                    plot_script_src += f"    pm.evaluate(database='data_log.sqlite', table_name='{test.get_name()}')\n"
                    try:
                        with open(dest_file, 'a') as f: #exists, overwrite, append?
                            f.write(plot_script_src)
                    except Exception as e:
                        #write locked? exists?
                        print(type(e))
                        print(e)
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.evaluate(database=os.path.relpath(db_file), table_name=db_table)
                if 'bench_image_creation' in self.used_plugins:
                    self.visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato', file_location=os.path.dirname(db_file))

                arch_plot_scripts.append(dest_file)
                print_banner(f'Archiving for {test.get_name()} complete.')

    ###
    # SCRIPT METHODS
    ###
    def collect(self, temperatures):
        '''This method aggregates the channels that will be logged and calls the collect method in every test added via self.add_test.
        args:
            temperatures (list): What values will be written to the temp_control_channel.'''
            # debug (Boolean): This will be passed on to the script and can be used to trigger shorter loops or fewer conditions under which to gather data to verify script completeness.'''
        try:
            self.master = master()
            self.add_instrument_channels()
            self.all_benches = []
            for test in self.tests:
                test._temperatures = temperatures
                test._channel_reconfiguration_settings=[]
                self._create_logger(test)
                if 'bench_config_management' in self.used_plugins:
                    self.test_components = component_collection()
                    self.test_connections = connection_collection(name=test.get_name())
                    try:
                        test._declare_bench_connections()
                    except Exception as e:
                        raise("TEST_MANAGER ERROR: This project indicated bench configuration data would be stored. Test template requires a _declare_bench_connections method that gathers the data.")
                    self.all_benches.append(self.test_connections)
            if 'bench_config_management' in self.used_plugins:
                self.all_connections = connection_collection.distill(self.all_benches)
            for test in self.tests:
                if 'traceability' in self.used_plugins:
                    self._create_metalogger(test)
                    if 'bench_config_management' in self.used_plugins:
                        test._traceabilities.get_traceability_data()['test_bench_connections'] = self.all_connections.get_readable_connections()
                        test._metalogger.add_channel_dummy('test_bench_connections')
                        test._metalogger.write('test_bench_connections', self.all_connections.get_readable_connections())
                        
                        test._traceabilities.get_traceability_data()['blocked_bench_terminals'] = lambda: self.all_connections.get_readable_blocked_terminals()
                        test._metalogger.add_channel_dummy('blocked_bench_terminals')
                        test._metalogger.write('blocked_bench_terminals', self.all_connections.get_readable_blocked_terminals())
                    self._metalog(test)
            if 'bench_config_management' in self.used_plugins and self.verbose:
                print(self.all_connections.print_connections())
            if 'bench_image_creation' in self.used_plugins:
                self.visualizer = bench_visualizer.visualizer(connections=self.all_connections.connections, locations=test.get_bench_image_locations())
                for test in self.tests:
                    self.visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato', file_location=test._module_path+os.sep+'scratch')
            summary_msg = f'{self.operator} on {self.thismachine}\n'
            if not len(temperatures):
                for test in self.tests:
                    summary_msg += f'\t* {test.get_name()}*\n'
                    if not test._is_crashed:
                        try:
                            # test.test_timer.resume_timer()
                            self.startup()
                            test._reconfigure()
                            print_banner(f'{test.get_name()} Collecting. . .')
                            test.collect()
                            test._restore()
                        except (Exception, BaseException) as e:
                            traceback.print_exc()
                            test._is_crashed = True
                            test._crash_info = sys.exc_info()
                            print(test._crash_info)
                            self.notify(test._crash_info, subject='CRASHED!!!')
                        self.cleanup()
                self.shutdown()
            else:
                assert self.temperature_channel != None
                for temp in temperatures:
                    print_banner(f'Setting temperature to {temp}')
                    self.temperature_channel.write(temp)
                    for test in self.tests:
                        if not test._is_crashed:
                            try:
                                print_banner(f'Starting {test.get_name()} at {temp}C')
                                # test.test_timer.resume_timer()
                                self.startup()
                                test._reconfigure()
                                test.collect()
                                test._restore()
                            except (Exception, BaseException) as e:
                                traceback.print_exc()
                                test._is_crashed = True
                                test._crash_info = sys.exc_info()
                                print(test._crash_info)
                                self.notify(test._crash_info, subject='CRASHED!!!')
                            self.cleanup()
                    if all([x._is_crashed for x in self.tests]):
                        print_banner('All tests have crashed. Skipping remaining temperatures.')
                        break
                self.shutdown()
        except Exception as e:
            traceback.print_exc()
            for test in self.tests:
                test._is_crashed = True
            try:
                self.cleanup()
                self.shutdown()
            except AttributeError as e:
                # Didn't get far enough to populate the bench before crashing.
                pass
        finally:
            try:
                self.close_ports()
            except AttributeError as e:
                # Didn't get far enough to populate the bench before crashing.
                pass
            except Exception as e:
                # Not sure if this should crash now or not, or how it might happen
                try:
                    self.notify(f'{self.operator} on {self.thismachine}\n'+str(e), subject='Port cleanup crash!')
                except:
                    pass

    def plot(self, database=None, table_name=None, plot_filepath=None):
        '''Run the plot method of each test in self.tests. Any plots returned by a test script's plot method will be emailed if the notifications plugin is used.
        args:
            database - string. The location of the database with the data to plot If left blank, the plot will continue with the database in the same directory as the test script.
            table_name - string. The name of the table in the database with the data to plot. If left blank, the plot will continue with the table named after the test script.
            plot_filepath - string. This is where the plots will be placed upon creation. If left blank, a directory name plots will be created in the directory with the plot script and and the plots will be placed in there.'''
        self._plots=[]
        self._linked_plots={}
        reset_db = False
        reset_tn = False
        reset_pf = False
        print_banner('Plotting. . .')
        for test in self.tests:
            if not test._skip_plot and hasattr(test, 'plot') and not test._is_crashed:
                test.plot_list=[]
                test.linked_plots={}
                print_banner(f'{test.get_name()} Plotting. . .')
                if database is None:
                    database = test.get_db_file()
                    reset_db = True
                if table_name is None:
                    test._table_name = test.get_name()
                    reset_tn = True
                else:
                    test._table_name=table_name
                if plot_filepath is None:
                    test._plot_filepath = os.path.dirname(os.path.abspath(database))
                    reset_pf = True
                else:
                    test._plot_filepath = plot_filepath
                test._db = sqlite_data(database_file=database, table_name=test.get_table_name())
                try:
                    test.plot()
                except Exception as e:
                    # Don't stop other test's plotting or archiving because of a plotting error.
                    print_banner(e)
                if isinstance(test.plot_list, (LTC_plot.plot, LTC_plot.Page)):
                    test.plot_list = [self._convert_svg(test.plot_list)]
                else:
                    assert isinstance(test.plot_list, list)
                    test.plot_list = [self._convert_svg(plt) for plt in test.plot_list]
                for plot_group in test.linked_plots:
                    test.linked_plots[plot_group] = [self._convert_svg(plt) for plt in test.linked_plots[plot_group]]
                self._plots.extend(test.plot_list)
                self._linked_plots.update(test.linked_plots)
                print_banner(f'Plotting for {test.get_name()} complete.')
                if reset_db:
                    database = None
                if reset_tn:
                    table_name = None
                if reset_pf:
                    plot_filepath = None
            elif test._is_crashed:
                print(f"{test.get_name()} crashed. Skipping plot.")

    def evaluate(self, database=None, table_name=None):
        '''Run the evaluate method of each test in self.tests.
        args:   
            database - string. The location of the database with the data to evaluate If left blank, the evaluation will continue with the database in the same directory as the test script.
            table_name - string. The name of the table in the database with the relevant data. If left blank, the evaluation will continue with the table named after the test script.'''
        print_banner('Evaluating. . .')
        reset_db = False
        reset_tn = False
        for test in self.tests:
            if not test._skip_eval and not test._is_crashed:
                if database is None:
                    database = test._db_file
                    reset_db = True
                if table_name is None:
                    test._table_name = test.get_name()
                    reset_tn = True
                else:
                    test._table_name = table_name
                test._test_results = Test_Results(test._name, module=test)
                test._db = sqlite_data(database_file=database, table_name=test.get_table_name())
                test.evaluate_results()
                if test._test_results._test_results:
                    print(test.get_test_results())
                t_r = test._test_results.json_report()
                dest_abs_filepath = os.path.join(os.path.dirname(database), f"test_results.json")
                if t_r is not None:
                    with open(dest_abs_filepath, 'wb') as f:
                        f.write(t_r.encode('utf-8'))
                        f.close()
                if reset_db:
                    database = None
                if reset_tn:
                    table_name = None
            elif test._is_crashed:
                print(f"{test.get_name()} crashed. Skipping evaluation.")
                

    def correlate(self, database=None, table_name=None):
        '''Run the correlate method of each test in self.tests.
        args:   
            database - string. The location of the database with the data to evaluate If left blank, the evaluation will continue with the database in the same directory as the test script.
            table_name - string. The name of the table in the database with the relevant data. If left blank, the evaluation will continue with the table named after the test script.'''
        print_banner('Correlating. . .')
        for test in self.tests:
            if test._is_crashed:
                print(f"{test.get_name()} crashed. Skipping correlation.")
                continue
            if database is None:
                database = test._db_file
            if table_name is None:
                test._table_name = test.get_name()
            else:
                test._table_name = table_name
            test._corr_results = Test_Results(test.get_name(), module=test)
            test._db = sqlite_data(database_file=database, table_name=test.get_table_name())
            test.correlate_results()
            print(test.get_test_results())
            t_r = test._corr_results.json_report()
            dest_abs_filepath = os.path.join(os.path.dirname(database),f"correlation_results.json")
            if t_r is not None:
                with open(dest_abs_filepath, 'wb') as f:
                    f.write(t_r.encode('utf-8'))
                    f.close()