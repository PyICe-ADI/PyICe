from PyICe import lab_core
import json
import objutils
import os

####
# Memory Dump reader, such as:
#   Motorola format: https://en.wikipedia.org/wiki/SREC_(file_format)
#   Tek format: https://en.wikipedia.org/wiki/Tektronix_hex_format
#   Intel format: https://en.wikipedia.org/wiki/Intel_HEX
####

class memory_decoder():
    def __init__(self, twii=None):
        self.twii = twii
    def _parse_mdump(self, mem_str, fmt, offset=0):
        #TODO. Dtype hardcoded to unit8, for lack of an alternate stakeholder right now.
        # https://pypi.org/project/objutils/
        mem = objutils.loads(fmt, mem_str)
        mem_dict = {}
        for section in mem.sections:
            mem_array = section.read_numeric_array(addr=section.address, length=section.length, dtype='uint8_be')
            for idx, data in enumerate(mem_array):
                mem_dict[idx+section.address+offset] = data
        return mem_dict
    def parse_srec(self, srec_str, offset=0):
        return self._parse_mdump(srec_str, fmt='srec', offset=offset)
    def parse_ihex(self, ihex_str, offset=0):
        return self._parse_mdump(ihex_str, fmt='ihex', offset=offset)
    def parse_hexdump(self, rfc4194_str, offset=0):
        return self._parse_mdump(rfc4194_str, fmt='shf', offset=offset)

    # def parse_ascii_hex(ascii_hex_str, offset=0):
        #not quite hexdump format, ex:
        # 0x1F 0x00 0x01 0x08 0x00 0x00 0x09 0x03 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        # 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00
        # mem_data = {}
        # for idx, reg in enumerate(ascii_hex_str.split()):
            # addr = offset + idx
            # dbyte = int(reg, 16)
            # mem_data[addr] = dbyte
        # print(f'READ data between addresses 0x{min(mem_data.keys()):X} and 0x{max(mem_data.keys()):X} ({max(mem_data.keys())-min(mem_data.keys())+1})')
        # return mem_data
    def _parse_bitfields(self):
        #depends on twii memory dect having been previously populated!
        bf_data = {}
        for bf in self.twii:
            try:
                bf_data[bf.get_name()] = bf.read()
            except lab_core.ChannelAccessException as e:
                # Not all bit fields are readable
                pass
        return bf_data
    def prettify(self, bf_name, bf_value): #, twii=None
        if self.twii is None:
            try:
                pkey = f'0x{bf_name:X}'
            except ValueError as e:
                pkey = bf_name
            try:
                pvalue = f'0x{bf_value:02X}'
            except ValueError as e:
                pvalue = bf_value
        else:
            pkey = bf_name # Name
            bf = self.twii[bf_name]
            fvalue = bf.format(data=bf_value, format=None, use_presets=True)
            if fvalue == bf_value:
                size = bf.get_size()
                nsize = (size-1) // 4 + 1
                nsizefstr = f'{bf_value:0{nsize}X}'
                pvalue = f"{size}'h{nsizefstr}"
            else:
                pvalue = fvalue
        return (pkey, pvalue)
    def prettyprint(self, dict): # twii=None
        for k in sorted(dict):
            (pkey, pvalue) = self.prettify(bf_name=k, bf_value=dict[k]) #, twii=twii
            print(f'{pkey}: {pvalue}')
    def decode(self, memdump_file):
        file_ext = os.path.splitext(memdump_file)[1]
        with open(memdump_file, 'r') as f:
            if file_ext == '.srec' or file_ext == '.s19':
                reg_data = self.parse_srec(f.read(), offset=0)
            elif file_ext == '.ihex':
                reg_data = self.parse_ihex(f.read(), offset=0)
            else:
                raise Exception(f'Unknown file type {file_ext}. Contact PyICe-developers@analog.com for more information.')
            f.close()
        self.twii.get_interface().set_data_source(reg_data)
        bf_data = self._parse_bitfields()
        self.prettyprint(bf_data)
        return bf_data
    def read(self, ascii_dump_file):
        #Warning, this modifies the twii, making it incompatible with binary decode()
        for bf in self.twii:
            bf.set_delegator(bf)
            bf._write = None
            bf._read = None
            bf.set_write_access(True)
        file_ext = os.path.splitext(ascii_dump_file)[1]
        with open(ascii_dump_file, 'r') as f:
            if file_ext == ".txt":
                # "KEY: VALUE\n" record, like PyICe GUI dump
                for line in f:
                    k,v = line.strip().split(":")
                    try:
                        twii[k].write(v)
                    except lab_core.ChannelAccessException as e:
                        print(e)
                    except Exception as e:
                        raise e
            elif file_ext == ".json" or file_ext == ".jsonc":
                for k,v in json.json.load(f).items():
                    try:
                        twii[k].write(v)
                    except lab_core.ChannelAccessException as e:
                        print(e)
                    except Exception as e:
                        raise e
            else:
                raise Exception(f'Unknown file type {file_ext}. Contact PyICe-developers@analog.com for more information.')
            f.close()
        return self.twii.read_all_channels()
        
