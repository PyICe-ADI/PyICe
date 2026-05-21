"""Tests for  Franken oven."""
from PyICe import lab_core
from PyICe.lab_instruments.Franken_oven import Franken_oven

m = lab_core.master()
oven = Franken_oven(m.get_raw_serial_interface('com5'))
# oven.add_channels('temp')
# oven.add_advanced_channels('advtemp')
oven.add_channel('temp')

print(oven.get_all_channel_names())

m.add(oven)
m.gui()
