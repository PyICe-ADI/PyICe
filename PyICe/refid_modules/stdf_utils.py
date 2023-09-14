
import collections
import functools
import math
import os
import re
import sqlite3
import sys

try:
    from pystdf.IO import Parser
    import pystdf.V4
    from pystdf.Writers import format_by_type
except ModuleNotFoundError as e:
    # pystdf is needed for processing files, but not needed for audits, IVY and other Linux PyICe usage.
    print(f'WARNING: Import error with pystdf library. This is ok if not processing STDF dlogs directly, and temporarily expected in Linux because of Anaconda package issues.\n{type(e)}: {e.args}')
import time
from stowe_eval.stowe_eval_base.modules.stowe_die_traceability import stowe_die_traceability
from PyICe.data_utils import units_parser


class results_ord_dict(collections.OrderedDict):
    '''Ordered dictionary with pretty print addition.'''
    def __str__(self):
        s = ''
        max_name_length = 0
        for k,v in self.items():
            max_name_length = max(max_name_length, len(str(k)))
            s += f'{k}:\t{v}\n'
        s = s.expandtabs(max_name_length+2)
        return s


#hash table name
    # dlog file
    # PART_ID
    # 9900065:   RevID
    # 899900000: f_die_year (Since 2000)
    # 899900001: f_die_week (eng=month)
    # 899900002: f_die_wafer_number (eng=day)
    # 899900003: f_die_loc_x (eng=hour)
    # 899900004: f_die_loc_y (eng=minute)
    # 899900005: f_die_running (eng=serial #)
    # 
    # 'revid',
    # 'f_die_fab_2_0_',
    # 'f_die_fab_4_3_',
    # 'f_die_parent_child_9_8_',
    # 'f_die_loc_y',
    # 'f_die_loc_x',
    # 'f_die_running_7_0_',
    # 'f_die_parent_child_7_0_',
    # 'f_die_fab_6_5_',
    # 'f_die_wafer_number',
    # 'f_die_running_9_8_',
    # 'f_die_week',
    # 'f_die_year',
    
class testNumberException(Exception):
    '''class of exceptions for unable to parse test number input successfully.'''

class test_number:
    def __init__(self, test_number):
        if isinstance(test_number, int):
            (f_subtest, f_test) = math.modf(test_number/1e5)
            self._test = int(round(f_test))
            self._subtest = int(round(f_subtest*1e5))
        elif isinstance(test_number, str):
            assert len(test_number) == 10, 'String format is "tttttsssss".'
            self._test = int(test_number[0:5])
            self._subtest = int(test_number[5:10])
        elif isinstance(test_number, float):
            (f_subtest, f_test) = math.modf(test_number)
            self._test = int(round(f_test))
            self._subtest = int(round(f_subtest*1e5))
        elif isinstance(test_number, (tuple, list)):
            assert len(test_number) == 2, 'Tuple format is (test, subtest)'
            self._test = int(test_number[0])
            self._subtest = int(test_number[1])
        else:
            raise testNumberException('Unknown ATE test number format type: {type(test_number)}.')
    def __str__(self):
        ret_str = ''
        ret_str += f'Test: {self._test} Subtest: {self._subtest}\n'
        ret_str += f'INT: {self.to_int()}\n'
        ret_str += f'STR: {self.to_string()}\n'
        ret_str += f'DEC: {self.to_decimal()}\n'
        ret_str += f'TUP: {self.to_pair()}\n'
        return ret_str
    def to_int(self):
        return int(self._test*1e5 + self._subtest)
    def to_string(self):
        return f'{self.to_int():010d}'
    def to_decimal(self):
        return self._test + self._subtest/1e5
    def to_pair(self):
        return (self._test, self._subtest)


# print(test_number(12300045))
# print(test_number(123.00045))
# print(test_number('0012300045'))
# print(test_number((123,45)))


def x_loc_getter(dut_record):
    try:
        return dut_record['f_die_loc_x (eng=hour)'] #8999.3
    except KeyError as e:
        try:
            return dut_record['f_die_loc_x'] #8010.4
        except KeyError as f:
            print(e)
            print(f)
            raise

def y_loc_getter(dut_record):
    try:
        return dut_record['f_die_loc_y (eng=minute)'] #8999.4
    except KeyError as e:
        try:
            return dut_record['f_die_loc_y'] #8010.5
        except KeyError as f:
            print(e)
            print(f)
            raise

def die_running_getter(dut_record):
    try:
        return dut_record['f_die_running (eng=serial #)'] #8999.5
    except KeyError as e:
        try:
            return dut_record['f_die_running'] #8010.3
        except KeyError as f:
            print(e)
            print(f)
            raise

def die_wafer_getter(dut_record):
    try:
        return dut_record['f_die_wafer_number (eng=day)'] #8999.2
    except KeyError as e:
        try:
            return dut_record['f_die_wafer_number'] #8010.2
        except KeyError as f:
            print(e)
            print(f)
            raise

def die_week_getter(dut_record):
    try:
        return dut_record['f_die_week (eng=month)'] #8999.1
    except KeyError as e:
        try:
            return dut_record['f_die_week'] #8010.1
        except KeyError as f:
            print(e)
            print(f)
            raise
            
            
