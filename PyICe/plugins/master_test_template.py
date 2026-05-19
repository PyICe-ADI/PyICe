class Master_Test_Template():
    ###
    # SCRIPT METHODS
    ###
    def reconfigure(self, read_function, write_function, value):
        """Optional method used during customize() if changes are made to the DUT on a particular test in a suite.

        Unwound after test's collect at each temperature.
        read_function and write_function should be conjugate methods of a particular channel to help the system unwind after _this_ test.
        "value" is the value to which the channel will be assigned for _this_ test.

        Args:
            read_function: Callable for reading the channel.
            value: Value to set.
            write_function: Callable for writing the channel.
        """
        self._channel_reconfiguration_settings.append(
            (read_function(), write_function, value))

    def _reconfigure(self):
        """Save channel setting before writing to value."""
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(new)

    def _restore(self):
        """Undo any changes made by reconfigure."""
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(old)

    def customize(self):
        """Optional method to alter the logger before the test begins."""

    def declare_bench_connections(self):
        """Optional method to log the setup needed to run the test. Plugin required."""

    def collect(self):
        """Mandatory method to operate the bench and collect the data."""

    def plot(self):
        """Optional method to retrieve the data collected and create plots. Can be run over and over once a collect has run. User must return a list or tuple of plots and/or pages, or an individual LTC_plot.Page, or a single LTC_plot.plot.

        Returns:
            Result value.
        """
        return []

    def _modify_metalogger(self):
        """Method used to make any changes to the metalog before it is merged with a sqlite table. Not to be used itself, but to be overwritten in a project specific test_template. Plugin required."""

    ###
    # GET METHODS
    ###
    def get_channels(self):
        """Return the channels.

        Returns:
            Result value.
        """
        return self._logger

    def get_name(self):
        """Return the name.

        Returns:
            Result value.
        """
        return self._name

    def get_project_folder_name(self):
        """Return the project folder name.

        Returns:
            Result value.
        """
        return self.project_folder_name

    def get_module_path(self):
        """Return the module path.

        Returns:
            Result value.
        """
        if hasattr(self, '_module_path'):
            return self._module_path
        else:
            print(
                f"Attempted to access the module path for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")

    def get_debug(self):
        """Return the debug.

        Returns:
            Result value.
        """
        return self._debug

    def get_verbose(self):
        """Return the verbose.

        Returns:
            Result value.
        """
        return self.verbose

    def get_db_file(self):
        """Return the db file.

        Returns:
            Result value.
        """
        if hasattr(self, '_db_file'):
            return self._db_file
        else:
            print(
                f"Attempted to access the database file for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")

    def get_database(self):
        """Return the database.

        Returns:
            Result value.
        """
        if hasattr(self, '_db'):
            return self._db
        else:
            print(
                f"Attempted to access the database for {self.get_name()}. It's only intended to be accessible from inside the plot() or evaluate() methods.")

    def get_table_name(self):
        """Return the table name.

        Returns:
            Result value.
        """
        if hasattr(self, '_table_name'):
            return self._table_name
        else:
            print(
                f'No table name has been assigned to {self.get_name()} at this time.')

    def get_plot_filepath(self):
        """Return the plot filepath.

        Returns:
            Result value.
        """
        if hasattr(self, '_plot_filepath'):
            return self._plot_filepath
        else:
            print(
                f'No file path for plot locations has been assigned to {self.get_name()} at this time.')

    def get_bench_image_locations(self):
        """Return the bench image locations.

        Returns:
            Result value.

        Raises:
            Exception: On error condition.
        """
        if hasattr(self, 'bench_image_locations'):
            return self.bench_image_locations
        else:
            raise Exception(
                "PyICe Master Test Template: You said you wanted a visual representation of your lab bench. You'll need to define bench_image_locations in your Test_Template.")

    ###
    # EVALUATION/CORRELATION METHODS
    ###
    def evaluate_results(self):
        """Optional evaluate_results method placeholder."""

    def correlate_results(self):
        """Optional correlate_results method placeholder."""

    def declare_test(self, name: str, lower_limit=None,
                     upper_limit=None, **kwargs):
        """Optional means to manually set declarations apart from the evaluation methods.

        Args:
            **kwargs: Additional keyword arguments.
            lower_limit: Lower limit.
            name: Name identifier.
            upper_limit: Upper limit.
        """
        established_declarations = self._test_results.test_limits
        if name not in established_declarations.keys():
            established_declarations[name] = {
                'lower_limit': lower_limit, 'upper_limit': upper_limit, **kwargs}
        else:
            expected = {'lower_limit': lower_limit, 'upper_limit': upper_limit, **kwargs}
            assert established_declarations[name] == expected, (
                f"***Master Test Template Error*** Trying to change {name}'s declarations from"
                f" {established_declarations[name]} to lower_limit:{lower_limit}, upper_limit:{upper_limit}, {kwargs}"
            )

    def evaluate_rawdata(self, name, data, conditions=None):
        """Compare submitted data to limits for the named test.

        Args:
            name: The name of the test whose limits will be used.
            data: Boolean or iterable object to compare against limits.
            conditions: Dictionary of channel names to values for reporting context, or None.
        """
        if name not in self._test_results.test_limits.keys():
            self.declare_test(name, **self.get_test_limits(name))
        self._test_results._evaluate_list(
            name=name, iter_data=data, conditions=conditions)

    def evaluate_query(self, name, query):
        """Compare submitted query results to limits for the named test.

        Args:
            name: The name of the test whose limits will be used.
            query: SQL query string to execute against the database.
        """
        if name not in self._test_results.test_limits.keys():
            self.declare_test(name, **self.get_test_limits(name))
        self.get_database().query(query)
        self._test_results._evaluate_database(
            name=name, database=self.get_database())

    def evaluate_db(self, name):
        """Evaluate a pre-massaged SQLite database against limits for the named test.

        Args:
            name: The name of the test whose limits will be used.
        """
        if name not in self._test_results.test_limits.keys():
            self.declare_test(name, **self.get_test_limits(name))
        self._test_results._evaluate_database(
            name=name, database=self.get_database())

    def evaluate(self, name, values, conditions=None, where_clause=''):
        """Compare data from a SQLite database to a named test with more control over the query.

        Args:
            name: The name of the test whose limits will be used.
            values: Column name(s) to select and evaluate.
            conditions: List of additional column names for grouping, or None.
            where_clause: Optional SQL WHERE clause to filter rows.
        """
        if conditions is None:
            conditions = []
        condition_str = ''
        for condition in conditions:
            condition_str += f",{condition}"
        query_str = f'SELECT {values}{condition_str} FROM {self.get_table_name()} ' + (
            'WHERE ' + where_clause if where_clause else '')
        self.evaluate_query(name, query=query_str)

    def register_test_failure(self, name, reason, conditions=None, query=None):
        """Submit a result for a test that is considered a FAIL so the test, regardless of other data submitted, will result in a FAIL overall.

        Args:
            conditions: Conditions.
            name: Name identifier.
            query: Query.
            reason: Reason.
        """
        self._test_results._register_test_failure(
            name=name, reason=reason, conditions=conditions, query=query)

    def evaluate_test_conditions(
            self, name, expected_conditions='', report_conditions=[], where_clause=''):
        """Check that expected conditions return only True values in the test database.

        Args:
            name: The name of the test that will fail if conditions are not met.
            expected_conditions: SQL SELECT expression returning booleans (e.g. 'vout2 == 3').
            report_conditions: Column names whose values will be included in FAIL results.
            where_clause: Optional SQL WHERE clause to limit evaluated rows.
        """
        select_string = expected_conditions
        if report_conditions:
            select_string += ', '
            for more_channel_names in report_conditions:
                select_string += more_channel_names + ', '
            select_string = select_string[:-2]
        query = f"SELECT {select_string} FROM {self.get_table_name()}"
        if where_clause:
            query += f" WHERE {where_clause}"
        results = self.get_database().query(query).fetchall()
        for row in results:
            for excon in row.keys():
                if excon in report_conditions:
                    continue
                if row[excon] != 1:
                    reported_condition = []
                    for recon in report_conditions:
                        reported_condition.append(row[recon])
                    self.register_test_failure(
                        name=name,
                        reason=f"Channel {excon} was found to be False. ",
                        conditions=reported_condition)

    def correlate_data(self, name, reference_values=None,
                       test_values=None, spec=None, conditions=None):
        """Compare test values to reference values and evaluate against named test limits.

        Args:
            name: The name of the test whose limits will be used.
            reference_values: Base values to compare against.
            test_values: Values whose distance to reference will be calculated.
            spec: Either '%' for percentage or '-' for difference comparison.
            conditions: Dictionary of channel names to values for reporting context, or None.
        """
        if reference_values is None:
            reference_values = []
        if test_values is None:
            test_values = []
        self._corr_results.test_limits[name] = self.get_test_limits(name)
        self._corr_results._correlate_results(
            name=name,
            reference_values=reference_values,
            test_values=test_values,
            spec=spec,
            conditions=conditions)

    def get_test_results(self):
        """Returns a string that reports the Pass/Fail status for all the tests evaluated in the script and the test script as a whole.

        Returns:
            Result value.
        """
        res_str = ''
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._test_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._test_results else "FAIL"}. ***\n\n'
        return res_str

    def get_corr_results(self):
        """Returns a string that reports the Pass/Fail status for all the tests correlated in the script and the test script as a whole.

        Returns:
            Result value.
        """
        res_str = ''
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._corr_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._corr_results else "FAIL"}. ***\n\n'
        return res_str

    def get_test_limits(self, name):
        """Return the test limits.

        Args:
            name: Name identifier.

        Raises:
            Exception: On error condition.
        """
        raise Exception(
            "MASTER TEST TEMPLATE ERROR: This project indicated a use of the TEST_LIMIT plugin but no project specific 'get_test_limits' method was provided.")
