from pystdf.IO import Parser
import pystdf.V4
from PyICe.data_utils import stdf_utils

RECORDTYPE = 0


class FileReader:
    def __init__(self):
        self.data = []

    def after_send(self, dataSource, data):
        self.data.append(data)

    def write(self, line):
        self.data.append(line)

    def flush(self):
        pass


def map_data(record_type, data):
    return {k: v for (k, v) in zip(record_type.fieldNames, data)}


class STDFParser:
    def __init__(self, filename):
        self._test_name_dict = {}
        with open(filename, 'rb') as file:
            p = Parser(inp=file, reopen_fn=None)
            reader = FileReader()
            p.addSink(reader)
            p.parse()
            self.parts = {}
            self.metadata = {}
            for line in reader.data:
                master_info = map_data(*line)
                record_type = type(line[RECORDTYPE])
                if record_type is pystdf.V4.Ptr:  # Parametric Test Record - This is a test within this part.
                    self._test_name_dict[master_info['TEST_TXT']] = {
                        'upper_limit': master_info['HI_LIMIT'],
                        'lower_limit': master_info['LO_LIMIT'],
                        'result': master_info['RESULT'],
                        'units': master_info['UNITS'],
                    }

    def __getitem__(self, item):
        return self._test_name_dict[item]

        # assert num_devices == 1, "Correlation STDF must have only one DUT record"

import csv
class ATE_index_utils:                          ##Not really a part of this parser module, but will be part of the correlation enterprise as a whole.
    def __init__(self):
        self.index_file = "file/location.csv"

    def get_stdf_location(self, dut_id):
        with open(self.index_file, 'r') as index_file:
            csvreader = csv.reader(index_file)
            for row in csvreader:
                if row[0] is dut_id:
                    stdf_file = row[0]
                    break
        return stdf_file

    def append_index(self, dut_id, stdf_file_location):
        with open(self.index_file, 'a') as index_file:
            csvwriter = csv.writer(index_file)
            csvwriter.writerow([dut_id, stdf_file_location])

class do_i_pass_corr:
    def __init__(self, dut_id, testname, bench_data, upper_diff=None, lower_diff=None, percent=None):
        stdf_file   = ATE_indexer(dut_id)
        ate_data    = STDF_Parser(stdf_file)[testname]['result']
        errors      = self.compare(ate_data, bench_data)
        return self.verdict(errors, upper_diff, lower_diff, percent*.01)

    def compare(ate_data, bench_data):
        error = []
        if hasattr(bench_data, '__iter__'):
            for datapoint in data:
                error.append(datapoint - self.corr_data)
        else:
            error.append(data - self.corr_data)
        return error

    def verdict(self, errors, upper_diff, lower_diff, percent):
        if percent:
            assert upper_diff is None and lower_diff is None
            upper_diff = self.ate_test_data * percent
            lower_diff = -1 * upper_diff
        elif upper_diff is None and lower_diff is None:
            raise 'hey, we have a problem. what are the limits? I have no clue.'
        pass_above = True if ((upper_diff is None) or len([err for err in error if err>upper_diff])==0) else False
        pass_below = True if ((lower_diff is None) or len([err for err in error if err<lower_diff])==0) else False
        if pass_above and pass_below:
            ## Print victory message.
            return True
        else:
            ## Print failure message along with most egregious error.
            return False


if __name__ == '__main__':
    STDFParser(filename='example_stdf/lot2.stdf')

### e.g.
# corr = do_i_pass_corr('DUT1', 'ch1_vout', [1.6,1.66,1.6], percent=2)





