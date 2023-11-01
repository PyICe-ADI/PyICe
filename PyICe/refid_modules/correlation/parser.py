from pystdf.IO import Parser
import pystdf.V4

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
    def __init__(self, filenames):
        self._test_name_dict = {}
        for f in filenames:
            with open(f, 'rb') as file:
                p = Parser(inp=file, reopen_fn=None)
                reader = FileReader()
                p.addSink(reader)
                p.parse()
                self.parts = {}
                self.metadata = {}
                stopnow = False
                test_num_dict = {}
                for line in reader.data:
                    master_info = map_data(*line)
                    record_type = type(line[RECORDTYPE])

                    if record_type is pystdf.V4.Mir:
                        if master_info["TST_TEMP"] is None:
                            test_temp = '_25'
                        else:
                            test_temp = '_' + master_info["TST_TEMP"]

                    if record_type is pystdf.V4.Ptr:  # Parametric Test Record - This is a test within this part.
                        if master_info["TEST_TXT"] != '':
                            test_num_dict[master_info['TEST_NUM']] = {
                                'testname': master_info["TEST_TXT"],
                                'units': master_info['UNITS'],
                            }
                            self._test_name_dict[master_info["TEST_TXT"] + test_temp] = {           ## Be
                                'result': master_info['RESULT'],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }
                        else:
                            self._test_name_dict[test_num_dict[master_info['TEST_NUM']]['testname'] + test_temp] = {
                                'result': master_info['RESULT'],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }

                    if record_type is pystdf.V4.Prr:
                        if stopnow:
                            break
                        stopnow = True

    def __getitem__(self, item):
        return self._test_name_dict[item]

        # assert num_devices == 1, "Correlation STDF must have only one DUT record"


if __name__ == '__main__':
    # stuff = STDFParser(filename='example_stdf/lot2.stdf')
    stuff = STDFParser(filenames=[
        '../../../../../projects/stowe_eval/correlation/REVID7/2023-04-14/ENG_LT3390-6J_25C_ENG_ENG_FT_TRIM_LT3390_ETS1UOJU4-00334_20230414_162608.std_1',
        '../../../../../projects/stowe_eval/correlation/REVID7/2022-09-09/5627908_LT33906_-40C_QA100PCT_PRI_QA_COLD_LT3390_BOS-EAGLE2_20220909_071004.std_1'])
    pass
