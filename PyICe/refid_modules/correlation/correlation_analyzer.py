from unit_parse import parser as uparser


# Comparison of 1 medium of data collection to another
class CorrelationAnalyzer:
    def __init__(self, target_data_dict=None, upper_diff=None, lower_diff=None):
        # def __init__(self, stdf_file, upper_diff=None, lower_diff=None):
        if target_data_dict is None:
            self.all_target_data = input("Make your dictionary here")
        else:
            self.all_target_data = target_data_dict
        self.upper_diff = upper_diff
        self.lower_diff = lower_diff

    @property
    def upper_diff(self):
        return self._upper_diff

    @upper_diff.setter
    def upper_diff(self, value):
        self._upper_diff = value

    @property
    def lower_diff(self):
        return self._lower_diff

    @lower_diff.setter
    def lower_diff(self, value):
        self._lower_diff = value

    def _compare(self, target_data, bench_data, units, pct):
        """
        Creates a list of offsets between the given bench data and the ATE data of a given test.
        Args:
            target_data:
            bench_data: Data collected from which the ATE data will be subtracted.
            units: Units bench_data uses.
            pct: If boolean True, the generated list will be percent difference between ATE and bench.
                Otherwise, absolute.

        Returns:
        A list of absolute differences between the bench data and the ATE data.
        """
        error = []
        if not isinstance(bench_data, list) or not isinstance(bench_data, set):
            bench_data = [bench_data]
        for datapoint in bench_data:
            if isinstance(datapoint, str):
                datapoint = datapoint + units
            else:
                datapoint = str(datapoint) + units
            datap = uparser(datapoint)
            if pct:
                diff = (datap.to_base_units() / target_data.to_base_units()).m - 1
            else:
                diff = (datap.to_base_units() - target_data.to_base_units()).m
            error.append(diff)
        return error

    def _parsed_data(self, testname):
        """
        This finds ate data of the given test name transforms it into a parsed object
        Args:
            testname: Str. Name of the test found in the ate data's stdf file.

        Returns:
            A parse object with an associated magnitude and unit.
        """
        if isinstance(self.all_target_data[testname]['result'], str):
            ate_data = self.all_target_data[testname]['result'] + self.all_target_data[testname]['units']
        else:
            ate_data = str(self.all_target_data[testname]['result']) + self.all_target_data[testname]['units']
        parsed = uparser(ate_data)
        if parsed is None:
            parsed = uparser(ate_data.upper())  # Last ditch effort to make this work.
            assert parsed is not None, f'{self.__class__} failed to locate ATE data associated with {testname}.'
        return parsed

    def _set_limits(self, target_data=None, units=None, upper_diff=None, lower_diff=None, percent=None):
        """
        Calculates limits if percent, assigns limits if presented at initialization, and passes through values
        if presented now.
        Args:
            target_data:
            units:
            upper_diff: Upper limit from expected value that will still pass.
            lower_diff :Lower limit from expected value that will still pass.
            percent: Percent away from expected value that will still pass.

        Returns:
        Two values or a value and a None
        """
        u_diff = l_diff = None
        if percent:
            assert upper_diff is None and lower_diff is None
            u_diff = target_data * percent * 0.01
            l_diff = -1 * u_diff
        elif self.upper_diff is not None or self.lower_diff is not None:
            u_diff = self.upper_diff
            l_diff = self.lower_diff
        if upper_diff is not None:
            u_diff = uparser(str(upper_diff) + units).m
        if lower_diff is not None:
            l_diff = uparser(str(lower_diff) + units).m
        assert (u_diff is not None) or (l_diff is not None), f'Limits are not defined for {self}'
        return u_diff, l_diff

    def verdict(self, testname, bench_data, units, temperature=None, upper_diff=None, lower_diff=None, percent=None):
        """
        Determines if the difference between bench data and the ATE data of given data for a given test stays within
        the given limits.
        Args:
            testname:Name of the ATE test being compared. e.g. 'CH1 VOUT'
            bench_data: Data to compare to ATE records. Can be either a value or a string, as an individual point
            or as a list.
                e.g. 5 or '5' or [1,2] or ['1','2']
            units: A string that represents the units the bench data is presented with.
                e.g. 'A' or 'ohms'
            temperature: Str or Num. Temperature in Celsius at which data was collected.
            upper_diff:Maximum absolute difference in base units that will pass above the ATE value.
                Leave as None if using 'percent.'
            lower_diff:Minimum absolute difference in base units that will pass below the ATE value.
                Leave as None if using 'percent.'
            percent:Percent of ATE value all bench data must be within to pass.
                Leave as None if using absolute limits.

        Returns:
        A boolean based on whether the difference between the bench data and the ATE data remained within the given
        limits.
        """
        target_data = self._parsed_data(testname + '_25') if temperature is None else self._parsed_data(
            testname + '_' + str(temperature))
        errors = self._compare(target_data, bench_data, units, percent)
        upper_diff, lower_diff = self._set_limits(target_data.m, units, upper_diff, lower_diff, percent)
        upper_errors = [] if upper_diff is None else [err for err in errors if err > upper_diff]
        lower_errors = [] if lower_diff is None else [err for err in errors if err < lower_diff]
        pass_above = True if ((upper_diff is None) or len(upper_errors) == 0) else False
        pass_below = True if ((lower_diff is None) or len(lower_errors) == 0) else False
        if pass_above and pass_below:
            rslt_str = ''
            rslt_str += f'{testname} passed'
            rslt_str += f' at {temperature}.\n' if temperature else ' at room temperature.\n'
            print(rslt_str)
            return True
        else:
            rslt_str = ''
            rslt_str += f'{testname} failed'
            rslt_str += f' at {temperature}.\n' if temperature else ' at room temperature.\n'
            if upper_errors:
                rslt_str += f'Upper Limit = +{upper_diff}\tMax Diff = {max(upper_errors)}\n'
            if lower_errors:
                rslt_str += f'Lower Limit = {lower_diff}\tMax Diff = {min(lower_errors)}'
            print(rslt_str)
            return False

    def conjure_a_json(self, *args, **kwargs):
        """
        Throw in some basic traceability (test name, date, and dut id, I guess?) and follow up with the verdict of all
        the tests involved in the script.

        Args:
            *args: Don't think this'll be too useful, but kwargs looked so lonely.
            **kwargs: Extra info you want to include in the results. It's up to you!

        Returns:
        You better believe there'll be a json at the end of all this.
        """
        pass