class ETS_units_scaler:
    '''
    From: Keefer, Mark <Mark.Keefer@analog.com> 
    Sent: Thursday, April 29, 2021 1:29 PM
    To: Simmons, David <David.Simmons@analog.com>; Arnold, Jerimy <Jerimy.Arnold@analog.com>
    Subject: FW: ETS stdf writer, results and limit scaling
    
    HI Dave,
    
    See below the list of recognized and scaled base units. It’s small.
    
    Another oddity is that if a test has no limits, it will not apply scaling regardless of the base unit.
    
    The good news is that no data is misrepresented if your stdf parser reads the UNITS field and recognizes metric prefixes, right?
    
    Mark
    
    From: Randy Williams <randy.williams@teradyne.com> 
    Sent: Wednesday, April 28, 2021 8:04 PM
    To: Keefer, Mark <Mark.Keefer@analog.com>; Cristian Jimenez <cristian.jimenez@teradyne.com>
    Cc: Arnold, Jerimy <Jerimy.Arnold@analog.com>; Carboaro, Elijah <elijah.carbonaro@teradyne.com>; Andrew Westall <andrew.westall@teradyne.com>
    Subject: RE: ETS stdf writer, results and limit scaling
    
    Mark,
    
    Currently Ohms are not normalized to the base units. The only units that are currently normalized are volts amps seconds hertz and percentages.
    
    Regards,
    Randy Williams
    Field Apps. Engineer
    
    7124 LANTANA TERRACE
    CARLSBAD, CA 92011
    randy.williams@teradyne.com
        
    '''
    '''
    %
    %/V
    %/mA
    %/uA
    A
    A/V
    A/uA
    A/us
    AMPS
    BITS
    Bits
    C
    DUT/Hr
    FAIL
    HERTZ
    Hr
    KOhms
    MHZ
    Mhos
    NUM
    OHM
    Ohms
    SECONDS
    Sec
    V
    V/V
    VOLTS
    Wafer
    Week
    Year
    kOHM
    mA
    mOhm
    mS
    mV
    mV/V
    nS
    ns
    nsec
    pF
    uA
    uMHO
    usec
    
    
    ENG adds:
    Day
    Dnum
    MHz
    Month
    '''
    ets_normalized = {'%', #Skip units parser
                      'A',
                      'AMPS',
                      'BITS',
                      'Bits',
                      'C',
                      'DUT/Hr',
                      'FAIL',
                      'HERTZ',
                      'MHZ',
                      'NUM',
                      'SECONDS',
                      'Sec',
                      'V',
                      'VOLTS',
                      'Wafer',
                      'Week',
                      'Year',
                      'mA',
                      'mS',
                      'mV',
                      'nS',
                      'ns',
                      'nsec',
                      'uA',
                      'usec',
                      'P/F',
                      'T/F',
                      'Day',
                      'Dnum',
                      'MHz',
                      'Month',
                      'Ohm'
                     }
    un_normalized =  {'%/V', #Parse units
                      '%/mA',
                      '%/uA',
                      'A/V',
                      'A/uA',
                      'A/us',
                      'Hr',
                      'KOhms',
                      'kOhm',
                      'Mhos',
                      'OHM',
                      'Ohms',
                      'V/V',
                      'kOHM',
                      'mOhm',
                      'mV/V',
                      'pF',
                      'uMHO',
                      'LSB',
                      '',
                     }
    unconfirmed =    (
                     )
    def __init__(self):
        self.unrecognized_units = set()
        cls = type(self)
        assert len(cls.ets_normalized.intersection(cls.un_normalized)) == 0
    def print_unkown_units(self):
        if len(self.unrecognized_units):
            raise Exception(f"ERROR: Unrecognized units: '{sorted(list(self.unrecognized_units))}' in dlog. I don't know if these need to be renormalized.")
    def normalize(self, units):
        '''fix the units that ETS didn't normalized before logging.
        leave the ones that were already scaled by the ETS shell alone.
        The only way to know is via the support email info above.
        '''
        if units in type(self).ets_normalized:
            return self.fake_parser(units)
        elif units in type(self).un_normalized:
            return units_parser.parser(units)
        else:
            self.unrecognized_units.add(units)
            return self.fake_parser(units)
    def fake_parser(self, units):
        return {'MULT': 1, 'UNITS': f"[{units}]/[]"}
