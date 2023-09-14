# ================================
# TUTORIAL 4 Adding a Power Supply
# ================================

from PyICe import lab_core
from PyICe import lab_interfaces
from PyICe import lab_instruments

interface_factory = lab_interfaces.interface_factory()
supply_interface = interface_factory.get_visa_serial_interface("COM16", baudrate=115200, rtscts=True, timeout=10)

hameg = lab_instruments.hameg_4040(supply_interface)
hameg.add_channel(channel_name="force_voltage", num=3, ilim=1, delay=0.25)

channel_master = lab_core.channel_master()
channel_master.add(hameg)

hameg.add_channel_current(channel_name="current_limit", num=3)

channel_master.write(channel_name='force_voltage', value=5)
channel_master.write(channel_name='current_limit', value=0.5)

print("Reading ALL channels")
print(channel_master.read_all_channels())

print("Reading the '<your_name>_vsense' and '<your_name>_isense' auxilliary channels")
print(channel_master.read_channels(item_list=['force_voltage_vsense', 'force_voltage_isense']))