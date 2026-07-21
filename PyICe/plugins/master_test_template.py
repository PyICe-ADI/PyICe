"""Master test template plugin.

>>> from PyICe.plugins.master_test_template import Master_Test_Template

"""
class Master_Test_Template():  # pylint: disable=no-member; this is a mixin/template class whose attributes (_logger, _name, _test_results, _corr_results, _channel_reconfiguration_settings, project_folder_name, _debug, verbose) are set by Plugin_Manager at runtime
    """Master_ test_ template.

    >>> from PyICe.plugins.master_test_template import Master_Test_Template
    >>> Master_Test_Template is not None
    True

    """
    ###
    # SCRIPT METHODS
    ###
    def reconfigure(self, read_function, write_function, value):
        """Optional method used during customize() if changes are made to the DUT on a particular test in a suite.

        Unwound after test's collect at each temperature.
        read_function and write_function should be conjugate methods of a particular channel to help the system unwind after _this_ test.
        "value" is the value to which the channel will be assigned for _this_ test.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'reconfigure')
        True

        Args:
            read_function: Callable for reading the channel.
            value: Value to set.
            write_function: Callable for writing the channel.
        """
        self._channel_reconfiguration_settings.append(
            (read_function(), write_function, value))

    def _reconfigure(self):
        """Save channel setting before writing to value.

        Internal implementation detail; see the public API for usage.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, '_reconfigure')
        True

        """
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(new)

    def _restore(self):
        """Undo any changes made by reconfigure.

        Internal implementation detail; see the public API for usage.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, '_restore')
        True

        """
        for (old, write_function, new) in self._channel_reconfiguration_settings:
            write_function(old)

    def customize(self):
        """Optional method to alter the logger before the test begins.

        Captures data for later analysis or replay.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'customize')
        True

        """

    def declare_bench_connections(self):
        """Optional method to log the setup needed to run the test. Plugin required.

        Captures data for later analysis or replay.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'declare_bench_connections')
        True

        """

    def collect(self):
        """Mandatory method to operate the bench and collect the data.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'collect')
        True

        """

    def plot(self):
        """Optional method to retrieve the data collected and create plots. Can be run over and over once a collect has run. User must return a list or tuple of plots and/or pages, or an individual LTC_plot.Page, or a single LTC_plot.plot.
        Configures or updates the plot with the specified parameters.

        Generates or configures a visual representation of the data.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'plot')
        True

        Returns:
            The plot result.
        """
        return []

    def _modify_metalogger(self):
        """Method used to make any changes to the metalog before it is merged with a sqlite table. Not to be used itself, but to be overwritten in a project specific test_template. Plugin required.

        Internal implementation detail; see the public API for usage.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, '_modify_metalogger')
        True

        """

    ###
    # GET METHODS
    ###
    def get_channels(self):
        """Return the current channels.
        Returns the stored channels value from the object's internal state.
        Returns the stored channels from the object's internal state.

        Returns the stored channels from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_channels')
        True

        Returns:
            The current channels.
        """
        return self._logger

    def get_name(self):
        """Return the current name.
        Returns the stored name value from the object's internal state.
        Returns the stored name from the object's internal state.

        Returns the stored name from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_name')
        True

        Returns:
            The current name.
        """
        return self._name

    def get_project_folder_name(self):
        """Return the project folder name.
        Returns the stored project folder name value from the object's
        internal state.
        Returns the stored project folder name from the object's internal
        state.

        Returns the stored project folder name from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_project_folder_name')
        True

        Returns:
            The current project folder name.
        """
        return self.project_folder_name

    def get_module_path(self):
        """Return the module path.
        Returns the stored module path value from the object's internal state.
        Returns the stored module path from the object's internal state.

        Returns the stored module path from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_module_path')
        True

        Returns:
            The current module path.
        """
        if hasattr(self, '_module_path'):
            return self._module_path
        else:
            print(
                f"Attempted to access the module path for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")

    def get_debug(self):
        """Return the current debug.
        Returns the stored debug value from the object's internal state.
        Returns the stored debug from the object's internal state.

        Returns the stored debug from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_debug')
        True

        Returns:
            The current debug.
        """
        return self._debug

    def get_verbose(self):
        """Return the current verbose.
        Returns the stored verbose value from the object's internal state.
        Returns the stored verbose from the object's internal state.

        Returns the stored verbose from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_verbose')
        True

        Returns:
            The current verbose.
        """
        return self.verbose

    def get_db_file(self):
        """Return the db file.
        Returns the stored db file value from the object's internal state.
        Returns the stored db file from the object's internal state.

        Returns the stored db file from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_db_file')
        True

        Returns:
            The current db file.
        """
        if hasattr(self, '_db_file'):
            return self._db_file
        else:
            print(
                f"Attempted to access the database file for {self.get_name()}. It would be created upon adding a test to the plugin manager but you didn't get that far.")

    def get_database(self):
        """Return the current database.
        Returns the stored database value from the object's internal state.
        Returns the stored database from the object's internal state.

        Returns the stored database from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_database')
        True

        Returns:
            The current database.
        """
        if hasattr(self, '_db'):
            return self._db
        else:
            print(
                f"Attempted to access the database for {self.get_name()}. It's only intended to be accessible from inside the plot() or evaluate() methods.")

    def get_table_name(self):
        """Return the table name.
        Returns the stored table name value from the object's internal state.
        Returns the stored table name from the object's internal state.

        Returns the stored table name from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_table_name')
        True

        Returns:
            The current table name.
        """
        if hasattr(self, '_table_name'):
            return self._table_name
        else:
            print(
                f'No table name has been assigned to {self.get_name()} at this time.')

    def get_plot_filepath(self):
        """Return the plot filepath.
        Configures or updates the plot with the specified parameters.
        Returns the stored plot filepath from the object's internal state.

        Returns the stored plot filepath from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_plot_filepath')
        True

        Returns:
            The current plot filepath.
        """
        if hasattr(self, '_plot_filepath'):
            return self._plot_filepath
        else:
            print(
                f'No file path for plot locations has been assigned to {self.get_name()} at this time.')

    def get_bench_image_locations(self):
        """Return the bench image locations.
        Returns the stored bench image locations value from the object's
        internal state.
        Returns the stored bench image locations from the object's internal
        state.

        Returns the stored bench image locations from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_bench_image_locations')
        True

        Returns:
            The current bench image locations.

        Raises:
            Exception: If an unexpected error occurs.
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
        """Optional evaluate_results method placeholder.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate_results')
        True

        """

    def correlate_results(self):
        """Optional correlate_results method placeholder.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'correlate_results')
        True

        """

    def declare_test(self, name: str, lower_limit=None,
                     upper_limit=None, **kwargs):
        """Optional means to manually set declarations apart from the evaluation methods.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'declare_test')
        True

        Args:
            **kwargs: Additional keyword arguments.
            lower_limit: Lower limit to use.
            name: Name identifier.
            upper_limit: Upper limit to use.
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

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate_rawdata')
        True

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

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate_query')
        True

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

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate_db')
        True

        Args:
            name: The name of the test whose limits will be used.
        """
        if name not in self._test_results.test_limits.keys():
            self.declare_test(name, **self.get_test_limits(name))
        self._test_results._evaluate_database(
            name=name, database=self.get_database())

    def evaluate(self, name, values, conditions=None, where_clause=''):
        """Compare data from a SQLite database to a named test with more control over the query.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate')
        True

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

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'register_test_failure')
        True

        Args:
            conditions: Conditions to use.
            name: Name identifier.
            query: Query or command string to send.
            reason: Reason to use.
        """
        self._test_results._register_test_failure(
            name=name, reason=reason, conditions=conditions, query=query)

    def evaluate_test_conditions(
            self, name, expected_conditions='', report_conditions=[], where_clause=''):
        """Check that expected conditions return only True values in the test database.

        Supports the ``Master_Test_Template`` workflow by performing the described operation.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'evaluate_test_conditions')
        True

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
        """Compare measured test values against reference values and evaluate against test limits.

        Computes the deviation between each pair of (reference, test) values
        using the mode specified by ``spec``, then checks whether the deviation
        falls within the named test's limits (as returned by ``get_test_limits(name)``).

        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'correlate_data')
        True

        Args:
            name: Key into the test limits table (from ``get_test_limits``).
                Identifies which min/max limits to evaluate against.
            reference_values: Golden/expected values, typically from
                characterization data or a datasheet. List of numeric values.
            test_values: Measured values from the current test run. Must be
                the same length as reference_values.
            spec: Comparison mode. ``'%'`` computes percentage deviation
                ``(test - ref) / ref * 100``; ``'-'`` computes absolute
                difference ``test - ref``.
            conditions: Optional dict of {channel_name: value} pairs
                describing the operating conditions (e.g. temperature, supply
                voltage) under which the measurement was taken. Used for
                reporting context only.
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
        Returns the stored test results from the object's internal state.

        Returns the stored test results from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_test_results')
        True

        Returns:
            The current test results.
        """
        res_str = ''
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._test_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._test_results else "FAIL"}. ***\n\n'
        return res_str

    def get_corr_results(self):
        """Returns a string that reports the Pass/Fail status for all the tests correlated in the script and the test script as a whole.
        Returns the stored corr results from the object's internal state.

        Returns the stored corr results from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_corr_results')
        True

        Returns:
            The current corr results.
        """
        res_str = ''
        res_str += f'*** Module {self.get_name()} ***\n'
        res_str += f'{self._corr_results}'
        res_str += f'*** Module {self.get_name()} Summary {"PASS" if self._corr_results else "FAIL"}. ***\n\n'
        return res_str

    def get_test_limits(self, name):
        """Return the test limits.

        Returns the stored test limits from the object's internal state.


        >>> from PyICe.plugins.master_test_template import Master_Test_Template
        >>> hasattr(Master_Test_Template, 'get_test_limits')
        True

        Args:
            name: Name identifier.

        Raises:
            Exception: If an unexpected error occurs.
        """
        raise Exception(
            "MASTER TEST TEMPLATE ERROR: This project indicated a use of the TEST_LIMIT plugin but no project specific 'get_test_limits' method was provided.")
