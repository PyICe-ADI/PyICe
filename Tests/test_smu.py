from PyICe import lab_core
from PyICe.lab_instruments import *


m = lab_core.master()
m.set_allow_threading(False)
s = keithley_2400(m.get_visa_serial_interface('com8', baudrate=57600, xonxoff=True))
m.add(s)
foo = s.add_channels('test', channel_number=1)
print(m.get_all_channel_names())
v = m['test_vforce'] 
i = m['test_iforce'] 
print(m.read_all_channels())
m['test_iforce'].write(0.05)
print(m.read_all_channels())
m.gui()