class master_parser:
    traceability_regs = {'revid': lambda self: self._dut_record['RevID'],
                         # 'f_die_fab_2_0_': lambda self: self._dut_record['f_die_fab'] & 0x7,
                         'f_die_fab_2_0_': lambda self: 0, #removed from memory map, but hash order preserved.
                         # 'f_die_fab_4_3_': lambda self: (self._dut_record['f_die_fab'] >> 3) & 0x3,
                         'f_die_fab_4_3_': lambda self: 0,
                         # 'f_die_parent_child_9_8_': lambda self: (self._dut_record['f_die_parent_child'] >> 8) & 0x3,
                         'f_die_parent_child_9_8_': lambda self: 0,
                         # 'f_die_loc_y': lambda self: self._dut_record['f_die_loc_y (eng=minute)'],
                         'f_die_loc_y': lambda self: y_loc_getter(self._dut_record),
                         # 'f_die_loc_x': lambda self: self._dut_record['f_die_loc_x (eng=hour)'],
                         'f_die_loc_x': lambda self: x_loc_getter(self._dut_record),
                         # 'f_die_running_7_0_': lambda self: self._dut_record['f_die_running (eng=serial #)'] & 0xFF,
                         'f_die_running_7_0_': lambda self: die_running_getter(self._dut_record) & 0xFF,
                         # 'f_die_parent_child_7_0_': lambda self: self._dut_record['f_die_parent_child'] & 0xFF,
                         'f_die_parent_child_7_0_': lambda self: 0,
                         # 'f_die_fab_6_5_': lambda self: (self._dut_record['f_die_fab'] >> 5) & 0x3,
                         'f_die_fab_6_5_': lambda self: 0,
                         # 'f_die_wafer_number': lambda self: self._dut_record['f_die_wafer_number (eng=day)'],
                         'f_die_wafer_number': lambda self: die_wafer_getter(self._dut_record),
                         # 'f_die_running_9_8_': lambda self: (self._dut_record['f_die_running (eng=serial #)'] >> 8) & 0x3,
                         'f_die_running_9_8_': lambda self: (die_running_getter(self._dut_record) >> 8) & 0x3,
                         'f_die_week': lambda self: die_week_getter(self._dut_record),
                         'f_die_year': lambda self: self._dut_record['f_die_year (Since 2000)'],
                        }
    _db = None #Shared db conn.
    def __init__(self):
        pass
    def _debug_units_scaling(self, test_result_record):
        # TODO debug units scaling. STDF storage of values in base units vs metric prefix units inconsistent. Need to audit dlog for offenders....
        stdf_scale = 10**(-1*test_result_record["RES_SCAL"])
        steve_scale = self._units[test_result_record["TEST_NUM"]]["MULT"]
        # if self._units[test_result_record["TEST_NUM"]]["MULT"] != 1:
        # if stdf_scale != steve_scale:
        if test_result_record["TEST_NUM"] == 1000000 or test_result_record["TEST_NUM"] == 2000000:
            print(f'{test_result_record["TEST_TXT"]} {test_result_record["TEST_NUM"]} {test_result_record["RESULT"]} {test_result_record["UNITS"]} {self._units[test_result_record["TEST_NUM"]]} {test_result_record["RES_SCAL"]}')
    def map_data(self, record_type, data):
        return {k: v for (k,v) in zip(record_type.fieldNames, data)}
    def _compute_traceability_registers(self):
        for reg, f in type(self).traceability_regs.items():
            try:
                assert reg not in self._dut_record, f'Traceablity reg {reg} stepping on ATE dlist test name.' #could still be a problem with case sensitivity
            except AssertionError as e:
                if reg not in ['f_die_loc_y', 'f_die_loc_x', 'f_die_wafer_number', 'f_die_week']: #allow overwrite of a few that are unchanged
                    raise e
            try:
                self._dut_record[reg] = f(self)
            except KeyError as e:
                raise # No more workarounds for missing data post revid 2.
                if reg == 'revid':
                    print(f'{reg} not dlogged. Assumed 1 (2nd Si).') #Ugh!
                    self._dut_record[reg] = 1
                else:
                    print(f'{reg} not dlogged. Assumed zero.')
                    self._dut_record[reg] = 0
        try:
            del self._dut_record['RevID'] #duplicate case insensitive column name
        except KeyError:
            pass # Not logged in early ATE programs
        traceability_data = stowe_die_traceability.read_from_dict(register_list=stowe_die_traceability.traceability_registers,
                                                               data_dict=self._dut_record,
                                                              )
        # if traceability_data['f_die_running_9_8_'] == 0 and traceability_data['f_die_running_7_0_'] == 142:
            # # 0xAC87AAA4
            # print(traceability_data)
            # breakpoint()
        # if traceability_data['f_die_running_9_8_'] == 0 and traceability_data['f_die_running_7_0_'] == 0x30:
            # # 0xBE305BAD
            # print(traceability_data)
            # breakpoint()
        traceability_hash = stowe_die_traceability.compute_hash(register_data=traceability_data)
        # self._dut_record['traceability_hash'] = f'0x{traceability_hash.hex().upper()}'
        # print(f"Traceability (only) hash: 0x{traceability_hash.hex().upper()}")
        return f'0x{traceability_hash.hex().upper()}'
    def after_begin(self, dataSrc):
        self.dataSrc = dataSrc
        self.inp_file = self.dataSrc.inp.name
        print(f'Processing {self.inp_file}')
        self._dut_count = 0
        self._die_traceability_tests = results_ord_dict()
        
        self.ets_units_scaler = ETS_units_scaler()
        
        self._units = results_ord_dict() # Fix inconsitent ETS units scaling with Python parser
        # if type(self)._db is None:
            # type(self)._db = sqlite3.connect('stdf_data.sqlite') #share conn aross concurrent parsers. Bad idea?!?!
            # type(self)._cur = type(self)._db.cursor()
        # self._db = type(self)._db
        # self._cur = type(self)._cur
        self._db = sqlite3.connect('stdf_data.sqlite')
        self._cur = self._db.cursor()
    def after_send(self, dataSrc, data):
        if data is None:
            breakpoint()
        record_type = type(data[0])
        record_data = data[1]
        if record_type is pystdf.V4.Far:
            # File Attributes Record (FAR)
            # Function: Contains the information necessary to determine how to decode the STDF data
            # contained in the file.
            #     CPU_TYPE U*1 CPU type that wrote this file
            #     STDF_VER U*1 STDF version number
            # (<pystdf.V4.Far object at 0x0000025F2D270548>, [2, 4])
            pass
        elif record_type is pystdf.V4.Mir:
            # Master Information Record (MIR)
            # Function: The MIR and the MRR (Master Results Record) contain all the global information that
            # is to be stored for a tested lot of parts. Each data stream must have exactly one MIR,
            # immediately after the FAR (and the ATRs, if they are used). This will allow any data
            # reporting or analysis programs access to this information in the shortest possible
            # amount of time.
                # SETUP_T U*4 Date and time of job setup
                # START_T U*4 Date and time first part tested
                # STAT_NUM U*1 Tester station number
                # MODE_COD C*1 Test mode code (e.g. prod, dev) space
                # RTST_COD C*1 Lot retest code space
                # PROT_COD C*1 Data protection code space
                # BURN_TIM U*2 Burn-in time (in minutes) 65,535
                # CMOD_COD C*1 Command mode code space
                # LOT_ID C*n Lot ID (customer specified)
                # PART_TYP C*n Part Type (or product ID)
                # NODE_NAM C*n Name of node that generated data
                # TSTR_TYP C*n Tester type
                # JOB_NAM C*n Job name (test program name)
                # JOB_REV C*n Job (test program) revision number length byte = 0
                # SBLOT_ID C*n Sublot ID length byte = 0
                # OPER_NAM C*n Operator name or ID (at setup time) length byte = 0
                # EXEC_TYP C*n Tester executive software type length byte = 0
                # EXEC_VER C*n Tester exec software version number length byte = 0
                # TEST_COD C*n Test phase or step code length byte = 0
                # TST_TEMP C*n Test temperature length byte = 0
                # USER_TXT C*n Generic user text length byte = 0
                # AUX_FILE C*n Name of auxiliary data file length byte = 0
                # PKG_TYP C*n Package type length byte = 0
                # FAMLY_ID C*n Product family ID length byte = 0
                # DATE_COD C*n Date code length byte = 0
                # FACIL_ID C*n Test facility ID length byte = 0
                # FLOOR_ID C*n Test floor ID length byte = 0
                # PROC_ID C*n Fabrication process ID length byte = 0
                # OPER_FRQ C*n Operation frequency or step length byte = 0
                # SPEC_NAM C*n Test specification name length byte = 0
                # SPEC_VER C*n Test specification version number length byte = 0
                # FLOW_ID C*n Test flow ID length byte = 0
                # SETUP_ID C*n Test setup ID length byte = 0
                # DSGN_REV C*n Device design revision length byte = 0
                # ENG_ID C*n Engineering lot ID length byte = 0
                # ROM_COD C*n ROM code ID length byte = 0
                # SERL_NUM C*n Tester serial number length byte = 0
                # SUPR_NAM C*n Supervisor name or ID length byte = 0
            # (<pystdf.V4.Mir object at 0x0000025F2D270708>, [1600092154, 1600092154, 1, 'D', 'E', ' ', 65535, ' ', 'ENG', '1', 'ETS-364-', 'ETS364B', 'LT3390', '0.00', ' ', 'Engineer', 'ETS Test Executive', '2018A [2018.1.2.4]', 'ENG', '25', 'UNUSED', 'C:\\ETS\\APPS\\LT3390\\LT3390.pds', 'Package', 'Power', '08/23/2018', '', 'Boston', '', '', 'LT3390', '0.00', 'ENG1', None, None, None, None, None, None])
            self._master_info = self.map_data(*data)
            while True:
                corrected_temp = input(f"{self.inp_file} {self._master_info['FLOW_ID']} reports {self._master_info['TST_TEMP']}C. Corrected temperature? [{self._master_info['TST_TEMP']}] ")
                if not len(corrected_temp):
                    break #accept STDF unchanged
                try:
                    float(corrected_temp) # make sure response is a number, but database stores as string according to STDF spec.
                    self._master_info['TST_TEMP'] = corrected_temp
                    break
                except ValueError:
                    pass
        elif record_type is pystdf.V4.Sdr:
            # Site Description Record (SDR)
            # Function: Contains the configuration information for one or more test sites, connected to one test
            # head, that compose a site group.
                # HEAD_NUM U*1 Test head number
                # SITE_GRP U*1 Site group number
                # SITE_CNT U*1 Number (k) of test sites in site group
                # SITE_NUM kxU*1 Array of test site numbers
                # HAND_TYP C*n Handler or prober type length byte = 0
                # HAND_ID C*n Handler or prober ID length byte = 0
                # CARD_TYP C*n Probe card type length byte = 0
                # CARD_ID C*n Probe card ID length byte = 0
                # LOAD_TYP C*n Load board type length byte = 0
                # LOAD_ID C*n Load board ID length byte = 0
                # DIB_TYP C*n DIB board type length byte = 0
                # DIB_ID C*n DIB board ID length byte = 0
                # CABL_TYP C*n Interface cable type length byte = 0
                # CABL_ID C*n Interface cable ID length byte = 0
                # CONT_TYP C*n Handler contactor type length byte = 0
                # CONT_ID C*n Handler contactor ID length byte = 0
                # LASR_TYP C*n Laser type length byte = 0
                # LASR_ID C*n Laser ID length byte = 0
                # EXTR_TYP C*n Extra equipment type field length byte = 0
                # EXTR_ID C*n Extra equipment ID length byte = 0
            # (<pystdf.V4.Sdr object at 0x0000025F2D2792C8>, [1, 255, 4, [1, 2, 3, 4], None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None])
            pass
        elif record_type is pystdf.V4.Pir:
            # Part Information Record (PIR)
            # Function: Acts as a marker to indicate where testing of a particular part begins for each part
            # tested by the test program. The PIR and the Part Results Record (PRR) bracket all the
            # stored information pertaining to one tested part.
                # HEAD_NUM U*1 Test head number
                # SITE_NUM U*1 Test site number
            # (<pystdf.V4.Pir object at 0x0000025F2D2796C8>, [1, 2])
            self._test_results = results_ord_dict()
            self._dut_record = results_ord_dict()
            self._dut_record['STDF_file'] = os.path.basename(self.inp_file)
            self._dut_record.update(self._master_info)
        elif record_type is pystdf.V4.Ptr:
            # Parametric Test Record (PTR)
            # Function: Contains the results of a single execution of a parametric test in the test program. The
            # first occurrence of this record also establishes the default values for all semi-static
            # information about the test, such as limits, units, and scaling. The PTR is related to the
            # Test Synopsis Record (TSR) by test number, head number, and site number.
                # TEST_NUM U*4 Test number
                # HEAD_NUM U*1 Test head number
                # SITE_NUM U*1 Test site number
                # TEST_FLG B*1 Test flags (fail, alarm, etc.)
                # PARM_FLG B*1 Parametric test flags (drift, etc.)
                # RESULT R*4 Test result TEST_FLG bit 1 = 1
                # TEST_TXT C*n Test description text or label length byte = 0
                # ALARM_ID C*n Name of alarm length byte = 0
                # OPT_FLAG B*1 Optional data flag See note
                # RES_SCAL I*1 Test results scaling exponent OPT_FLAG bit 0 = 1
                # LLM_SCAL I*1 Low limit scaling exponent OPT_FLAG bit 4 or 6 = 1
                # HLM_SCAL I*1 High limit scaling exponent OPT_FLAG bit 5 or 7 = 1
                # LO_LIMIT R*4 Low test limit value OPT_FLAG bit 4 or 6 = 1
                # HI_LIMIT R*4 High test limit value OPT_FLAG bit 5 or 7 = 1
                # UNITS C*n Test units length byte = 0
                # C_RESFMT C*n ANSI C result format string length byte = 0
                # C_LLMFMT C*n ANSI C low limit format string length byte = 0
                # C_HLMFMT C*n ANSI C high limit format string length byte = 0
                # LO_SPEC R*4 Low specification limit value OPT_FLAG bit 2 = 1
                # HI_SPEC R*4 High specification limit value OPT_FLAG bit 3 = 1
        
            # (<pystdf.V4.Ptr object at 0x0000025F2D2799C8>, [2999900097, 1, 2, 129, 192, 0.0, 'Timeline', 'ALARM', 206, 0, 0, 0, -inf, inf, 'Sec', '%9.0f', '%9.0f', '%9.0f', None, None])
            # (<pystdf.V4.Ptr object at 0x0000025F2D2799C8>, [2999900098, 1, 2, 0, 192, 0.0, 'UPH', '    ', 206, 0, 0, 0, -inf, inf, 'DUT/Hr', '%9.1f', '%9.1f', '%9.1f', None, None])
            test_result_record = self.map_data(*data)
            
            
            # RESULT The RESULT value is considered useful only if all the following bits from TEST_FLG and PARM_FLG are 0:
                # TEST_FLG
                    # bit 0 = 0 no alarm
                    # bit 1 = 0 value in result field is valid
                    # bit 2 = 0 test result is reliable
                    # bit 3 = 0 no timeout
                    # bit 4 = 0 test was executed
                    # bit 5 = 0 no abort
                # PARM_FLG
                    # bit 0 = 0 no scale error
                    # bit 1 = 0 no drift error
                    # bit 2 = 0 no oscillation
            # If any one of these bits is 1, then the PTR result should not be used.
            if ((test_result_record['TEST_FLG'] & 0b111111) | (test_result_record['PARM_FLG'] & 0b111)):
                print(f'Invalid test data flags for test {test_result_record["TEST_NUM"]}')
                test_result_record['RESULT'] = None
            # breakpoint()
            ##########################
            # STOWE SPECIFIC!!!!!!!! #
            ##########################
            if test_result_record['TEST_NUM'] >= 901000000 and test_result_record['TEST_NUM'] <= 901099999:
                #skip all test 9010s. Fuse resistances are only in FTT, not QA runs. They make the correlation database have too many columns for Sqlite.
                return
            ##########################
            ##########################
            # if test_result_record['TEST_NUM'] == 102000022:
            # if test_result_record['TEST_NUM'] == 10000001 or \
            # test_result_record['TEST_NUM'] == 14000000 or \
            # test_result_record['TEST_NUM'] == 51000011:
            # if test_result_record['RES_SCAL'] != 0:
            #     print(test_result_record)
                # breakpoint()
            if test_result_record['TEST_TXT'] != '':
                #first record
                if re.search('f_die', test_result_record['TEST_TXT']):
                    self._die_traceability_tests[test_result_record['TEST_NUM']] = test_result_record['TEST_TXT']
                elif re.match('RevID', test_result_record['TEST_TXT']):
                    self._die_traceability_tests[test_result_record['TEST_NUM']] = test_result_record['TEST_TXT']
            if test_result_record['TEST_NUM'] in self._die_traceability_tests.keys():
                # Keyed by test name. Consider switch to test number???
                try:
                    self._dut_record[self._die_traceability_tests[test_result_record['TEST_NUM']]] = int(test_result_record['RESULT']) #traceability regs all ints! Why not dlog'd as such??
                except TypeError as e:
                    self._dut_record[self._die_traceability_tests[test_result_record['TEST_NUM']]] = None #invalid data
            if test_result_record['UNITS'] is None:
                # Not first record
                pass
            # elif test_result_record['UNITS'] == '':
                # breakpoint()
            # elif test_result_record['UNITS'] == 'P/F' or \
                 # test_result_record['UNITS'] == 'T/F':
                # # Parser can't deal with apparent quotient. Manual bypass hack.
                # self._units[test_result_record['TEST_NUM']] = {'UNITS': test_result_record['UNITS'],
                                                               # 'MULT' : 1.0,
                                                               # 'UNITS_ORIG': test_result_record['UNITS']
                                                              # }
            else:
                # self._units[test_result_record['TEST_NUM']] = units_parser.parser(test_result_record['UNITS']) #Units info only in first record of each file.
                self._units[test_result_record['TEST_NUM']] = self.ets_units_scaler.normalize(test_result_record['UNITS']) #Units info only in first record of each file.
                self._units[test_result_record['TEST_NUM']]['UNITS_ORIG'] = test_result_record['UNITS']
                # if True:
                    # self._debug_units_scaling(test_result_record)
            # Fix units scaling with Python Parser.
            try:
                test_result_record['UNITS'] = self._units[test_result_record['TEST_NUM']]['UNITS'] # Nobody really cares though...
                test_result_record['RESULT'] = self._units[test_result_record['TEST_NUM']]['MULT'] * test_result_record['RESULT']
            except TypeError as e:
                #Probably missing/invalid flagged data
                test_result_record['UNITS'] = None #eh... is this ok???
                test_result_record['RESULT'] = None
            except KeyError as e:
                # Tests 99.67, 99.68, 99.69 have no test name, and therefore never stored any units. Jerimy said it's ok. It's for MPW sorting.
                print(e)
                breakpoint()
            self._test_results[f"{test_result_record['TEST_NUM']:010d}"] = test_result_record['RESULT']
        elif record_type is pystdf.V4.Prr:
            # Part Results Record (PRR)
            # Function: Contains the result information relating to each part tested by the test program. The
            # PRR and the Part Information Record (PIR) bracket all the stored information
            # pertaining to one tested part.
                # HEAD_NUM U*1 Test head number
                # SITE_NUM U*1 Test site number
                # PART_FLG B*1 Part information flag
                # NUM_TEST U*2 Number of tests executed
                # HARD_BIN U*2 Hardware bin number
                # SOFT_BIN U*2 Software bin number 65535
                # X_COORD I*2 (Wafer) X coordinate -32768
                # Y_COORD I*2 (Wafer) Y coordinate -32768
                # TEST_T U*4 Elapsed test time in milliseconds 0
                # PART_ID C*n Part identification length byte = 0
                # PART_TXT C*n Part description text length byte = 0
                # PART_FIX B*n Part repair information length byte = 0
            #(<pystdf.V4.Prr object at 0x0000019E67CD9B08>, [1, 2, 0, 1915, 1, 1, -32768, -32768, 1802, '1', None, None])
            self._dut_record.update(self.map_data(*data))
            if self._dut_record['HARD_BIN'] in (65535,) or self._dut_record['SOFT_BIN'] in (65535,):
                print(f'Omitting DUT {self._dut_record["FLOW_ID"]} Head {self._dut_record["HEAD_NUM"]} Site {self._dut_record["SITE_NUM"]} Num {self._dut_record["NUM_TEST"]}. HARD_BIN={self._dut_record["HARD_BIN"]} SOFT_BIN={self._dut_record["SOFT_BIN"]}.')
            elif self._dut_record['HARD_BIN'] not in [1,2]: #Bin 2 seems to be REVID3 passes for MPW (pizza) sorting purpose.
                try:
                    hash_str = self._compute_traceability_registers()
                except KeyError as e:
                    print(f'Omitting DUT with missing traceability data. HARD_BIN={self._dut_record["HARD_BIN"]}')
                else:
                    if input(f'Allow this part anyway {self._dut_record} [y/n]? ').lower() in ['y', 'yes']:
                        self._dut_record.update(self._test_results)
                        self._log(hash_str)
                    else:
                        print(f'Omitting DUT {self._dut_record["FLOW_ID"]} Head {self._dut_record["HEAD_NUM"]} Site {self._dut_record["SITE_NUM"]} Num {self._dut_record["NUM_TEST"]}. HARD_BIN={self._dut_record["HARD_BIN"]}.')
            elif self._dut_record['SOFT_BIN'] not in [1,2]:
                # print(f'Omitting DUT {hash_str}. SOFT_BIN={self._dut_record["SOFT_BIN"]}')
                try:
                    hash_str = self._compute_traceability_registers()
                except KeyError as e:
                    print(f'Omitting DUT with missing traceability data. SOFT_BIN={self._dut_record["SOFT_BIN"]}')
                else:
                    if input(f'Allow this part anyway {self._dut_record} [y/n]? ').lower() in ['y', 'yes']:
                        self._dut_record.update(self._test_results)
                        self._log(hash_str)
                    else:
                        print(f'Omitting DUT {self._dut_record["FLOW_ID"]} Head {self._dut_record["HEAD_NUM"]} Site {self._dut_record["SITE_NUM"]} Num {self._dut_record["NUM_TEST"]}. SOFT_BIN={self._dut_record["SOFT_BIN"]}.')
            else:
                hash_str = self._compute_traceability_registers()
                self._dut_record.update(self._test_results)
                self._log(hash_str)
            # print(self._dut_record)
            self._dut_record = None
            self._test_results = None
        elif record_type is pystdf.V4.Tsr:
            # Test Synopsis Record (TSR)
            # Function: Contains the test execution and failure counts for one parametric or functional test in
            # the test program. Also contains static information, such as test name. The TSR is
            # related to the Functional Test Record (FTR), the Parametric Test Record (PTR), and the
            # Multiple Parametric Test Record (MPR) by test number, head number, and site
            # number.
                # HEAD_NUM U*1 Test head number See note
                # SITE_NUM U*1 Test site number
                # TEST_TYP C*1 Test type space
                # TEST_NUM U*4 Test number
                # EXEC_CNT U*4 Number of test executions 4,294,967,295
                # FAIL_CNT U*4 Number of test failures 4,294,967,295
                # ALRM_CNT U*4 Number of alarmed tests 4,294,967,295
                # TEST_NAM C*n Test name length byte = 0
                # SEQ_NAME C*n Sequencer (program segment/flow) name length byte = 0
                # TEST_LBL C*n Test label or text length byte = 0
                # OPT_FLAG B*1 Optional data flag See note
                # TEST_TIM R*4 Average test execution time in seconds OPT_FLAG bit 2 = 1
                # TEST_MIN R*4 Lowest test result value OPT_FLAG bit 0 = 1
                # TEST_MAX R*4 Highest test result value OPT_FLAG bit 1 = 1
                # TST_SUMS R*4 Sumof test result values OPT_FLAG bit 4 = 1
                # TST_SQRS R*4 Sum of squares of test result values OPT_FLAG bit 5 = 1
            # (<pystdf.V4.Tsr object at 0x00000299760A9948>, [255, 255, 'P', 9900063, 73, 0, 4294967295, 'Fuse Readings - Reg 191', '', '', 203, 1.6989434957504272, 0.0, 0.0, 0.0, 0.0])
            # (<pystdf.V4.Tsr object at 0x00000299760A9948>, [255, 255, 'P', 9900064, 73, 0, 4294967295, 'Lockout Set', '', '', 203, 1.6989434957504272, 0.0, 0.0, 0.0, 0.0])
            # (<pystdf.V4.Tsr object at 0x00000299760A9948>, [255, 255, 'P', 10000000, 73, 0, 4294967295, 'Vref Regs - Pre Trim', '', '', 203, 1.6989434957504272, 1.1398190259933472, 1.1470963954925537, 83.49664306640625, 95.50273132324219])
            pass
        elif record_type is pystdf.V4.Hbr:
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 16, 0, 'F', 'Continuity'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 17, 0, 'F', 'AbsMax'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 18, 0, 'F', 'Parametric'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 19, 0, 'F', 'Leakage'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 20, 0, 'F', 'Oxide Stress'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 21, 0, 'F', 'Buck'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 22, 0, 'F', 'Boost'])
            # (<pystdf.V4.Hbr object at 0x0000023563653908>, [255, 255, 23, 0, 'F', 'LDO'])
            pass
        elif record_type is pystdf.V4.Sbr:
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 16, 0, 'F', 'Continuity'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 17, 0, 'F', 'AbsMax'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 18, 0, 'F', 'Parametric'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 19, 0, 'F', 'Leakage'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 20, 0, 'F', 'Oxide Stress'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 21, 0, 'F', 'Buck'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 22, 0, 'F', 'Boost'])
            # (<pystdf.V4.Sbr object at 0x0000023563653A88>, [255, 255, 23, 0, 'F', 'LDO'])
            pass
        elif record_type is pystdf.V4.Pcr:
            # (<pystdf.V4.Pcr object at 0x0000023563653788>, [1, 1, 0, 0, 4294967295, 0, 4294967295])
            # (<pystdf.V4.Pcr object at 0x0000023563653788>, [1, 2, 73, 0, 4294967295, 64, 4294967295])
            # (<pystdf.V4.Pcr object at 0x0000023563653788>, [1, 3, 0, 0, 4294967295, 0, 4294967295])
            # (<pystdf.V4.Pcr object at 0x0000023563653788>, [1, 4, 0, 0, 4294967295, 0, 4294967295])
            pass
        elif record_type is pystdf.V4.Mrr:
            # (<pystdf.V4.Mrr object at 0x0000023563653688>, [1600092457, None, None, None])
            pass
        elif record_type is pystdf.V4.Bps:
            # (<pystdf.V4.Bps object at 0x000002E0BCEFE5C8>, ['TouchDownID=0'])
            pass
        elif record_type is pystdf.V4.Eps:
            # (<pystdf.V4.Eps object at 0x000002E0BCEFE6C8>, [])
            pass
        elif record_type is pystdf.V4.Wcr:
            # Wafer Configuration Record (WCR)
            # Function: Contains the configuration information for the wafers tested by the job plan. The
            # WCR provides the dimensions and orientation information for all wafers and dice
            # in the lot. This record is used only when testing at wafer probe time.
            # Data Fields:
                # REC_LEN U*2 Bytes of data following header
                # REC_TYP U*1 Record type (2)
                # REC_SUB U*1 Record sub-type (30)
                # WAFR_SIZ R*4 Diameter of wafer in WF_UNITS 0
                # DIE_HT R*4 Height of die in WF_UNITS 0
                # DIE_WID R*4 Width of die in WF_UNITS 0
                # WF_UNITS U*1 Units for wafer and die dimensions 0
                # WF_FLAT C*1 Orientation of wafer flat space
                # CENTER_X I*2 X coordinate of center die on wafer -32768
                # CENTER_Y I*2 Y coordinate of center die on wafer -32768
                # POS_X C*1 Positive X direction of wafer space
                # POS_Y C*1 Positive Y direction of wafer space
            # Notes on Specific Fields:
                # WF_UNITS Has these valid values:
                    # 0 = Unknown units
                    # 1 = Units are in inches
                    # 2 = Units are in centimeters
                    # 3 = Units are in millimeters
                    # 4 = Units are in mils
                # WF_FLAT Has these valid values:
                    # U = Up
                    # D = Down
                    # L = Left
                    # R = Right
                    # space = Unknown
                # CENTER_X,
                # CENTER_Y
                    # Use the value -32768 to indicate that the field is invalid.
                # POS_X Has these valid values:
                    # L = Left
                    # R = Right
                    # space = Unknown
                # POS_Y Has these valid values:
                    # U = Up
                    # D = Down
                    # space = Unknown
            # Frequency: One per STDF file (used only if wafer testing).
            # Location: Anywhere in the data stream after the initial sequence (see page 14), and before the MRR.
            # Possbile Use: Wafer Map

            # (<pystdf.V4.Wcr object at 0x000001BC1AA90388>, [0.0, 0.0, 0.0, 0, ' ', -32768, -32768, ' ', ' '])
            # Doesn't appear to be filled out properly in our ETS probe setup. 
            pass
        elif record_type is pystdf.V4.Wir:
            # Wafer Information Record (WIR)
            # Function: Acts mainly as a marker to indicate where testing of a particular wafer begins for each
            # wafer tested by the job plan. The WIR and the Wafer Results Record (WRR) bracket all
            # the stored information pertaining to one tested wafer. This record is used only when
            # testing at wafer probe. A WIR/WRR pair will have the same HEAD_NUM and SITE_GRP
            # values.
            # Data Fields:
                # REC_LEN U*2 Bytes of data following header
                # REC_TYP U*1 Record type (2)
                # REC_SUB U*1 Record sub-type (10)
                # HEAD_NUM U*1 Test head number
                # SITE_GRP U*1 Site group number 255
                # START_T U*4 Date and time first part tested
                # WAFER_ID C*n Wafer ID length byte = 0
            # Notes on Specific Fields:
                # SITE_GRP Refers to the site group in the SDR. This is ameans of relating the wafer information to the configuration of the equipment used to test it. If this information is not known, or the tester does not support the concept of site groups, this field should be set to 255.
                # WAFER_ID Is optional, but is strongly recommended in order to make the resultant data files as useful as possible.
            # Frequency: One per wafer tested.
            # Location: Anywhere in the data stream after the initial sequence (see page 14) and before the MRR.
            # Sent before testing each wafer.
            
            # (<pystdf.V4.Wir object at 0x000001BC1AA90188>, [1, 255, 1620737799, 'W01'])
            # DJS: WAFER_ID might be useful to disambiguate coordinate data when multiple wafer lots are mixed into a single production lot.
            pass
        else:
            # DJS: Wrr looks useful, but haven't seen it in an ETS probe dlog yet.
            print('Unknown record type!')
            print(data)
            breakpoint()
    def after_complete(self, dataSrc):
        # print(self._die_traceability_tests) #Use to fine f_die registers!
        # print(self._units) # Check no crazy parser mistakes.
        
        self.ets_units_scaler.print_unkown_units()
        
        print(f'Processed {self._dut_count} DUTs.')
        self._db.commit()
        self._db.close()
        # print('end!')
    # def after_cancel(self, exc):
        # print('die!')
        # raise exc




