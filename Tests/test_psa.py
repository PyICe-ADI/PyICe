from PyICe import lab_core
from PyICe.lab_instruments import *



m = lab_core.master()
m.set_allow_threading(False)
# sa = keysight_e4440a(m.get_visa_interface('TCPIP::192.168.100.101::5025::SOCKET'))
sa = keysight_e4440a(m.get_visa_interface('TCPIP1::192.168.100.101::inst0::INSTR'), reset=False)
m.add(sa)
# foo = sa.add_channel_xdata('test_x')
# bar = sa.add_channel_ydata('test_y', trace_number=1)
sa.add_chanels('test')
print(m.get_all_channel_names())
breakpoint()
# m['test_trigger'].write('Single')
m.gui()