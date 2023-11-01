from pystdf.IO import Parser
import pystdf.V4

RECORDTYPE = 0


class FileReader:
    def __init__(self):
        self.data = []
        self.count=0
        self._multitest = False
        self.valid_ptr=0

    def after_send(self, dataSource, data):
        self.data.append(data)
        rectype, fields = data
        if rectype is pystdf.V4.Pir:
            self.valid_ptr = 0
        if rectype is pystdf.V4.Ptr and fields['TEST_FLG'] is 0:
            self.valid_ptr +=1
        if rectype is pystdf.V4.Prr and self.valid_ptr:
            self.count +=1

    def after_complete(self, dataSrc):
        if self.count >1:
            self._multitest =True

    def write(self, line):
        self.data.append(line)

    def flush(self):
        pass


def map_data(record_type, data):
    return {k: v for (k, v) in zip(record_type.fieldNames, data)}


class STDFParser:
    def __init__(self, filenames):      ## We might need to expand on this. Like, [(filename, dut #),(filename, dut #)]
        self._test_name_dict = {}       ## And how would we do this without the indexer?
        self._multidut = False
        # if number of valid Prrs in stdf >1, self._multidut=True
        for f in filenames:
            with open(f, 'rb') as file:
                p = Parser(inp=file, reopen_fn=None)
                reader = FileReader()
                p.addSink(reader)
                p.parse()
                self.parts = {}
                self.metadata = {}
                test_num_dict = {}
                for line in reader.data:
                    master_info = map_data(*line)
                    record_type = type(line[RECORDTYPE])
                    if record_type is pystdf.V4.Mir:
                        if master_info["TST_TEMP"] is None:
                            test_temp = '_25'
                        else:
                            test_temp = '_' + master_info["TST_TEMP"]
                    if record_type is pystdf.V4.Pir:
                        valid_ptr = 0
                    if record_type is pystdf.V4.Ptr:  # Parametric Test Record - This is a test within this part.
                        if master_info["TEST_TXT"] != '':
                            test_num_dict[master_info['TEST_NUM']] = {
                                'testname': master_info["TEST_TXT"],
                                'lo_limit': master_info["LO_LIMIT"],
                                'hi_limit': master_info["HI_LIMIT"],
                                'units': master_info['UNITS'],
                            }
                            self._test_name_dict[master_info["TEST_TXT"] + test_temp] = {           ## Be careful about str vs number equivalence.
                                'result': master_info['RESULT'],
                                'lo_limit': master_info["LO_LIMIT"],
                                'hi_limit': master_info["HI_LIMIT"],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }
                        else:
                            self._test_name_dict[test_num_dict[master_info['TEST_NUM']]['testname'] + test_temp] = {
                                'result': master_info['RESULT'],
                                'lo_limit':  test_num_dict[master_info['TEST_NUM']]['lo_limit'],
                                'hi_limit':  test_num_dict[master_info['TEST_NUM']]['hi_limit'],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }

    def __getitem__(self, item):
        return self._test_name_dict[item]

        # assert num_devices == 1, "Correlation STDF must have only one DUT record"


if __name__ == '__main__':
    # stuff = STDFParser(filename='example_stdf/lot2.stdf')
    stuff = STDFParser(filenames=[
        '../../../../../projects/stowe_eval/correlation/REVID7/2023-04-14/ENG_LT3390-6J_25C_ENG_ENG_FT_TRIM_LT3390_ETS1UOJU4-00334_20230414_162608.std_1',])
        #'../../../../../projects/stowe_eval/correlation/REVID7/2023-04-14/ENG_LT3390-6J_25C_ENG_ENG_FT_TRIM_LT3390_ETS1UOJU4-00334_20230414_162608.std_1',
        #'../../../../../projects/stowe_eval/correlation/REVID7/2022-09-09/5627908_LT33906_-40C_QA100PCT_PRI_QA_COLD_LT3390_BOS-EAGLE2_20220909_071004.std_1'])
    pass
