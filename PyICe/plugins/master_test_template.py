from PyICe.plugins.plugin_manager import plugin_manager
from PyICe import lab_core
from PyICe.lab_core import logger
import os, inspect

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


class Master_test_template():
    def __init__(self, db_filename='data_log.sqlite'):
        '''User's test_template inherits this class as a bridge to connect to PyICe.'''
        (self._module_path, file) = os.path.split(inspect.getsourcefile(type(self)))
        self.name = self._module_path.split('\\')[-1]
        try:
            self._project_path = self._module_path[:self._module_path.index(self.project_folder_name)+len(self.project_folder_name)]
        except AttributeError as e:
            print_banner("PYICE MASTER TEST TEMPLATE: User's test template requires an attribute 'project_folder_name' that names the project's topmost folder in order for this PyICe workflow to be able to find the project.")
        self._db_file = os.path.join(self._module_path, db_filename)
        self._channel_reconfiguration_settings = []

    def evaluate_results(self, database, table_name):
        ''' Optional method for comparing data collected to user provided limits across a variety of conditions.
        Use of this feature requires the use of evaluate test plugins.
        User is expected to overwrite this with their own method that describes how their results are to be evaluated.'''
        raise(f"This project added in the plugin 'evaluate'. f{self.name} script does not have the required register_tests method to operate the plugin.")

    def correlate_results(self, database, table_name):
        ''' Optional method for correlating data collected with user provided other set keyed by a unique device identifier (e.g. serial number of sorts)
        Use of this feature requires the correlate test plugins.
         User is expected to overwrite this with their own method that describes how their results are to be correlated.'''
        raise("Test scripts requires a correlate_results method.")

    def declare_bench_connections(self, components, connections):
        '''This method is only needed if the 'bench_config_management' plugin is used. This optional method provides set up instructions and generates a computerized representation of the physical experimental setup. Tracks compatiblity between tests within a suite.
        Use of this method requires the bench_management plugin.
        User is expected to overwrite this with their own method that adds the connections their bench uses.'''
        raise("Test scripts requires a configure_bench method.")

    def _create_logger(self, master, special_channel_actions=None):
        '''Combine the master with a logger for the test. 
        The special_channel_actions are passed to a logger wrapper in order to be performed on a per-log basis.'''
        self.special_channel_actions = special_channel_actions
        self._logger = Callback_logger(database=self._db_file, special_channel_actions=special_channel_actions, test=self)
        # self._logger.merge_in_channel_group(master.get_flat_channel_group())  ## Not sure why this is necessary when add(master) works just as well. TODO: Ask Dave.
        self._logger.add(master)
        ret = self.customize(self._logger)
        self._logger.new_table(table_name=self.name, replace_table=True)

    def _create_metalogger(self):
        '''Called from the plugin_master if the 'traceability' plugin was included in the plugin_registry, this creates a master and logger separate from the test data logger, and populates them using user provided metadata gathering functions. '''
        _master = lab_core.master()
        self._metalogger = lab_core.logger(database=self._db_file)
        self._metalogger.add(_master)
        self._get_metadata_gathering_fns().get_traceability_items().get_traceability_data(self._metalogger)


    
    def _get_metadata_gathering_fns(self):
        '''This method is only needed if the 'traceability' plugin is used. This method shall return the file that contains the functions used to obtain test metadata. This meta data will be stored in a separate table in the database alongside test data for ease of reference.'''
        raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated traceability data would be stored in a metadata database table. Please include a 'def _get_metadata_gathering_fns(self)' method in your test_template class that returns the file containing the functions for obtaining the data to be stored.")

    def _metalog(self):
        '''This is separate from the _create_metalogger method in order to give other plugins the opportunity to add to the metalogger before the channel list is commited to a table.'''
        self._metalogger.new_table(table_name=self.name+"_metadata", replace_table=True)
        self._metalogger.log()

    def _get_components(self):
        '''This method is necessary if the 'bench_config_management' plugin is used. This method shall return a bench_configuration_management.component_collection() object, populated with the components used by the tests in this project. Typically, this will consist of instruments from bench_configuration_management.lab_components() and any boards created for the project.'''
        raise Exception("MASTER TEST TEMPLATE ERROR: This project requires a _get_components method.")

    def customize(self, channels):
        '''Optional method to make a late script specific change to the logger often used for speed improvement or special data reduction or additional channels. 
        Can also create script specific class objects or PyICe channels such as slow rampers, finders (binary search), oscilloscope channel assignments, etc.'''
        pass

    def collect(self, channels, debug):
        ''' Mandatory method to operate the bench and collect the data.'''
        raise Exception("Test scripts require a collect method.")

    def plot(self, database, table_name, plot_filepath):
        ''' Optional method to retrieve the data collected and create plots. Can be run over and over once a collect has run. User must return a list or tuple of plots and/or pages, or an individual LTC_plot.Page, or a single LTC_plot.plot.'''
        print("No plots were made with this script.")
        return []

    def register_test_result(self, test_name, data):
        ## storing or comparing data provided is between limits given by self.get_eval_limits(test_name). generates a pass/fail
        pass

    def get_eval_limits(self):
        raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated a use of the TEST_LIMIT plugin but no project specific 'get_eval_limits' method was provided.")

    def reconfigure(self, channel, value):
        '''save channel settings specific to a particular test. Unwound after test at each temperature.'''
        self._channel_reconfiguration_settings.append((channel, channel.read(), value))

    def _reconfigure(self):
        '''save channel setting before writing to value'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(new)

    def _restore(self):
        '''undo any changes made by reconfigure'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(old)

    @classmethod
    def run(cls, temperatures=[], debug=False):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will make a logger, collect a full set of data, and execute any plugins added to the project.'''
        temperatures = [] if temperatures == None else temperatures 
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.run(temperatures, debug)

    @classmethod
    def debug(cls, temperatures=[], debug=True):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will make a logger, collect an abridged set of data determined by the test itself, and execute any plugins added to the project.'''
        temperatures = [] if temperatures == None else temperatures 
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.run(temperatures, debug)
    
    @classmethod
    def collect_only(cls):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will make a logger and collect a full set of data, but will skip any plugins added that typically run after collect.'''
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.collect(temperatures, debug)
            
    @classmethod
    def plot_only(cls):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will make a plot based on the last set of data collected in the database adjacent to the test script.'''
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.plot()
            
    @classmethod
    def evaluate_only(cls):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will produce a pass/fail grade for the tests with set limits from the last set of data collected for the test.'''
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.evaluate()
            
    @classmethod
    def correlate_only(cls):
        '''A class method so the user can start a test at the test level without first having to instantiate it. This will produce a pass/fail grade for the tests with comparison limits from the last set of data collected for the test.'''
        cls.pm = plugin_manager()
        cls.pm.add_test(cls)
        cls.pm.correlate()