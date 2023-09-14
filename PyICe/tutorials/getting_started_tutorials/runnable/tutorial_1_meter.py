# ============================================
# TUTORIAL 1 Adding a Single Channel Voltmeter
# ============================================

from PyICe import lab_interfaces
interface_factory = lab_interfaces.interface_factory()
my_a34401_interface = interface_factory.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)

from PyICe import lab_core
channel_master = lab_core.channel_master()

from PyICe import lab_instruments
my_a34401 = lab_instruments.agilent_34401a(my_a34401_interface)
channel_master.add(my_a34401)

my_a34401.add_channel("vmeas")
my_a34401.config_dc_voltage()

reading = channel_master.read('vmeas')
print(f"Measuring 'vmeas' using channel_master, reading = {reading}V.")

reading = my_a34401.read('vmeas')
print(f"Measuring 'vmeas' using by circumventing the channel_master and using my_a34401 (not recommended), reading = {reading}V.")

vmeas_channel_object = channel_master['vmeas']  # This gets the channel object. It could also be obtained from my_a34401
reading = vmeas_channel_object.read()
print(f"Measuring 'vmeas' by retreiving the actual channel first and asking it to read. Reading = {reading}.")

reading = channel_master['vmeas'].read()
print(f"Measuring 'vmeas' using the condensed version of rereiving the channel. Reading = {reading}.")