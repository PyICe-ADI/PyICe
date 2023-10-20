from pystdf.IO import Parser
import pystdf.V4
from PyICe.data_utils import stdf_utils

RECORDTYPE = 0
class FileReader:
    def __init__(self):
        self.data = []
    def after_send(self, dataSource, data):
        self.data.append(data)
    def write(self,line):
        self.data.append(line)
    def flush(self):
        pass


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
                record_type = type(line[RECORDTYPE])
                if record_type is pystdf.V4.Ptr:                        # Parametric Test Record - This is a test within this part.
                    self._test_name_dict[line[1][6]] = {
                        'upper_limit': line[1][13],
                        'lower_limit': line[1][12],
                        'result': line[1][5],
                        'units': line[1][14],
                    }

    def __getitem__(self, item):
        return self._test_name_dict[item]



        # assert num_devices == 1, "Correlation STDF must have only one DUT record"


if __name__ == '__main__':
    STDFParser(filename='example_stdf/lot2.stdf')