class population_data(master_parser):
    '''log single table with traceability column'''
    # (Pdb) self._dut_record results_ord_dict([('STDF_file', '.\\LT3390H_ENG_QA_COLD_m50C_ENG_01142021_132648.std_1'), ('SETUP_T', 1610630929), ('START_T', 1610630929), ('STAT_NUM', 1), ('MODE_COD', 'D'), ('RTST_COD', 'E'), ('PROT_COD', ' '), ('BURN_TIM', 65535), ('CMOD_COD', ' '), ('LOT_ID', 'ENG'), ('PART_TYP', 'LT3390H'), ('NODE_NAM', 'BOS-EAGLE2'), ('TSTR_TYP', 'ETS364B'), ('JOB_NAM', 'LT3390'), ('JOB_REV', '0.00'), ('SBLOT_ID', ' '), ('OPER_NAM', 'Engineer'), ('EXEC_TYP', 'ETS Test Executive'), ('EXEC_VER', '2018A [2018.1.2.4]'), ('TEST_COD', 'ENG'), ('TST_TEMP', -50.0), ('USER_TXT', 'UNUSED'), ('AUX_FILE', 'C:\\ETS\\APPS\\LT3390\\LT3390.pds'), ('PKG_TYP', 'Package'), ('FAMLY_ID', 'Power'), ('DATE_COD', '08/23/2018'), ('FACIL_ID', ''), ('FLOOR_ID', 'Boston'), ('PROC_ID', ''), ('OPER_FRQ', ''), ('SPEC_NAM', 'LT3390'), ('SPEC_VER', '0.00'), ('FLOW_ID', 'QA COLD'), ('SETUP_ID', None), ('DSGN_REV', None), ('ENG_ID', None), ('ROM_COD', None), ('SERL_NUM', None), ('SUPR_NAM', None), ('f_die_year (Since 2000)', 21), ('f_die_week (eng=month)', 1), ('f_die_wafer_number (eng=day)', 14), ('f_die_loc_x (eng=hour)', 10), ('f_die_loc_y (eng=minute)', 48), ('f_die_running (eng=serial #)', 6), ('f_die_fab', 0), ('f_die_parent_child', 0), ('f_die_crc', 0), ('HEAD_NUM', 1), ('SITE_NUM', 2), ('PART_FLG', 0), ('NUM_TEST', 609), ('HARD_BIN', 1), ('SOFT_BIN', 1), ('X_COORD', -32768), ('Y_COORD', -32768), ('TEST_T', 1669), ('PART_ID', '1'), ('PART_TXT', None), ('PART_FIX', None), ('revid', 3), ('f_die_fab_2_0_', 0), ('f_die_fab_4_3_', 0), ('f_die_parent_child_9_8_', 0), ('f_die_loc_y', 48), ('f_die_loc_x', 10), ('f_die_running_7_0_', 6), ('f_die_parent_child_7_0_', 0), ('f_die_fab_6_5_', 0), ('f_die_wafer_number', 14), ('f_die_running_9_8_', 0), ('f_die_week', 1), ('f_die_year', 21), ('2999900097', 0.0), ('2999900098', 0.0), ('2999900099', 0.017000000923871994), ('2999900100', 0.08299999684095383), ('2999900101', 2.305555608472787e-05), ('0000100000', -0.5450356602668762), ('0000100001', -0.5449007153511047), ('0000100002', -0.5442603826522827), ('0000100003', -0.5431643128395081), ('0000100004', -0.5447741150856018), ('0000100005', -0.5448459386825562), ('0000100006', -0.5448157787322998), ('0000100007', -0.5452605485916138), ('0000100008', -0.928746223449707), ('0000100009', -0.6678857207298279), ('0000100010', -0.8823137283325195), ('0000100011', -0.679685115814209), ('0000100012
    def _log(self, traceability_hash):
        table_name = "population_data"
        self._dut_record['TRACEABILITY_HASH'] = traceability_hash
        missing_column_exc_str = f'^table {table_name} has no column named (?P<test_number>.+$)'
        unique_exc_str = f'^UNIQUE constraint failed: (?P<constraint_cols>.+$)'
        def _add_column(column_name):
            print(f'Column {column_name} is missing from table {table_name}. Attempting to add it. {self.inp_file}')
            self._cur.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}"')
            self._db.commit()
        col_str = ', '.join([f'"{k}"' for k in self._dut_record.keys()])
        try:
            ## RHM - In conference with DJS, we really don't know why PART_ID is in the primary key. It allows through retests of the same dut. 
            # self._cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_str}, PRIMARY KEY (TRACEABILITY_HASH, STDF_file, PART_ID))')
            self._cur.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_str}, PRIMARY KEY (TRACEABILITY_HASH, STDF_file))')
            self._db.commit()
        except sqlite3.OperationalError as e:
            print(e)
            print(len(self._dut_record.keys()))
            print('Too many columns???')
            raise e
        try:
            # self._cur.execute(f'INSERT OR IGNORE INTO "{table_name}" ({col_str}) VALUES ({", ".join(["?" for i in range(len(self._dut_record))])})', tuple(self._dut_record.values()))
            self._cur.execute(f'INSERT INTO "{table_name}" ({col_str}) VALUES ({", ".join(["?" for i in range(len(self._dut_record))])})', tuple(self._dut_record.values()))
            self._db.commit() #thread locking issue. Will slow down script!
            self._dut_count += 1
        except sqlite3.OperationalError as e:
            # if re.match(r'table 0xB0DEA1B1 has no column named 103000055', str(e)):
            # r'Bus: {netlist_name}\s+State = (?P<reading>0x[0-9a-f]+)'
            missing_col = re.match(missing_column_exc_str, str(e))
            if missing_col:
                _add_column(missing_col.group("test_number"))
                #Try again recursively
                self._log(traceability_hash)
                # Column 103000055 is missinng from table 0xB0DEA1B1. Attempting to add it.
            else:
                print(e)
                breakpoint()
                raise e
        except sqlite3.IntegrityError as e:
            # sqlite3.IntegrityError: UNIQUE constraint failed: population_data.TRACEABILITY_HASH, population_data.STDF_file
            # 2022-10-26 db is good test case
            unique_violation = re.match(unique_exc_str, str(e))
            if unique_violation:
                col_violations = unique_violation.group('constraint_cols').split(', ')
                stdf_file = self._dut_record['STDF_file']
                print("UNIQUE constraint failure. Either you are re-running this script on an existing database, or the STDF data contains duplicated re-test data for the same DUT.")
                print("If re-running, please try deleting existing database and trying again.")
                print(f"DUT:{traceability_hash} in {stdf_file}")
                if input(f'Replace previous DUT record with latest (re-test) record ({self._dut_record["PART_ID"]}) [y/n]? ') in ['y', 'yes']:
                    #Note, this would allow replacement of a bin1 with a bin!1 if data existed in the STDF file in that test ordering.
                    self._cur.execute(f'DELETE FROM {table_name} WHERE TRACEABILITY_HASH == "{traceability_hash}" AND STDF_file == "{stdf_file}"')
                    self._dut_count -= 1
                    self._log(traceability_hash)
                else:
                    raise e
            else:
                #unknown problem
                raise e
    
