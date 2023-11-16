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
    def __init__(self, filenames, part_ids):
        """

        Args:
            filenames: List of directory addresses for the files of interest.
            part_ids: List of values in the 'PART_ID' of the PRR of the dut in question. Should be in the same order as
                filenames. For example, the first value in part_ids should be the part id of the dut in the first
                directory address in filenames.
        """
        pairs = list(zip(filenames, part_ids))
        self._test_name_dict = {}
        for f, i in pairs:
            with open(f, 'rb') as file:
                p = Parser(inp=file, reopen_fn=None)
                reader = FileReader()
                p.addSink(reader)
                p.parse()
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
                        self.to_be_added = {}
                    if record_type is pystdf.V4.Ptr:  # Parametric Test Record - This is a test within this part.
                        if master_info["TEST_TXT"] != '':
                            test_num_dict[master_info['TEST_NUM']] = {
                                'testname': master_info["TEST_TXT"],
                                'lo_limit': master_info["LO_LIMIT"],
                                'hi_limit': master_info["HI_LIMIT"],
                                'units': master_info['UNITS'],
                            }
                            self.to_be_added[master_info["TEST_TXT"] + test_temp] = {
                                'result': master_info['RESULT'],
                                'lo_limit': master_info["LO_LIMIT"],
                                'hi_limit': master_info["HI_LIMIT"],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }
                        else:
                            self.to_be_added[test_num_dict[master_info['TEST_NUM']]['testname'] + test_temp] = {
                                'result': master_info['RESULT'],
                                'lo_limit':  test_num_dict[master_info['TEST_NUM']]['lo_limit'],
                                'hi_limit':  test_num_dict[master_info['TEST_NUM']]['hi_limit'],
                                'units': test_num_dict[master_info['TEST_NUM']]['units'],
                            }
                    if record_type is pystdf.V4.Prr and master_info['PART_ID'] is i:
                            for testname, data in self.to_be_added.items():
                                self._test_name_dict[testname] = data
                            break

    def __getitem__(self, item):
        return self._test_name_dict[item]


if __name__ == '__main__':
    stuff = STDFParser(filenames=['example_stdf/lot2.stdf'], part_ids=['2'])
    #stuff = STDFParser(filenames=[
       # '../../../../../projects/stowe_eval/correlation/REVID7/2023-04-14/ENG_LT3390-6J_25C_ENG_ENG_FT_TRIM_LT3390_ETS1UOJU4-00334_20230414_162608.std_1',
        #'../../../../../projects/stowe_eval/correlation/REVID7/2022-09-09/5627908_LT33906_-40C_QA100PCT_PRI_QA_COLD_LT3390_BOS-EAGLE2_20220909_071004.std_1'],
        #part_ids=['1', '2'])
    pass
