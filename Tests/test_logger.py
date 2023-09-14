
from PyICe import lab_core, lab_instruments, lab_utils
import random

m = lab_core.master()
m.add_channel_delta_timer('log_speed')
for i in range(1996): #Max 1998 channels to stay within SQLITE_MAX_COLUMN, which defaults to 2000 (+rowid, +datetime), but only 1998 variables can be passed in two tries (+datetime but not rowid).
    ch = m.add_channel_dummy('channel_{:04d}'.format(i))
    ch.write(i)
    if i == 2:
        ch.set_display_format_str('1.1f')
    elif i == 3:
        ch.write([1,2,3,4,5])
    elif i == 4:
        ch.write("hello, world")
    elif i == 5:
        ch.write('hello, "world"')
    elif i == 6:
        ch.write({'a':1,'b,c':2})
l = lab_core.logger(m, database="logger_test.sqlite", use_threads=True)
l.new_table(table_name='dummy_data',replace_table=True)
c = lab_utils.csv_logger(output_file='logger_test.csv')
c.register_logger_callback(l)
print(l.log())
for i in range(10000):
    for ch in m:
        if ch.is_writeable():
            ch.write(random.random())
    print('{i}: {log_speed}'.format(i=i,**l.log()))

