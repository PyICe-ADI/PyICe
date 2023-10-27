from PyICe.refid_modules.correlation.ATE_index_utils import ATE_index_utils
from PyICe.refid_modules.correlation.parser import STDFParser
from unit_parse import parser as uparser

class do_i_pass_corr:
    def __init__(self, dut_id, testname, bench_data, upper_diff=None, lower_diff=None, percent=None):
        ATE_utils = ATE_index_utils()
        stdf_file = ATE_utils.get_stdf_location(dut_id)
        ate_data = uparser(STDFParser(stdf_file)[testname]['result']+STDFParser(stdf_file)[testname]['units'])
        errors = self.compare(ate_data, bench_data)
        if percent:
            assert upper_diff is None and lower_diff is None
            upper_diff = ate_data * percent*0.01
            lower_diff = -1 * upper_diff
        assert (upper_diff is not None) and (lower_diff is not None), f'Limits are not defined for {self}'
        self.verdict(errors, upper_diff, lower_diff)

    @staticmethod
    def compare(ate_data, bench_data):
        error = []
        if hasattr(bench_data, '__iter__'):
            for datapoint in bench_data:
                error.append(datapoint - ate_data)
        else:
            error.append(bench_data - ate_data)
        return error

    @staticmethod
    def verdict(errors, upper_diff, lower_diff):
        pass_above = True if ((upper_diff is None) or len([err for err in errors if err > upper_diff]) == 0) else False
        pass_below = True if ((lower_diff is None) or len([err for err in errors if err < lower_diff]) == 0) else False
        if pass_above and pass_below:
            # Print victory message.
            return True
        else:
            # Print failure message along with most egregious error.
            return False