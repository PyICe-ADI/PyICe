# ========================================
# TUTORIAL 2 Logging Data to a SQLite File
# ========================================

from PyICe import lab_core
from PyICe import lab_interfaces
from PyICe.lab_instruments.agilent_34401a import agilent_34401a

interface_factory = lab_interfaces.interface_factory()
my_a34401_interface = interface_factory.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)
my_a34401 = agilent_34401a(my_a34401_interface)

my_a34401.add_channel("vmeas")
my_a34401.config_dc_voltage()

channel_master = lab_core.channel_master()
channel_master.add(my_a34401)

logger = lab_core.logger(channel_master)
logger.new_table(table_name='tutorial_2_table', replace_table=True)

print("Logging all channels...")
for measurement in range(10):
   print(f"Logging measurement number: {measurement}")
   logger.log()
print("\n\nConsider opening data_log.sqlite with DB Browser https://sqlitebrowser.org/ and opening the [Browse Data] tab.")