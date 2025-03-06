import collections
from ..lab_core import *
from .modbus_register import modbus_register
from enum import Enum, auto
import minimalmodbus

class modbus_reg_type(Enum):
    bit = auto()
    register = auto()
    long = auto()
    float = auto()
    string = auto()
    
register_description =  collections.namedtuple('Register_description',
                                                ('name',
                                                'address',
                                                'readable',
                                                'writeable',
                                                'reg_type', #(bit, register, long, float, string)
                                                'signed',
                                                'number_of_decimals', 
                                                'number_of_registers', #for long, float, string
                                                'byteorder', #for long, float
                                                'documentation'),
                                                defaults = (modbus_reg_type.register, None, None, None, None, None),
                                                )


class modbus_instrument(instrument, minimalmodbus.Instrument):
    '''
    https://en.wikipedia.org/wiki/Modbus
    Modbus function codes 
    01: Read coils
    02: Read discrete inputs
    03: Read holding registers
    04: Read input registers
    05: Write single coil
    06: Write single register
    15: Write multiple coils
    16: Write multiple registers
    20: Read file record
    '''
    def __init__(self, interface_raw_serial, modbus_address, baudrate, mode='rtu'):
        minimalmodbus.BAUDRATE = baudrate
        self._base_name = 'Modbus Instrument'
        interface_raw_serial.write = interface_raw_serial.write_raw
        interface_raw_serial.read = interface_raw_serial.read_raw
        instrument.__init__(self,f"Modbus instrument @ {interface_raw_serial}:{modbus_address}")
        minimalmodbus.Instrument.__init__(self, interface_raw_serial, modbus_address, mode = minimalmodbus.MODE_RTU if mode.lower() == 'rtu' else minimalmodbus.MODE_ASCII, debug=False)
        #self.sp = interface_raw_serial
        #self.modbus_address = modbus_address
        #self.modbus_pid = minimalmodbus.Instrument(interface_raw_serial,modbus_address)
        #self.modbus_pid.serial.stopbits = 1
        #self.modbus_pid.serial.timeout = 5
    def _read_register(self, ch):
        return self.read_register(registeraddress=ch.get_attribute('address'),
                                  number_of_decimals=ch.get_attribute('number_of_decimals'),
                                  functioncode=ch.get_attribute('read_functioncode'),
                                  signed=ch.get_attribute('signed'),
                                 )
    def _write_register(self, v, ch):
        return self.write_register(registeraddress=ch.get_attribute('address'),
                                   value=v,
                                   number_of_decimals=ch.get_attribute('number_of_decimals'),
                                   functioncode=ch.get_attribute('write_functioncode'),
                                   signed=ch.get_attribute('signed'),
                                  )
    def add_registers(self, register_descriptions):
        # todo add capability to merge separate MODBUS read/write (only) addresses into one pyice register channel?
        for reg_description in register_descriptions:
            if reg_description.reg_type == modbus_reg_type.bit:
                ch = register(name = reg_description.name,
                              size = 1,
                              #todo lambda closure problem?!??!
                              read_function = None, #lambda addr=reg_description.address: self.read_bit(registeraddress=addr, functioncode=2) if reg_description.readable else None,
                              write_function = None, #lambda v, addr=reg_description.address: self.write_bit(registeraddress=addr, value=v, functioncode=5) if reg_description.writeable else None,
                              )
                ch.set_attribute('read_functioncode', 2)
                ch.set_attribute('write_functioncode', 5)
            elif reg_description.reg_type == modbus_reg_type.register:
                ch = modbus_register(name = reg_description.name,
                              read_function = None, #lambda reg=reg_description: self._read_register(reg) if reg_description.readable else None,
                              write_function = None, #lambda v, reg=reg_description: self._write_register(v, reg) if reg_description.writeable else None,
                              )
                ch.set_attribute('read_functioncode', 3)
                ch.set_attribute('write_functioncode', 16)
            elif reg_description.reg_type in modbus_reg_type:
                raise Exception('Currently unimplemented. Contact PyICe developers')
            else:
                raise Exception(f'Unknown register type {reg_description.reg_type} not a member of {modbus_reg_type}')
            if reg_description.readable:
                ch._read = lambda ch=ch: self._read_register(ch)    
                ch.set_read_access(True)
            else:
                ch.set_read_access(False)
            if reg_description.writeable:
                ch._write = lambda v, ch=ch: self._write_register(v, ch)
                ch.set_write_access(True)
            else:
                ch.set_write_access(False)
            for attr in reg_description._fields:
                if attr is 'number_of_decimals' and getattr(reg_description, attr) is None:
                    ch.set_attribute(attr, 0)
                elif attr is 'signed' and getattr(reg_description, attr) is None:
                    ch.set_attribute(attr, False)
                else:
                    ch.set_attribute(attr, getattr(reg_description, attr))
            ch.set_description(reg_description.documentation)
            self._add_channel(ch)
     
