from pystdf.IO import Parser
import pystdf.V4, time, math
from .. import lab_utils
# ENUMS for fields by position within STDF record to make this code more readable.
# See: http://www.kanwoda.com/wp-content/uploads/2015/05/std-spec.pdf
# Return value is always in the form of the tuple: [RECORDTYPE, DATAOBJECT]
RECORDTYPE=0; DATAOBJECT=1
# Record?:
PARTNUM=9; SETUPTIME=0; STARTTIME=1; DEVICENAME=9; XLOC=6; YLOC=7
HEAD_NUM=0; SITE_NUM=1; SBIN_NUM=2; SBIN_CNT=3; SBIN_PF=4; SBIN_NAM=5                                                                           # SBR - Software Bin Record
HEAD_NUM=0; SITE_NUM=1; PART_FLG=2; NUM_TEST=3; HARD_BIN=4; SOFT_BIN=5; X_COORD=6; Y_COORD=7; TEST_T=8; PART_ID=9; PART_TXT=10; PART_FIX=11     # PRR - Part Results Record
# PRR Datatypes
# PART_FLG - All bits want to be 0 for a good part
PRR_PART_FLG_INCOMPLETE_BIT=2**2; PRR_PART_FLG_FAILED_BIT=2**3; PRR_PART_FLG_INVALID_BIT=2**4
# PTR Fields by position
PTR_TEST_NUM=0; PTR_HEAD_NUM=1; PTR_SITE_NUM=2; PTR_TEST_FLG=3; PTR_PARM_FLG=4; PTR_RESULT=5; PTR_TEST_TXT=6; PTR_ALARM_ID=7
# PTR Datatypes
# TEST_FLG - All bits want to be 0 for a good test
PTR_TEST_FLG_ALARM=2**0; PTR_TEST_FLG_RESULT_INVALID=2**1; PTR_TEST_FLG_RESULT_RELIABLE=2**2; PTR_TEST_FLG_TIMEOUT=2**3; PTR_TEST_FLG_NOT_EXECUTED=2**4; PTR_TEST_FLG_TEST_ABORTED=2**5; PTR_TEST_FLG_FLAG_INVALID=2**6; PTR_TEST_FLG_TEST_FAILED=2**7;

class FileReader:
    def __init__(self):
        self.data = []
    def after_send(self, dataSource, data):
        self.data.append(data)
    def write(self,line):
        self.data.append(line)
    def flush(self):
        pass

