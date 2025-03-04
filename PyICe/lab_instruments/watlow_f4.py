
from .temperature_chamber import temperature_chamber
from .modbus_instrument import modbus_instrument, modbus_reg_type, register_description as rd

class watlow_f4(temperature_chamber, modbus_instrument):
    REGISTERS = [
        rd('Setpoint1', 300, readable=True, writeable=True),
    ]
    def __init__(self, interface_raw_serial, modbus_address, baudrate=19200):
        modbus_instrument.__init__(self,
                                   interface_raw_serial=interface_raw_serial,
                                   modbus_address=modbus_address,
                                   baudrate=baudrate,
                                   mode='rtu')
        temperature_chamber.__init__(self)
        self.add_registers(type(self).REGISTERS)

    
    


    def _write_temperature(self, value):
        '''Program tempertaure setpoint to value. Implement for specific hardware.'''
        self.setpoint = value
    def _read_temperature_sense(self):
        '''read back actual chamber temperature.  Implement for specific hardware.'''
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.'''
    def shutdown(self, shutdown):
        '''separate method to turn off temperature chamber.
        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.
        '''
        self._enable(not shutdown)



