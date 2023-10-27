from pystdf.IO import Parser
import pystdf.V4
import csv

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

if __name__ == '__main__':
    # STDFParser(filename='example_stdf/lot2.stdf')
    STDFParser(filename='../../../../../projects/stowe_eval/correlation/REVID7/2022-01-05/5627908_LT3390_25C_CLASS_PRI_FT_TRIM_LT3390_BOS-EAGLE1_20220105_102154.std_1')

