from ..lab_core import *
from .temperature_chamber import temperature_chamber

class TestEquity_115(temperature_chamber):
    '''
    TestEquity_115 with basic channels
    '''
    def __init__(self, interface_raw_serial):
        import minimalmodbus
        minimalmodbus.BAUDRATE = 9600
        minimalmodbus.TIMEOUT = 5       
        # self._base_name = f"TestEquit115A @ {self.comport}"
        self._base_name = "TestEquit115A"        
        temperature_chamber.__init__(self)
        self.sp = interface_raw_serial        
        interface_raw_serial.write = interface_raw_serial.write_raw
        interface_raw_serial.read = interface_raw_serial.read_raw
        self.add_interface_raw_serial(interface_raw_serial)
        self.modbus_pid = minimalmodbus.Instrument(interface_raw_serial, slaveaddress=1)
    
    def add_channels(self, channel_name):
        temp_channel = temperature_chamber.add_channels(self, channel_name)
        return temp_channel
        
    def add_channel_enable_output(self, channel_name):
        '''Enable/Disable heat and cool outputs.'''
        new_register = register(f'{channel_name}_enable',
                                size=1,
                                read_function=lambda: False if self.modbus_pid.read_register(2000, functioncode=3) else True,
                                write_function=self._enable)
        new_register.add_preset('Run',True)
        new_register.add_preset('Stop',False)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Enables')
        new_register.set_description(self.add_channel_enable_output.__doc__)
        return self._add_channel(new_register)

    def _enable(self, enable):
        self.modbus_pid.write_register(2000, 0 if enable else 1, functioncode=6)
        
    def _read_temperature_sense(self):
        temp = None
        while (temp == None):
            try:
                temp=self.modbus_pid.read_register(100, 1, 3, True)
            except (IOError, ValueError):
                if self.__scriptDebug == True:  print ("TE115A: get_temp communication error")
                time.sleep(5)
                pass
        return float(temp)
        
    def _write_temperature(self, value):
        self.modbus_pid.write_register(300, float(value), 1, 16, True)
        
    def instrumentInfoString(self):
        return "%s - %s - SN:%s - %s" % \
            (self._manufacturer, self._modelNumber, self._serialNumber, self._address) 
