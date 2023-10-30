from PyICe.refid_modules.correlation.parser import STDFParser
from unit_parse import parser as uparser


class CorrelationAnalyzer:
    def __init__(self, stdf_file, upper_diff=None, lower_diff=None):
        self.all_ate_data = STDFParser(stdf_file)
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

    def _compare(self, testname, bench_data, units, pct):
        """
        Creates a list of offsets between the given bench data and the ATE data of a given test.
        Args:
            testname: Name of the test which
            bench_data: Data collected from which the ATE data will be subtracted.
            units: Units bench_data uses.
            pct: If boolean True, the generated list will be percent difference between ATE and bench.
                Otherwise, absolute.

        Returns:
        A list of absolute differences between the bench data and the ATE data.
        """
        self.ate_data = uparser(self.all_ate_data[testname]['result'] + self.all_ate_data[testname]['units'])
        assert self.ate_data, f'{self.__class__} failed to locate ATE data associated with {testname}.'
        error = []
        if hasattr(bench_data, '__iter__'):
            for datapoint in bench_data:
                if isinstance(datapoint, str):
                    datapoint = datapoint + units
                else:
                    datapoint = str(datapoint) + units
                if pct:
                    datap = uparser(datapoint)
                    diff = 1 - (datap.to_base_units() / self.ate_data.to_base_units())
                    assert diff.dimensionless
                    error.append(diff.m)
                else:
                    datap = uparser(datapoint)
                    diff = datap.to_base_units() - self.ate_data.to_base_units()
                    assert diff.to_base_units().u == datap.to_base_units().u
                    error.append(diff.m)
        else:
            if isinstance(bench_data, str):
                bench_data = bench_data + units
            else:
                bench_data = str(bench_data) + units
            if pct:
                datap = uparser(bench_data)
                diff = 1 - (datap.to_base_units() / self.ate_data.to_base_units())
                assert diff.dimensionless
                error.append(diff.m)
            else:
                datap = uparser(bench_data)
                diff = datap.to_base_units() - self.ate_data.to_base_units()
                assert diff.to_base_units().u == datap.to_base_units().u
                error.append(diff.m)
        return error

    def verdict(self, testname, bench_data, units, upper_diff=None, lower_diff=None, percent=None):
        """
        Determines if the difference between bench data and the ATE data of given data for a given test stays within
        the given limits.
        Args:
            testname:Name of the ATE test being compared. e.g. 'CH1 VOUT'
            bench_data: Either a string or an iterable object of strings. e.g. '5V' or ['1A','2A']
            units: A string that represents the units the bench data is presented with.
            upper_diff:Maximum absolute difference that will pass above the ATE value. Leave as None if using 'percent.'
            lower_diff:Minimum absolute difference that will pass below the ATE value. Leave as None if using 'percent.'
            percent:Percent of ATE value all bench data must be within to pass. Leave as None if using absolute limits.

        Returns:
        A boolean based on whether the difference between the bench data and the ATE data remained within the given
        limits.
        """
        errors = self._compare(testname, bench_data, units, pct=percent)
        if percent:
            assert upper_diff is None and lower_diff is None
            upper_diff = self.ate_data * percent * 0.01
            lower_diff = -1 * upper_diff
        elif self.upper_diff is not None or self.lower_diff is not None:
            upper_diff = self.upper_diff
            lower_diff = self.lower_diff
        assert (upper_diff is not None) and (lower_diff is not None), f'Limits are not defined for {self}'
        pass_above = True if ((upper_diff is None) or len([err for err in errors if err > upper_diff]) == 0) else False
        pass_below = True if ((lower_diff is None) or len([err for err in errors if err < lower_diff]) == 0) else False
        if pass_above and pass_below:
            # Print victory message.
            return True
        else:
            # Print failure message along with most egregious error.
            return False
