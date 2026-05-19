"""Tests for saleae."""

from PyICe import lab_instruments, lab_core

m = lab_core.master()
s = lab_instruments.saleae()
for ch in range(8):
    s.add_channel_scalar("ch{}".format(ch), ch)
# for ch in range(8,16):
#    s.add_channel_trace("ch{}".format(ch), ch)
m.add(s)
m.add_channel_delta_timer('log_time')
logger = lab_core.logger(m)
logger.new_table('test_table', replace_table=True)
for i in range(1000000):
    res = logger.log()
    print("Log: {} Time: {}s".format(i, res['log_time']))