class stdf_reader():
    def __init__(self, filename, exit_if_malformed=True):
        '''
        Creates an object that can be interrogated for both stdf metadata like test setup time and device numbers as well as any individual test.
        It utilizes the pystdf module which does the really dirty business of parsing the raw .stdf file and all of its 1985 file structure economizations.
        Upon object creation, the file will be parsed by pystdf and then scanned again record by record to produce a far friendlier collection of interrogation methods.
        The main attribute self.parts is a dictionary of devices with part numbers as the key.
        The part number will be a string as that's what pystdf returned.
        A secondary attribute self.metadata is a dictionary of metadata objects like "SETUPTIME" and "STARTTIME".
        '''
        self.exit_if_malformed = exit_if_malformed
        self.scan_file(filename)
    def scan_file(self, filename):
        with open(filename, 'rb') as file:
            p = Parser(inp=file, reopen_fn=None)
            reader = FileReader()
            p.addSink(reader)
            p.parse()
            self.parts = {}
            self.metadata = {}
            state = None
            for line in reader.data:
                record_type = type(line[RECORDTYPE])
                if record_type is pystdf.V4.Sbr:
                    pass
                    # self.metadata["BINCOUNT"][line[DATAOBJECT][SBIN_NUM]] = line[DATAOBJECT][SBIN_CNT] # Anyone care about this record, seems redundant?
                if record_type is pystdf.V4.Mir:                        # Master information record
                    if state not in [None]:
                        lab_utils.print_banner(f'Corrupted STDF File: {filename}!', f'Got an MIR but not as the first Field. Last record type is "{state}".', length=160)
                        if self.exit_if_malformed:
                            raise Exception("\n\nSet exit_if_malformed to False if you want to push on.")
                    self.metadata["SETUPTIME"] = {"UNIX": line[DATAOBJECT][SETUPTIME], "HUMAN": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(line[DATAOBJECT][SETUPTIME]))}
                    self.metadata["STARTTIME"] = {"UNIX": line[DATAOBJECT][STARTTIME], "HUMAN": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(line[DATAOBJECT][STARTTIME]))}
                    state = "MIR"
                if record_type is pystdf.V4.Pir:                        # Product Information record - New Part Found!
                    if state not in ["MIR", "PRR"]:
                        lab_utils.print_banner(f'Corrupted STDF File: {filename}', f'Got a PIR but not after an MIR or after a PRR. Last record type is "{state}".', length=160)
                        if self.exit_if_malformed:
                            raise Exception("\n\nSet exit_if_malformed to False if you want to push on.")
                    this_part = {}                                      # Each unit gets a fresh dictionary.
                    this_part["HEADER"] = line[DATAOBJECT]              # Grab the header.
                    this_part["TESTS"] = []                             # Start a new list of tests.
                    state = "PIR"
                if record_type is pystdf.V4.Ptr:                        # Parametric Test Record - This is a test within this part.
                    if state not in ["PIR", "PTR"]:
                        lab_utils.print_banner(f'Corrupted STDF File: {filename}', f'Got a PTR but not at after a PIR or another PTR. Last record type is "{state}".', length=160)
                        if self.exit_if_malformed:
                            raise Exception("\n\nSet exit_if_malformed to False if you want to push on.")
                    this_part["TESTS"].append(line[DATAOBJECT])         # Grab the test data.
                    state = "PTR"
                if record_type is pystdf.V4.Prr:                        # Product Results record - End of this part.
                    if state not in ["PIR", "PTR"]:
                        lab_utils.print_banner(f'Corrupted STDF File: {filename}', f'Got a PRR but not at after a PIR or a PTR. Last record type is "{state}".', length=160)
                        if self.exit_if_malformed:
                            raise Exception("\n\nSet exit_if_malformed to False if you want to push on.")
                    this_part["XLOC"] = line[DATAOBJECT][XLOC]
                    this_part["YLOC"] = line[DATAOBJECT][YLOC]
                    this_part["SOFTBIN"] = line[DATAOBJECT][SOFT_BIN]
                    this_part["HARDBIN"] = line[DATAOBJECT][HARD_BIN]
                    flag = line[DATAOBJECT][PART_FLG]
                    this_part["PASSING"] = (flag & PRR_PART_FLG_FAILED_BIT != PRR_PART_FLG_FAILED_BIT) and (flag & PRR_PART_FLG_INVALID_BIT != PRR_PART_FLG_INVALID_BIT) and (flag & PRR_PART_FLG_INCOMPLETE_BIT != PRR_PART_FLG_INCOMPLETE_BIT)
                    self.parts[line[DATAOBJECT][PARTNUM]] = this_part   # Set the key to the device number and attach the data.
                    state = "PRR"
                if record_type is pystdf.V4.Mrr:                        # Master information record
                    if state not in ["PRR"]:
                        lab_utils.print_banner(f'Corrupted STDF File: {filename}', f'Got an MRR but not after a PRR. Last record type is "{state}".', length=160)
                        if self.exit_if_malformed:
                            raise Exception("\n\nSet exit_if_malformed to False if you want to push on.")
                    state = "MRR"
            file.close()
    def test_passed(self, device, testnum):
        for test in self.parts[str(device)]["TESTS"]:
            if test[PTR_TEST_NUM] == testnum:
                return test[PTR_TEST_FLG] == 0 # All bits must be 0 to pass
    def part_passed(self, device):
        '''
        Takes a part number <int> or <string>.
        Returns its PASS/FAIL status as a boolean.
        True is passing, False failing.
        '''
        return self.parts[str(device)]["PASSING"]
    def get_all_passing_parts(self):
        '''
        Returns a list of all parts with a Passing flag.
        '''
        passing_parts = []
        for part in self.parts:
            if self.parts[part]["PASSING"]:
                passing_parts.append(part)
        return passing_parts
    def get_all_in_bins_list(self, bins_list):
        '''
        Takes a bin number list.
        Returns a list of device numbers found with a bin number within the bins_list.
        '''
        parts_in_bins = []
        for part in self.parts:
            if self.parts[part]["SOFTBIN"] in bins_list:
                parts_in_bins.append(part)
        return parts_in_bins
    def get_bin_numbers(self, device_list):
        '''
        Takes a part number list <int>s or <string>s.
        Returns an list of dictionaries of the part numbers <string>s and their bin numbers <int>s with keys: {"PART", "BIN"}
        '''
        results = []
        for part in device_list:
            part = str(part) # All part numbers are strings
            results.append({"PART": part, "BIN": self.parts[part]["SOFTBIN"]})
        return results
    def get_bin_number(self, device):
        '''
        Takes a part number <int> or <string>.
        Returns its bin number <int>.
        '''
        return self.get_bin_numbers(device_list=[str(device)])[0]["BIN"]
    def get_all_part_indices(self):
        '''
        Takes no arguments.
        Returns a simple Python list of part numbers found in the STDF file.
        It is a list of strings because that is what pystdf returned.
        '''
        parts_list = []
        for part in self.parts:
            parts_list.append(part)
        return parts_list
    def get_all_of_testnum(self, testnum):
        '''
        The only argument is test number (testnum) which is an integer in the .stdf format which is a list of 10 digits like 104000041 which was stored as the U*4 or unsigned 4 byte format.
        In some testers the test and subtest numbers are represented as the T.S or test and subtest format.
        Usually the left 5 digits of the returned value represent the major test number (lefft padded with 0s) and the right 5 digits represent the subordinate test number (right justified).
        Your mileage may vary. See to_eagle_testnumber and from_eagle_testnumber at the bottom of this file.
        Returns a python dictionary with the device number (a string as returned by pystdf) and the value (usually float?) as the tester reading for that device.'''
        results = {}
        for part in self.parts:
            for test in self.parts[part]["TESTS"]:
                if test[PTR_TEST_NUM] == testnum:
                    results[part] = test[PTR_RESULT]
        return results
    def get_value(self, devnum, testnum):
        '''
        Takes arguments devnum and testnum.
        Returns a single scalar result.
        devnum accepts integers or strings.
        testnum is in the stdf 9 digit format.
        '''
        for test in self.parts[str(devnum)]["TESTS"]:
            if test[PTR_TEST_NUM] == testnum:
                return test[PTR_RESULT]
    def get_setup_time(self):
        '''
        Returns the tester's setup time as a dictionary keyed by "UNIX" and "STRING".
        The unix version is in the U*4 or 4 byte Unix format for easy time manipulation operations.
        The date and time field used in this specification is defined as a four byte (32 bit) unsigned integer field measuring the number of seconds since midnight on January 1st, 1970, in the local time zone.
        This is the UNIX standard base time, adjusted to the local time zone.
        The string version is converted to human readable as '%Y-%m-%d %H:%M:%S'.
        '''
        return self.metadata["SETUPTIME"]
    def get_starttime(self):
        '''
        Returns the test run's start time (start of first unit) as a dictionary keyed by "UNIX" and "STRING".
        The unix version is in the U*4 or 4 byte Unix format for easy time manipulation operations.
        The date and time field used in this specification is defined as a four byte (32 bit) unsigned integer field measuring the number of seconds since midnight on January 1st, 1970, in the local time zone.
        This is the UNIX standard base time, adjusted to the local time zone.
        The string version is converted to human readable as '%Y-%m-%d %H:%M:%S'.
        '''
        return self.metadata["STARTTIME"]
    def get_xlocation(self, devnum):
        '''
        Takes the argument devnum and returns the x location on the wafer as an integer.
        devnum accepts integers or strings.
        Returned value is an integer.
        '''
        return self.parts[str(devnum)]["XLOC"]
    def get_ylocation(self, devnum):
        '''
        Takes the argument devnum and returns the y location on the wafer as an integer.
        devnum accepts integers or strings.
        Returned value is an integer.
        '''
        return self.parts[str(devnum)]["YLOC"]

def to_eagle_testnumber(test_number):
    '''
    Returns a dictionary with keys {"TESTNUM", "SUBTESTNUM"} from a natively stored test number which is a U*4 or unsigned 4 byte value.
    The test number is the left 5 digits shifted down to the decimal point and the subtest number is the 5 rightmost digits.
    '''
    subtestnum, testnum = math.modf(test_number/1e5)
    return {"TESTNUM": round(testnum), "SUBTESTNUM": round(subtestnum*1e5)}
def from_eagle_testnumber(test_number, subtest_number):
    '''
    Returns an integer comprised of the arguments test_number time 100,000 plus the argument subtest_number to get back to the natively stored value of the U*4, 32 bit number, in the stdf file.
    '''
    return round(test_number * 1e5 + subtest_number)