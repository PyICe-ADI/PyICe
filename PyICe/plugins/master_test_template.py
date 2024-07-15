class Master_Test_Template():
    ###
    # SCRIPT METHODS
    ###
    def reconfigure(self, channel, value):
        '''Optional method used during customize() if changes are made to the DUT on a particular test in a suite. Unwound after test's collect at each temperature.'''
        self._channel_reconfiguration_settings.append((channel, channel.read(), value))
    def _reconfigure(self):
        '''save channel setting before writing to value'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(new)
    def _restore(self):
        '''undo any changes made by reconfigure'''
        for (ch, old, new) in self._channel_reconfiguration_settings:
            ch.write(old)
    def customize(self):
        '''Optional method to alter the logger before the test begins.'''
        if self.verbose:
            print("This test script does not have a collect method.")
    def declare_bench_connections(self):
        '''Optional method to log the setup needed to run the test. Plugin required.'''
        if self.verbose:
            print("This test script does not have a declare_bench_connections method, and is assumed to use the default setup")
    def collect(self):
        ''' Mandatory method to operate the bench and collect the data.'''
        if self.verbose:
            print("This test script does not have a collect method.")
    def plot(self):
        ''' Optional method to retrieve the data collected and create plots. Can be run over and over once a collect has run. User must return a list or tuple of plots and/or pages, or an individual LTC_plot.Page, or a single LTC_plot.plot.'''
        print("No plots were made with this script.")
        return []

    ###
    # BEHIND THE SCENES METHODS
    ###
    def get_channels(self):
        return self._logger
    def get_bench_image_locations(self):
        if hasattr(self, 'bench_image_locations'):
            return self.bench_image_locations
        else:
            raise Exception('Oi! You said you wanted a visual representation of your lab bench! You need to define bench_image_locations in your Test_Template!')

    ###
    # EVALUATION METHODS
    ###
    def evaluate_test_result(self, name, data, conditions=None):
        '''This will compare submitted data to limits for the named test.
        args:
            name - string. The name of the test whose limits will be used.
            data - Boolean or iterable object. Each value will be compared to the limits (or boolean value) of the name argument.
            conditions - None or dictionary. A dictionary with channel names as keys and channel values as values. Used to report under what circumstances the data was taken. Default is None.'''
        self._test_results.test_info[name]=self.get_test_info(name)
        self._test_results._register_test_result(name=name, iter_data=data, conditions=conditions)
    def evaluate_test_query(self, name, query):
        '''This will compare submitted data to limits for the named test.
        args:
            name - string. The name of the test whose limits will be used.
            database - SQLite database object. The first column will be compared to the limits of the named spec and the rest will be used for grouping.'''
        self._test_results.test_info[name]=self.get_test_info(name)
        self.db.query(query)
        self._test_results._evaluate_database(name=name, database=self.db)
    def evaluate(self, name, values, conditions=[], where_clause=''):
        '''This compares submitted data from a SQLite database to a named test in a more outlined fashion.
        args:
            name - string. The name of the test with limits to be used.
            value_column - string. The name of the channel that will be evaluated.
            grouping_columns - list. The values of the value_column will be grouped and evaluated by the permutations of the channels that are named in this list of strings.'''
        grouping_str = ''
        for condition in conditions:
            grouping_str += ','
            grouping_str += condition
        query_str = f'SELECT {values}{grouping_str} FROM {self.table_name} ' + ('WHERE ' + where_clause if where_clause else '')
        self.evaluate_test_query(name, query=query_str)
    # def evaluate_database_value_column(self, name, value_channel, where_clause=''):
    def get_test_results(self):
        '''Returns a string that reports the Pass/Fail status for all the tests evaluated in the script and the test script as a whole.'''
        res_str = ''
        all_pass = True
        res_str += f'*** Module {self.name} ***\n'
        res_str += f'{self._test_results}'
        res_str += f'*** Module {self.name} Summary {"PASS" if self._test_results else "FAIL"}. ***\n\n'
        return res_str
    def get_test_info(self, name):
        raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated a use of the TEST_LIMIT plugin but no project specific 'get_test_info' method was provided.")


    # ###
    # # CORRELATE FEATURE METHODS
    # ###
    # def correlate_results(self):
        # ''' Optional method for correlating data collected with user provided other set keyed by a unique device identifier (e.g. serial number of sorts)
        # Use of this feature requires the correlate test plugins.
         # User is expected to overwrite this with their own method that describes how their results are to be correlated.'''
        
        # raise("Test scripts requires a correlate_results method.")
    # def correlate_test_result(self, name, data, key_conditions):
        # self._test_results.test_info[name]=self.get_correlation_test_info(name)
        # self._test_results._register_correlation_result(name, data, key_conditions)
    # def get_correlation_data_scalar(self, REFID, data, key_conditions):
        # '''Must return a value from an outside data source associated with the REFID named and matching key_conditions in the data provided.'''
        # raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated a use of the CORRELATION plugin but no project specific 'get_correlation_data_scalar' method was provided.")
    # def get_correlation_test_info(self, name):
        # '''Must return a dictionary of info relating to the REFID name, with keys that include AT LEAST 'upper_limit', 'lower_limit', and 'UNIT'.'''
        # raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated a use of the CORRELATION plugin but no project specific 'get_correlation_test_info' method was provided.")