from PyICe.refid_modules import bench_identifier
from PyICe import lab_core, lab_utils, virtual_instruments
try:
    from PyICe.data_utils import stdf_utils
except ImportError as e:
    print('STDF processing library unavailable. Expected on Linux VDI.')
import collections
import functools
import itertools
import importlib
import hashlib
import sqlite3
import time
import abc
import os
import re

class byte_ord_dict(collections.OrderedDict):
    '''Ordered dictionary for channel results reporting with pretty print addition.'''
    def __str__(self):
        s = ''
        max_channel_name_length = 0
        for k,v in self.items():
            max_channel_name_length = max(max_channel_name_length, len(k))
            # s += f'{k}:\t{v[0]:02X}\n'
            s += f'{k}:\t{v:02X}\n'
        s = s.expandtabs(max_channel_name_length+2).replace(' ','.')
        return s

class SQLiteDBError(Exception):
    '''parent exception for problems reading from logged sqlite data.'''
class MissingColumnsError(SQLiteDBError):
    '''die traceablilty columns weren't logged'''
class EmptyTableError(SQLiteDBError):
    '''sqlite table has no rows from which to extract die traceability'''
class InvalidDataError(SQLiteDBError):
    '''sqlite table has no rows from which to extract die traceability'''

class die_traceability(abc.ABC):
    '''Shared infrastructure to compute identification values from I2C, SQLite, or STDF'''

    @classmethod
    def read_registers_i2c(cls, register_list, channels, powerup_fn=None, powerdown_fn=None):
        '''read relevant data directly from DUT. Assumes "channels" PyICe master is properly configured and DUT is powered and able to talk I2C.
        powerup_fn and powerdown_fn should take zero arguments. They can be uses as an alternative method to get Stowe talking I2C in other apps/configs.'''
        if powerup_fn is None:
            try:
                cls.powerup_fn(channels)
            except:
                print('Please define a powerup_fn in your project specific die_traceability script to read the registers.')
                breakpoint()
        else:
            powerup_fn(channels)
        results = byte_ord_dict()
        for ch in register_list:
            if ch in cls.zero_intercept_registers:          ### This isn't good. Why are we assuming there is an attribute called zero_intercept_registers?
                v = 0
            else:
                v = channels.read(ch)
            # results[ch] = (bytes((v,)))
            results[ch] = v
        if powerdown_fn is None:
            try:
                cls.powerdown_fn(channels)
            except:
                print('Please define a powerdown_fn in your project specific die_traceability script to put the dut to rest.')
                breakpoint()
        else:
            powerdown_fn(channels)
        return results

    @classmethod
    def read_registers_sqlite(cls, register_list, db_file, db_table):
        '''pull relevant register data from first row of sqlite database file/table'''
        conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES) #automatically convert datetime column to Python datetime object
        conn.row_factory = sqlite3.Row #index row data tuple by column name
        legacy_register_list = [f"0 as {r}" if r in cls.zero_intercept_registers else r for r in register_list]
        column_query_str = ', '.join(legacy_register_list)
        try:
            row = conn.execute(f"SELECT {column_query_str} FROM {db_table}").fetchone()
        except sqlite3.OperationalError as e:
            if len(e.args) and e.args[0] == 'no such column: f_variant':
                legacy_register_list = [f"0 as {r}" if r in cls.zero_intercept_registers or r in ('f_variant',) else r for r in register_list]
                column_query_str = ', '.join(legacy_register_list)
                row = conn.execute(f"SELECT {column_query_str} FROM {db_table}").fetchone()
            elif len(e.args) and e.args[0].startswith('no such column: ') and input('Logger DB table is missing die traceability register(s). Proceed anyway? ').lower.startswith('y'):
                return byte_ord_dict()
            else:
                raise e
        # assert row is not None #Empty table!
        if row is None:
            raise EmptyTableError()
        results = byte_ord_dict()
        for k in row.keys():
            # results[k] = (bytes((row[k],)))
            results[k] = row[k]
            if results[k] is None:
                raise InvalidDataError()
        return results
    @classmethod
    def read_from_dict(cls, register_list, data_dict):
        '''filter and reorder dict data. data_dict must contain superset of required data.'''
        results = byte_ord_dict()
        for k in register_list:
            if k in cls.zero_intercept_registers:
                results[k] = 0
            else:
                results[k] = data_dict[k]
        return results
    @classmethod
    def read_registers_stdf(cls, test_map, device_number, stdf_reader):
        '''read device information from PyICe.data_utils.stdf_utils.stdf_utils record'''
        assert isinstance(stdf_reader, stdf_utils.stdf_reader)
        return {tname: stdf_reader.get_value(devnum=device_number, testnum=tnum) for tname,tnum in test_map.items()}
    @classmethod
    def compute_hash_stdf(cls, device_number, stdf_reader):
        '''read die traceability hash from PyICe.data_utils.stdf_utils.stdf_utils record
            a cls.traceability_test_map dictionary is required.'''
        # This method is only compatible with REVID7+ DUTS which have undergone wafer sort.
        # Blind built units and units wich predate the correction of the signed x,y loc register mis-allocation won't work correctly.
        # Legacy unit calculation is possible, but much more complicated, and removed here for the sake of simplicity. Legacy calculation is intact in stowe_eval.stowe_eval_base.modules.stdf_utils.

        record = cls.read_registers_stdf(cls.traceability_test_map, device_number, stdf_reader)
        record = {k: int(v) for k,v in record.items()}
        record['f_die_running_7_0_'] = record['f_die_running_7_0_'] & 0xFF
        record['f_die_running_9_8_'] = (record['f_die_running_9_8_'] >> 8) & 0x03
        dut_data = cls.read_from_dict(cls.traceability_registers, record)
        return f'0x{cls.compute_hash(dut_data).hex().upper()}'
    @classmethod
    def compute_hash(cls, register_data):
        h = hashlib.blake2b(digest_size=4)
        assert isinstance(register_data, byte_ord_dict)
        for ch in register_data:
            # Cast possibly signed data into single unsigned byte
            # x and y die coordinates are now signed bytes.
            try:
                # 0-255 first try
                byte_data = register_data[ch].to_bytes(length=1, byteorder='big', signed=False)
            except OverflowError as e:
                # Something went wrong. Subset of possible outcomes: 
                    # int too big to convert
                    # can't convert negative int to unsigned
                # Without checking too carefully, let's just see if it fits into a signed byte instead. No loss of information here.
                byte_data = register_data[ch].to_bytes(length=1, byteorder='big', signed=True)
                # If this one doesn't take, let it crash. Not sure what else to do. Incoming data isn't supposed to be bigger than a byte by the time it gets here.
            h.update(byte_data)
        return h.digest()
    @classmethod
    def compute_unconfigured_hash(cls, revid):
        unconfigured_data = cls.read_from_dict(register_list=cls.nvm_registers, data_dict = {k:0 for k in cls.nvm_registers})
        unconfigured_data['revid'] = revid
        return cls.compute_hash(register_data=unconfigured_data)
    @classmethod
    def compute_untraceable_hash(cls, revid):
        unconfigured_data = cls.read_from_dict(register_list=cls.traceability_registers, data_dict = {k:0 for k in cls.traceability_registers})
        unconfigured_data['revid'] = revid
        return cls.compute_hash(register_data=unconfigured_data)
    @classmethod
    def compare_nvm_hash(cls, data1, data2):
        '''this is dumb. Why not compare the registers directly? No need to hash!'''
        data1_ord_filt = cls.read_from_dict(register_list=cls.nvm_registers, data_dict=data1)
        data2_ord_filt = cls.read_from_dict(register_list=cls.nvm_registers, data_dict=data2)
        unconfigured_data1 = cls.compute_unconfigured_hash(revid=data1['revid'])
        unconfigured_data2 = cls.compute_unconfigured_hash(revid=data2['revid'])
        data1_hash = cls.compute_hash(data1_ord_filt)
        data2_hash = cls.compute_hash(data2_ord_filt)
        assert data1_hash != unconfigured_data1
        assert data2_hash != unconfigured_data2
        return data1_hash == data2_hash
    @classmethod
    def compare_traceability_hash(cls, data1, data2):
        '''this is dumb. Why not compare the registers directly? No need to hash!'''
        data1_ord_filt = cls.read_from_dict(register_list=cls.traceability_registers, data_dict=data1)
        data2_ord_filt = cls.read_from_dict(register_list=cls.traceability_registers, data_dict=data2)
        unconfigured_data1 = cls.compute_untraceable_hash(revid=data1['revid'])
        unconfigured_data2 = cls.compute_untraceable_hash(revid=data2['revid'])
        data1_hash = cls.compute_hash(data1_ord_filt)
        data2_hash = cls.compute_hash(data2_ord_filt)
        assert data1_hash != unconfigured_data1
        assert data2_hash != unconfigured_data2
        return data1_hash == data2_hash
    @classmethod
    def compare_nvm(cls, data1, data2):
        data1_ord_filt = cls.read_from_dict(register_list=cls.nvm_registers, data_dict=data1)
        data2_ord_filt = cls.read_from_dict(register_list=cls.nvm_registers, data_dict=data2)
        unconfigured_data1 = cls.read_from_dict(register_list=cls.nvm_registers, data_dict = {k:0 for k in cls.nvm_registers})
        unconfigured_data2 = cls.read_from_dict(register_list=cls.nvm_registers, data_dict = {k:0 for k in cls.nvm_registers})
        unconfigured_data1['revid'] = data1['revid']
        unconfigured_data2['revid'] = data2['revid']
        assert data1_ord_filt != unconfigured_data1
        assert data2_ord_filt != unconfigured_data2
        return data1_ord_filt == data2_ord_filt
    @classmethod
    def compare_traceability(cls, data1, data2):
        data1_ord_filt = cls.read_from_dict(register_list=cls.traceability_registers, data_dict=data1)
        data2_ord_filt = cls.read_from_dict(register_list=cls.traceability_registers, data_dict=data2)
        unconfigured_data1 = cls.read_from_dict(register_list=cls.traceability_registers, data_dict = {k:0 for k in cls.traceability_registers})
        unconfigured_data2 = cls.read_from_dict(register_list=cls.traceability_registers, data_dict = {k:0 for k in cls.traceability_registers})
        unconfigured_data1['revid'] = data1['revid']
        unconfigured_data2['revid'] = data2['revid']
        return data1_ord_filt == data2_ord_filt and data1_ord_filt != unconfigured_data1 and data2_ord_filt != unconfigured_data2
    @classmethod
    def compare_dut_database(cls, channels, db_file, db_table, die_only=True, powerup_fn=None, powerdown_fn=None):
        '''just _die_ registers, not trim registers'''
        if die_only:
            register_list = cls.traceability_registers
        else:
            register_list = cls.nvm_registers
        i2c_data = cls.read_registers_i2c(register_list=register_list, channels=channels, powerup_fn=powerup_fn, powerdown_fn=powerdown_fn)
        db_data = cls.read_registers_sqlite(register_list=register_list, db_file=db_file, db_table=db_table)
        return i2c_data == db_data
    @classmethod
    def compare_dut_database(cls, db_file1, db_table1, db_file2, db_table2, die_only=True):
        '''just _die_ registers, not trim registers'''
        if die_only:
            register_list = cls.traceability_registers
        else:
            register_list = cls.nvm_registers
        db_data1 = cls.read_registers_sqlite(register_list=register_list, db_file=db_file1, db_table=db_table1)
        db_data2 = cls.read_registers_sqlite(register_list=register_list, db_file=db_file2, db_table=db_table2)
        return db_data1 == db_data2
    @classmethod
    def replace_die_traceability_channels(cls, channels, die_only=False, powerup_fn=None, powerdown_fn=None):
        if die_only:
            register_list = cls.traceability_registers
        else:
            #register_list = cls.nvm_registers
            register_list = cls.nvm_derived_registers
        register_data = cls.read_registers_i2c(register_list = register_list,
                                               channels      = channels,
                                               powerup_fn=powerup_fn,
                                               powerdown_fn=powerdown_fn,
                                              )
        # c_g_dummy = lab_core.channel_group('die_traceability dummy channels')
        c_g_dummy = virtual_instruments.dummy_quantum_twin('die_traceability dummy channels')
        c_g_orig = lab_core.channel_group('die_traceability original channels')
        for (bf_name, bf_value) in register_data.items():
            print(f'NOTICE: Replacing {bf_name} register channel with dummy channel.')
            try:
                c_g_orig._add_channel(channels[bf_name])
                channels.remove_channel_by_name(bf_name)
                # ch = lab_core.channel(name=bf_name, read_function=None, write_function=None)
                c_g_dummy.add_channel(live_channel=c_g_orig[bf_name], skip_read=True, cached_value=bf_value)
            except lab_core.ChannelAccessException as e:
                if bf_name in cls.zero_intercept_registers:
                    # Deleted in future Yoda
                    pass
                else:
                    raise e
        channels.add(c_g_dummy)
        return {'dummy_replacements': c_g_dummy,
                'originals'         : c_g_orig,
               }
    @classmethod
    def compute_variant(cls, data):
        # REVID omitted. Might a Si-spin be related to variant programming?
        
        data_ord_filt = cls.read_from_dict(register_list=cls.variant_regs, data_dict=data)
        # Debug to see why nothing matches
        # foo = {k: LT3390.LT3390[k.upper()]==v for k,v in data_ord_filt.items()}
        # bar = list(itertools.filterfalse(lambda kv: kv[1], foo.items())) 
        # It's broken enums: (Pdb) !bar [('f_x_ldo_mode_ch3', False), ('f_x_ldo_mode_ch4', False), ('f_mon_ov_en_ch3', False)]
        # is_LT3390 = functools.reduce(lambda a,b: a and b, foo.values())
        # print(is_LT3390)
        matches = {}
        for variant in cls.variants:
            reg_matches = {k: variant[k.upper()]==v for k,v in data_ord_filt.items()} # Why did the model change bf names to all uppecase?
            is_variant = functools.reduce(lambda a,b: a and b, reg_matches.values())
            why_not = list(itertools.filterfalse(lambda kv: kv[1], reg_matches.items())) # Debug. Not matching anything because of f_x_ldo_mode_chx bogus enums now.
            matches[variant['NAME']] = {
                                        'is_variant': is_variant,
                                        'reg_matches': reg_matches,
                                        'why_not': why_not,
                                       }
        if not len([m for (m,findings) in matches.items() if findings['is_variant']]):
            for variant in cls.variants:
                print(f'{variant["NAME"]}: (model vs DUT)')
                for (mismatch, is_mismatched) in matches[variant['NAME']]['why_not']:
                    print(f'\t{mismatch}: {variant[mismatch.upper()]} vs. {data_ord_filt[mismatch]}')
        return matches
        # Todo: what if these aren't always unique?
        # Todo: what if not all variant registers are present in the record?
        # Todo: try this against stdf data record instead, matching just on f_die_ registers?
    @classmethod
    def get_ATE_config(cls, data, given_trace_hash=None):
        if given_trace_hash is None:
            traceability_data = cls.read_from_dict(register_list=cls.traceability_registers,
                                                                   data_dict=data, # Should be superset of required data
                                                                  )
            traceability_hash = cls.compute_hash(register_data=traceability_data)
            traceability_hash_table = f'0x{traceability_hash.hex().upper()}' #String version
        else:
            traceability_hash_table = given_trace_hash
        query_str = f'''SELECT START_T, STDF_file, SETUP_ID as config_file, ROM_COD as config_change, ENG_ID as config_date, SPEC_NAM as variant_datasheet, PART_TYP as variant_shell FROM population_data WHERE TRACEABILITY_HASH == '{traceability_hash_table}' AND CAST(TST_TEMP AS NUMERIC) == 25'''
        try:
            db = lab_utils.sqlite_data(database_file=cls.correlation_db_filename)
            row = db.query(query_str).fetchone()
            if row is None:
                print(f'WARNING: ATE data not found for DUT {traceability_hash_table}.')
                return None
            elif None in row:
                # Legacy data before ATE program stored values into previously unused fields.
                print(f'WARNING: (Legacy) ATE found for DUT {traceability_hash_table}, but missing configuration traceability fields.')
                return None
            return {k: row[k] for k in row.keys()}
        except sqlite3.OperationalError as e:
            # OperationalError('no such table: 0xC6A857A5')
            table_pat = re.compile(r'^no such table: (?P<table_name>\w+)$', re.MULTILINE)
            # OperationalError('no such column: SETUP_ID3')
            column_pat = re.compile(r'^no such column: (?P<col_name>\w+)$', re.MULTILINE)
            if table_pat.match(str(e)):
                # This shouldn't happen when looking in population_data table instead of individual DUT table.
                print(f'WARNING: ATE data not found for DUT {traceability_hash_table}.')
            elif column_pat.match(str(e)):
                print(f'ERROR: Missing columns from ATE data for DUT {traceability_hash_table}. This should never happen. Please send details to PyICe Support at PyICe-developers@analog.com for investigation.')
                raise # Don't need to crash here, but would really like to know if this system isn't working as designed.
            else:
                # What happened???
                print(f'ERROR: Unknown problem with ATE config traceability data for DUT {traceability_hash_table}. This should never happen. Please send details to PyICe Support at PyICe-developers@analog.com for investigation.')
                print(type(e), e)
                raise
            return None
    @classmethod
    def get_ATE_variant(cls, data):
        try:
            cfg_file = cls.get_ATE_config(data)['config_file']
        except TypeError as e:
            # missing ATE data
            return None
        ate_config = os.path.basename(cfg_file).rstrip(' $')
        #todo what about non-unique # versioning if moved/renamed. Change number?
        return ate_config