def copy_ATE_data(source_db=None, dest_db=None):
    if source_db is None:
        source_db = './stdf_data.sqlite'
    source_conn = sqlite3.connect(source_db)
    if dest_db is None:
        dest_db = os.path.join(os.path.dirname(__file__), '../../correlation/stdf_data.sqlite')
    # p4_dest_info = p4_traceability.get_fstat(dest_db)
    # if p4_dest_info['depotFile'] is not None and p4_info['action'] is None:
    #     # TODO: Ask to p4 check out
    #     print('Skipping copy. Destination database checked in')
    #     return False
    source_dest_table = 'population_data'
    conn = sqlite3.connect(dest_db)
    conn.row_factory = sqlite3.Row
    attach_schema = '__source_db__'
    conn.execute(f"ATTACH DATABASE '{source_db}' AS {attach_schema}")
    source_cols = set(conn.execute(f'SELECT * FROM {attach_schema}.{source_dest_table} LIMIT 1').fetchone().keys())
    dest_cols = set(conn.execute(f'SELECT * FROM {source_dest_table} LIMIT 1').fetchone().keys())
    extra_source_cols = source_cols - dest_cols
    if len(extra_source_cols):
        for col in extra_source_cols:
            print(col)
        if input(f'Modify destination table columns to accommodate extra source columns [y/n]? ') in ['y', 'yes']:
            for col in extra_source_cols:
                sql_alter = f'ALTER TABLE {source_dest_table} ADD COLUMN "{col}"'
                print(sql_alter)
                conn.execute(sql_alter)
        else:
            #Crash coming no matter what!!!
            raise Exception('Column mismatch uncorrected.')
    insert_str = f'''INSERT INTO {source_dest_table} ("{'","'.join(source_cols)}")\n SELECT\n"{'","'.join(source_cols)}"\nFROM\n{attach_schema}.{source_dest_table}'''
    # print(insert_str)
    try:
        conn.execute(insert_str)
        conn.commit()
    except sqlite3.IntegrityError as e:
        # assumed! Could copy regex from above to be certain.
        print("UNIQUE constraint failure. Most likely you are re-inserting existing data. Try pruning first.")
        raise e
    finally:
        conn.close()

