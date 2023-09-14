# ============================
# TUTORIAL 6 The Code-Free GUI
# ============================

from PyICe import lab_core, lab_instruments

channel_master = lab_core.channel_master()
a34401_interface = channel_master.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)
supply_interface = channel_master.get_visa_serial_interface("COM16", baudrate=115200, rtscts=True, timeout=10)

a34401 = lab_instruments.agilent_34401a(a34401_interface)
a34401.add_channel("vresistor_vsense")
a34401.config_dc_voltage()

hameg = lab_instruments.hameg_4040(supply_interface)
hameg.add_channel(channel_name="vsweep", num=3, ilim=1, delay=0.25)
hameg.add_channel_current(channel_name="current_limit", num=3)
channel_master.add(a34401)
channel_master.add(hameg)

channel_master.gui()