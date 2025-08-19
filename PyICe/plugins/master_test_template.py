class Master_Test_Template():
    ###
    # SCRIPT METHODS
    ###
    def reconfigure(self, read_function, write_function, value):
        '''
        Optional method used during customize() if changes are made to the DUT on a particular test in a suite.
        Unwound after test's collect at each temperature.
        read_function and write_function should be conjugate methods of a particular channel to help the system unwind after _this_ test.
        "value" is the value to which the channel will be assigned for _this_ test.
        '''
        self._channel_reconfiguration_settings.append((read_function(), write_function, value))
    def _reconfigure(self):
        '''save channel setting before writing to value'''
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(new)
    def _restore(self):
        '''undo any changes made by reconfigure'''
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(old)
    def customize(self):
        '''Optional method to alter the logger before the test begins.'''
    def declare_bench_connections(self):
        '''Optional method to log the setup needed to run the test. Plugin required.'''
    def collect(self):
        ''' Mandatory method to operate the bench and collect the data.'''
    def plot(self):
        ''' Optional method to retrieve the data collected and create plots. Can be run over and over once a collect has run. User must return a list or tuple of plots and/or pages, or an individual LTC_plot.Page, or a single LTC_plot.plot.'''
        return []
    def _modify_metalogger(self):
        '''Method used to make any changes to the metalog before it is merged with a sqlite table. Not to be used itself, but to be overwritten in a project specific test_template. Plugin required.'''

    ###
    # GET METHODS
    ###
    def get_channels(self):
        return self._logger
    def get_name(self):
        return self._name
    def get_project_folder_name(self):
        return self.project_folder_name
    def get_module_path(self):
        if hasattr(self, '_module_path'):
            return self._module_path
        else:
            print(f"Attempted to access the module path for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")
    def get_debug(self):
        return self._debug
    def get_verbose(self):
        return self.verbose
    def get_db_file(self):
        if hasattr(self, '_db_file'):
            return self._db_file
        else:
            print(f"Attempted to access the database file for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")
    def get_database(self):
        if hasattr(self, '_db'):
            return self._db
        else:
            print(f"Attempted to access the database for {self.get_name()}. It's only intended to be accessible from inside the plot() or evaluate() methods.")
    def get_table_name(self):
        if hasattr(self, '_table_name'):
            return self._table_name
        else:
            print(f'No table name has been assigned to {self.get_name()} at this time.')
    def get_plot_filepath(self):
        if hasattr(self, '_plot_filepath'):
            return self._plot_filepath
        else:
            print(f'No file path for plot locations has been assigned to {self.get_name()} at this time.')
    def get_bench_image_locations(self):
        if hasattr(self, 'bench_image_locations'):
            return self.bench_image_locations
        else:
            raise Exception("PyICe Master Test Template: You said you wanted a visual representation of your lab bench. You'll need to define bench_image_locations in your Test_Template.")

    ###
    # EVALUATION/CORRELATION METHODS
    ###
    def evaluate_results(self):
        '''Optional evaluate_results method placeholder'''
    def correlate_results(self):
        '''Optional correlate_results method placeholder'''
    def evaluate_rawdata(self, name, data, conditions=None, limits:dict={}):
        '''This will compare submitted data to limits for the named test.
        args:
            name - string. The name of the test whose limits will be used.
            data - Boolean or iterable object. Each value will be compared to the limits (or boolean value) of the name argument.
            conditions - None or dictionary. A dictionary with channel names as keys and channel values as values. Used to report under what circumstances the data was taken. Default is None.
            limits - Dictionary. A dictionary with the value limits to compare to the data. Must provide at least an upper or a lower limit as a key. If none are provided, the project's get_test_limits method will be used.'''
        if len(limits) == 0:
            self._test_results.test_limits[name]=self.get_test_limits(name)
        elif 'upper_limit' in limits.keys() or 'lower_limit' in limits.keys():
            self._test_results.test_limits[name]=limits
        else:
            raise KeyError(f"The limits argument for evaluate_rawdata requires an upper_limit and/or a lower_limit in its keys. Found {[x for x in limits.keys()]}.")
        self._test_results._evaluate_list(name=name, iter_data=data, conditions=conditions)
    def evaluate_query(self, name, query, limits:dict={}):
        '''This will compare submitted data to limits for the named test.
        args:
            name - string. The name of the test whose limits will be used.
            database - SQLite database object. The first column will be compared to the limits of the named spec and the rest will be used for grouping.
            limits - dictionary. A dictionary with the value limits to compare to the data obtained by the query. Must provide at least an upper or a lower limit as a key. If none are provided, the project's get_test_limits method will be used.'''
        if len(limits) == 0:
            self._test_results.test_limits[name]=self.get_test_limits(name)
        elif 'upper_limit' in limits.keys() or 'lower_limit' in limits.keys():
            self._test_results.test_limits[name]=limits
        else:
            raise KeyError(f"The limits argument for evaluate_query requires an upper_limit and/or a lower_limit in its keys. Found {[x for x in limits.keys()]}.")
        self.get_database().query(query)
        self._test_results._evaluate_database(name=name, database=self.get_database())
    def evaluate_db(self, name, limits:dict={}):
        '''This method evaluates a pre-massaged SQLite database, self.get_database(), from the user. It returns a bit of flexibility on the sequel query to the user.
        args:
            name - string. The name of the test whose limits will be used.
            limits - dictionary. A dictionary with the value limits to compare to the data obtained from the database. Must provide at least an upper or a lower limit as a key. If none are provided, the project's get_test_limits method will be used.'''
        if len(limits) == 0:
            self._test_results.test_limits[name]=self.get_test_limits(name)
        elif 'upper_limit' in limits.keys() or 'lower_limit' in limits.keys():
            self._test_results.test_limits[name]=limits
        else:
            raise KeyError(f"The limits argument for evaluate_db requires an upper_limit and/or a lower_limit in its keys. Found {[x for x in limits.keys()]}.")
        self._test_results._evaluate_database(name=name, database=self.get_database())
    def evaluate(self, name, values, conditions=[], where_clause='', limits:dict={}):
        '''This compares submitted data from a SQLite database to a named test in a more outlined fashion.
        args:
            name - string. The name of the test with limits to be used.
            value_column - string. The name of the channel that will be evaluated.
            grouping_columns - list. The values of the value_column will be grouped and evaluated by the permutations of the channels that are named in this list of strings.
            limits - dictionary. A dictionary with the value limits to compare to the data obtained from the database. Must provide at least an upper or a lower limit as a key. If none are provided, the project's get_test_limits method will be used.'''
        condition_str = ''
        for condition in conditions:
            condition_str += f",{condition}"
        query_str = f'SELECT {values}{condition_str} FROM {self.get_table_name()} ' + ('WHERE ' + where_clause if where_clause else '')
        self.evaluate_query(name, query=query_str, limits = limits)
    def register_test_failure(self, name, reason, conditions=None, query=None):
        '''Submit a result for a test that is considered a FAIL so the test, regardless of other data submitted, will result in a FAIL overall.'''
        self._test_results._register_test_failure(name=name, reason=reason, conditions=conditions, query=query)
    def evaluate_test_conditions(self, name, expected_conditions= '', report_conditions = [], where_clause=''):
        '''This queries the test's database and checks that the string provided in expected_conditions returns only True values. If a False is returned, a FAIL result is added to the provided test's submitted data.
            name - string. The name of the test that will fail if the expected conditions are not met.
            expected_conditions - string. A string that will be added to the SELECT portion of a sqlite query. Should return boolean statements, e.g. vout2 == 3, imaina_force < 5, etc.
            report_conditions - list of strings. Column names of the database whose values will be included in the FAIL result.
            where_clause - string. Portion of a sqlite query that goes after WHERE, limiting what rows the database is considering the expected conditions in.'''
        select_string=expected_conditions
        if report_conditions:
            select_string += ', '
            for more_channel_names in report_conditions:
                select_string+=more_channel_names+', '
            select_string = select_string[:-2]
        query = f"SELECT {select_string} FROM {self.get_table_name()}"
        if where_clause:
            query+=f" WHERE {where_clause}"
        results = self.get_database().query(query).fetchall()
        for row in results:
            for excon in row.keys():
                if excon in report_conditions:
                    continue
                if row[excon] != 1:
                    reported_condition = []
                    for recon in report_conditions:
                        reported_condition.append(row[recon])
                    self.register_test_failure(name=name, reason=f"Channel {excon} was found to be False. ", conditions=reported_condition)
        
    def correlate_data(self, name, reference_values=[], test_values=[], spec=None, conditions=None, limits:dict={}):
        '''Compares test values to reference values and compare the output to the limits of the named test.
        args:
            name - string. The name of the test whose limits will be used.
            reference_values - iterable. The base values to which test values will be compared.
            test_values - iterable. The object values whose distance to the reference value will be calculated.
            spec - string. Either '%' or '-'. Determines whether the comparison is made by percentage or by difference.
            conditions - None or dictionary. A dictionary with channel names as keys and channel values as values. Used to report under what circumstances the data was taken. Default is None.'''
        if len(limits) == 0:
            self._corr_results.test_limits[name]=self.get_test_limits(name)
        elif 'upper_limit' in limits.keys() or 'lower_limit' in limits.keys():
            self._corr_results.test_limits[name]=limits
        else:
            raise KeyError(f"The limits argument for correlate_data requires an upper_limit and/or a lower_limit in its keys. Found {[x for x in limits.keys()]}.")
        self._corr_results._correlate_results(name=name, reference_values=reference_values, test_values=test_values, spec=spec, conditions=conditions)
    def get_test_results(self):
        '''Returns a string that reports the Pass/Fail status for all the tests evaluated in the script and the test script as a whole.'''
        res_str = ''
        all_pass = True
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._test_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._test_results else "FAIL"}. ***\n\n'
        return res_str
    def get_corr_results(self):
        '''Returns a string that reports the Pass/Fail status for all the tests correlated in the script and the test script as a whole.'''
        res_str = ''
        all_pass = True
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._corr_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._corr_results else "FAIL"}. ***\n\n'
        return res_str
    def get_test_limits(self, name):
        raise Exception("MASTER TEST TEMPLATE ERROR: This project indicated a use of the TEST_LIMIT plugin but no project specific 'get_test_limits' method was provided.")