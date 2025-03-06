
from .temperature_chamber import temperature_chamber
from .modbus_instrument import modbus_instrument, modbus_reg_type, register_description as rd

class watlow_f4(temperature_chamber, modbus_instrument):
    REGISTERS = [
        rd('SV1', 300, readable=True, writeable=True, signed=True),
        rd('PV1', 100, readable=True, writeable=False, signed=True),
        rd('heat_power', 103, readable=True, writeable=False, number_of_decimals=2, signed=True),
        rd('cool_power', 107, readable=True, writeable=False, number_of_decimals=2, signed=True),
        #308 Idle Set Point, Channel 1, Power Out Action
        #1206 Power-Out Action
        #2072 Power On
        #2073 Power Off
    ]
    def __init__(self, interface_raw_serial, modbus_address, baudrate=19200):
        self._base_name = 'Watlow F4'
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
        self['SV1'].write(value)
        self._wait_settle()
    def _read_temperature_sense(self):
        '''read back actual chamber temperature.  Implement for specific hardware.'''
        return self['PV1'].read()
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.'''
        if enable:
            pass #?
        else:
            self['SV1'].write(25)
    def shutdown(self, shutdown):
        '''separate method to turn off temperature chamber.
        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.
        '''
        self._enable(not shutdown)