if __name__ == '__main__':
    import sys
    from stowe_eval.stowe_eval_base.modules import test_module #not used, but fixes import cycle
    from stowe_eval.stowe_eval_base.modules import test_results
    register_list = stowe_die_traceability.nvm_registers
    # register_list = stowe_die_traceability.traceability_registers
    if len(sys.argv) == 1:
        #no arguments; read from live DUT
        with bench_identifier.get_bench_instruments(project_folder_name = 'dummy_project', benchsetup = None)() as bench:      #This is increadibly frustrating. If I import a bench from dummy_project, the gui won't have FUSE DATA or FUSE CNTRL, but will if I import from stowe_eval.
            channels = bench.get_master()
            channels.gui()
            # breakpoint()
            register_data = stowe_die_traceability.read_registers_i2c(register_list=register_list,
                                                                      channels=channels,
                                                                     )
            # channels.write("enable_pin", "AVIN")
            # channels.write("vmaina_force", 3.3)
            # time.sleep(0.1)
            # print(f'msm_state={channels.read("msm_state")}')
            # channels.write("enable_pin", "LOW")
            # channels.write("vmaina_force", 0)
    elif len(sys.argv) == 2:
        # filename argument
        (script_name, db_filename) = sys.argv[:]
        path, file_name = os.path.split(db_filename)
        file_base, file_ext = os.path.splitext(file_name)
        if file_ext == ".sqlite":
            db = lab_utils.sqlite_data(database_file=db_filename)
            table_names = db.get_table_names()
            print(table_names)
            sys.exit(0)
        elif file_ext == ".json":
            if file_base == "test_results":
                trr = test_results.test_results_reload(db_filename)
                # print(trr)
                register_data = byte_ord_dict({k:trr.get_traceability_info()[k] for k in stowe_die_traceability.traceability_registers})
            elif file_base == "correlation_results":
                crr = test_results.correlation_results_reload(db_filename)
                # print(crr)
                register_data = byte_ord_dict({k:crr.get_traceability_info()[k] for k in stowe_die_traceability.traceability_registers})
            else:
                raise Exception(f'Unknown file type: {db_filename}')
        else:
            raise Exception(f'Unknown file type: {db_filename}')
    elif len(sys.argv) == 3:
        # filename and database table name argument
        (script_name, db_filename, table_name) = sys.argv[:]
        register_data = stowe_die_traceability.read_registers_sqlite(register_list=register_list,
                                                                     db_file=db_filename,
                                                                     db_table=table_name,
                                                                    )
    else:
        raise Exception('USAGE:' + \
                        '\n\tWith no arguments, script will power up default bench and read I2C registers.' + \
                        '\n\tWith one argument, script will open the SQLite database file named in argument, print table names, and exit.' + \
                        '\n\tWith two arguments, script will open the SQLite database file named in first argument and read from table named in second argument.' + \
                        f'\n\t{[arg for arg in sys.argv]}'
                       )
    # Compute hash over subset of registers specific to die traceability.
    # This uniquely (hopefully) identifies a part, even if other NVM registers are changed by test mode
    # This will fail if die level traceabiility registers aren't configured properly by ATE.
    # Early test programs (limited to 1st Si) didn't do this configuration.
    unconfigured_hash = stowe_die_traceability.compute_untraceable_hash(revid=register_data['revid'])
    traceability_data = stowe_die_traceability.read_from_dict(register_list=stowe_die_traceability.traceability_registers,
                                                               data_dict=register_data, # Should be superset of required data
                                                              )
    # Print hash of traceability registers only. Do it early to reduce prominence (and chance of being mistaken for the all-NVM hash

    traceability_hash = stowe_die_traceability.compute_hash(register_data=traceability_data)
    print(f"Traceability (only) hash: 0x{traceability_hash.hex().upper()}")
    # Print summary of NVM configuration
    print()
    print(register_data)
    nvm_hash = stowe_die_traceability.compute_hash(register_data=register_data)
    # Warn if die traceability registers appear empty (last for prominence - this is important!):
    if traceability_hash == unconfigured_hash:
        print("WARNING! This DUT's die-level traceability registers were improperly programmed (empty).")
    try:
        # if register_data['f_die_crc_7_5_'] == 0 and     \
        #    register_data['f_die_crc_4_'] == 0 and       \
        #    register_data['f_die_crc_3_'] == 0 and       \
        #    register_data['f_die_crc_2_'] == 0 and       \
        #    register_data['f_die_crc_1_'] == 0 and       \
        #    register_data['f_die_crc_0_'] == 0:
        if register_data['f_die_crc'] == 0:
            print("WARNING! This DUT's die traceability CRC registers were improperly programmed (empty).")
        # print(f"NVM (complete) hash: 0x{nvm_hash.hex().upper()}")
        matches = stowe_die_traceability.compute_variant(register_data).items()
        matches_filt = [m for (m,findings) in matches if findings['is_variant']]
        if len(matches_filt) == 1:
            print(f'NVM inspection matched variant: {matches_filt[0]}')
        else:
            for name,variant in matches:
                print(f'{name}:\t{variant["is_variant"]}'.expandtabs(10)) # TODO prettier? Necessary?
    except KeyError as e:
        print("WARNING! This DUT's die traceability CRC missing.") # Not in JSONs??
    print(stowe_die_traceability.get_ATE_config(traceability_data))

    print(stowe_die_traceability.get_ATE_variant(register_data))