def process_file(filename):
    with open(filename, 'rb') as f:
        p = Parser(inp=f, reopen_fn=None)
        p.addSink(population_data())
        p.parse()
        f.close()

def process_dir(top_dir):
    if os.path.splitext(top_dir)[1] in ['.std_1', '.stdf']:
        # Single file
        process_file(top_dir)
    else:
        # Directory tree
        for (dirpath, dirnames, filenames) in os.walk(top_dir, topdown=True, onerror=None, followlinks=False):
            for filename in filenames:
                filebase, file_extension = os.path.splitext(filename)
                if file_extension in ['.std_1', '.stdf']:
                    process_file(os.path.join(dirpath, filename))
                else:
                    print(f'rejected file extension: {filename}, {file_extension}')

def clean_dir(top_dir):
    if os.path.splitext(top_dir)[1] in ['.std_1', '.stdf']:
        # Single file
        dest_db = os.path.join(os.path.dirname(__file__), '../../correlation/stdf_data.sqlite')
        dest_table = 'population_data'
        conn = sqlite3.connect(dest_db)
        cur = conn.cursor()
        sql = f'DELETE FROM {dest_table} WHERE STDF_file == "{top_dir}" OR STDF_file == "{os.path.basename(top_dir)}"'
        print(sql)
        cur.execute(sql)
        print(f'{cur.rowcount} rows deleted from {top_dir}.')
        conn.commit()
        conn.close()
    else:
        # Directory tree
        for (dirpath, dirnames, filenames) in os.walk(top_dir, topdown=True, onerror=None, followlinks=False):
            for filename in filenames:
                filebase, file_extension = os.path.splitext(filename)
                if file_extension in ['.std_1', '.stdf']:
                    # process_file(os.path.relpath(os.path.abspath(os.path.join(dirpath, filename)), start=os.path.abspath(top_dir)), filepath=top_dir)
                    # process_file(os.path.abspath(os.path.join(dirpath, filename)))
                    clean_dir(os.path.join(dirpath, filename))
                else:
                    print(f'rejected file extension: {filename}, {file_extension}')

if __name__ == "__main__":
    # process_dir(r'../../correlation')
    if input(f'Prune STDF data from present working directory from correlation lookup database [y/n]? ').lower() in ['y', 'yes']:
        clean_dir(r'.')
    if input(f'Process STDF files from present working directory [y/n]? ').lower() in ['y', 'yes']:
        process_dir(r'.')
    if input(f'Merge database from present working directory with corrlation lookup database [y/n]? ') in ['y', 'yes']:
        copy_ATE_data()


'''
Helpful queries. TODO: Functionalize someday?
Duplicate search:
SELECT a.stdf_file, b.stdf_file, a.revid, traceability_hash, a.oper_frq, b.oper_frq
FROM population_data as a join population_data as b 
USING (traceability_hash)
WHERE 
a.flow_id == b.flow_id AND
a.stdf_file != b.stdf_file AND
a.rowid != b.rowid

Duplicate removal:
DELETE FROM population_data WHERE STDF_file == '.\5305699_LT33903_25C_QA100PCT_PRI_QA_ROOM_LT3390_BOS-EAGLE2_20210519_151447.std_1'
'''
