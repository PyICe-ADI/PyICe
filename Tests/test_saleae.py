
from PyICe import lab_instruments, lab_core

m = lab_core.master()
s = lab_instruments.saleae()
for ch in range(8):
    s.add_channel_scalar("ch{}".format(ch), ch)
#for ch in range(8,16):
#    s.add_channel_trace("ch{}".format(ch), ch)
m.add(s)
m.add_channel_delta_timer('log_time')
l = lab_core.logger(m)
l.new_table('test_table', replace_table=True)
for i in range(1000000):
    res = l.log()
    print("Log: {} Time: {}s".format(i,res['log_time']))