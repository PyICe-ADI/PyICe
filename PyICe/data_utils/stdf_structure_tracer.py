
import functools
import math
import os
import re
import sqlite3
import sys
import time

try:
    from pystdf.IO import Parser
    import pystdf.V4
    # from pystdf.Writers import format_by_type
except ModuleNotFoundError as e:
    # pystdf is needed for processing files, but not needed for audits, IVY and other Linux PyICe usage.
    print(f'WARNING: Import error with pystdf library. This is ok if not processing STDF dlogs directly, and temporarily expected in Linux because of Anaconda package issues.\n{type(e)}: {e.args}')

class record_order_parser:
    def __init__(self):
        self._indent = 0 #todo
        self._last_record_type = None
        self._record_count = 0
        self._repeat_count = 0
    def map_data(self, record_type, data):
        class pretty_dict(dict):
            def __str__(self):
                hex_fields = ('TEST_FLG', 'PARM_FLG',)
                bin_fields = (),
                dcopy = pretty_dict(self) #don't mess up data!
                for (k,v) in dcopy.items():
                    if k in hex_fields:
                        dcopy[k] = f'0x{v:X}'
                    elif k in bin_fields:
                        dcopy[k] = f'0b{v:B}'
                return super(type(self), dcopy).__str__()
        dmap = pretty_dict()
        for (k,v) in zip(record_type.fieldNames, data):
            dmap[k] = v
        return dmap
    def after_begin(self, dataSrc):
        self.dataSrc = dataSrc
        self.inp_file = self.dataSrc.inp.name
        print(f'Processing {self.inp_file}')
        self._dut_count = 0
    def after_send(self, dataSrc, data):
        if data is None:
            breakpoint()
        record_type = type(data[0])
        record_data = self.map_data(*data)
        # if None in data[1]:
            # print(record_data)
            # breakpoint()
        self._record_count += 1
        
        openers = (pystdf.V4.Far, pystdf.V4.Pir,) # pystdf.V4.Mir,
        results = (pystdf.V4.Ptr, pystdf.V4.Mpr, pystdf.V4.Ftr,)
        closers = (pystdf.V4.Prr, pystdf.V4.Mrr,)
        summary = (pystdf.V4.Tsr, pystdf.V4.Hbr, pystdf.V4.Sbr, pystdf.V4.Pcr)
        
        no_summarize = (pystdf.V4.Atr,)

        if record_type == self._last_record_type and record_type not in no_summarize:
            self._repeat_count += 1
        else:
            if self._repeat_count != 0:
                print(f'{" "*self._indent}{self._last_record_type}: (*{self._repeat_count})')
            self._repeat_count = 0

        if record_type in closers:
            self._indent -= 2
        
        if record_type != self._last_record_type or record_type in no_summarize:        
            print(f'{" "*self._indent}{record_type}: {record_data}')

        if record_type in openers:
            self._indent += 2
        self._last_record_type = record_type
        if record_type == pystdf.V4.Prr:
            self._dut_count += 1
    def after_complete(self, dataSrc):
        print(f'Processed {self._dut_count} DUTs.')

def process_file(filename):
    with open(filename, 'rb') as f:
        p = Parser(inp=f, reopen_fn=None)
        p.addSink(record_order_parser())
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        for f in sys.argv[1:]:
            process_file(f)
    else:
        process_dir(r'.')
