import collections
from ..lab_core import *
from .modbus_register import modbus_register #todo use?
from enum import Enum, auto
import minimalmodbus

class modbus_reg_type(Enum)
    bit = auto()
    register = auto()
    long = auto()
    float = auto()
    string = auto()
    
register_description =  collections.namedtuple('Register_description',
                                                'name',
                                                'address',
                                                'readable',
                                                'writeable',
                                                'reg_type', #(bit, register, long, float, string)
                                                'signed',
                                                'number_of_decimals', 
                                                'number_of_registers', #for long, float, string
                                                'byteorder', #for long, float
                                                'documentation',
                                                defaults = (modbus.register, None, None, None, None, None),
                                                )


class modbus_instrument(instrument, minimalmodbus.Instrument):
    def __init__(self, interface_raw_serial, modbus_address, baudrate, mode='rtu'):
        minimalmodbus.BAUDRATE = baudrate
        self._base_name = 'Modbus Instrument'
        interface_raw_serial.write = interface_raw_serial.write_raw
        interface_raw_serial.read = interface_raw_serial.read_raw
        instrument.__init__(self,f"Modbus instrument @ {interface_raw_serial}:{modbus_address}")
        minimalmodbus.Instrument.__init__(self, interface_raw_serial, modbus_address, mode = minimalmodbus.MODE_RTU if mode.lower() == 'rtu' else minimalmodbus.MODE_ASCII, debug=True)
        #self.sp = interface_raw_serial
        #self.modbus_address = modbus_address
        #self.modbus_pid = minimalmodbus.Instrument(interface_raw_serial,modbus_address)
        #self.modbus_pid.serial.stopbits = 1
        #self.modbus_pid.serial.timeout = 5
    def add_registers(self, resigter_descriptions):
        for reg_description in register_descriptions:
            if reg_description.reg_type == modbus_reg_type.bit:
                ch = register(name = reg_description.name,
                              size = 1,
                              read_function = lambda addr=reg_description.address: self.read_bit(registeraddress=addr, functioncode=2) if reg_description.readable else None,
                              write_function = lambda v, addr=reg_description.address: self.write_bit(registeraddress=addr, value=v, functioncode=5) if reg_description.writeable else None,
                              )
            elif reg_description.reg_type == modbus_reg_type.register:
                ch = register(name = reg_description.name,
                              size = 16,
                              read_function = lambda addr=reg_description.address,
                                                     nod=reg_description.number_of_decimals,
                                                     signed=reg_description.signed: self.read_register(registeraddress=addr,
                                                                                                       number_of_decimals=nod,
                                                                                                       functioncode=3,
                                                                                                       signed=signed) if reg_description.readable else None,
                              write_function = lambda v, 
                                                      addr=reg_description.address,
                                                      nod=reg_description.number_of_decimals,
                                                      signed=reg_description.signed: self.write_register(registeraddress=addr,
                                                                                                         value=v,
                                                                                                         number_of_decimals=nod,
                                                                                                         functioncode=16,
                                                                                                         signed=signed) if reg_description.writeable else None,
                              )
            elif reg_description.reg_type in modbus_reg_type:
                raise Exception('Currently unimplemented. Contact PyICe developers')
            else:
                raise Exception(f'Unknown register type {reg_description.reg_type} not a member of {modbus_reg_type}')
            ch.set_description(reg_description.documentation)
            self._add_channel(ch)
     
