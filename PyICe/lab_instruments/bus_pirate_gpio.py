from PyICe.lab_core import *
import time

class bus_pirate_gpio(instrument):
    '''bus pirate board as a gpio driver, uses binary mode to control and read up to 5 bits.'''
    def __init__(self,interface_raw_serial):
        '''creates a bus_pirate_gpio object, serial_port can be a pyserial object or a string'''
        self._base_name = 'bus_pirate_gpio'
        instrument.__init__(self,f"BUS PIRATE {interface_raw_serial}")
        self.add_interface_raw_serial(interface_raw_serial)
        self.ser = interface_raw_serial
        self._config_bus_pirate_binary()
        self.output_data = 0
        self.output_enable_mask = 0b00011111 # start as inputs, inputs are 1
        self.pin_names = ["AUX","MISO","CS","MOSI","CLK"]
        self.pin_mask = {"AUX":16,"MOSI":8,"CLK":4,"MISO":2,"CS":1}
    def _config_bus_pirate_binary(self):
        self.ser.write('\n'*10) #exit any menus
        self.ser.write('#') #reset
        self.ser.read(self.ser.inWaiting())
        #get into binary mode
        resp = ''
        tries = 0
        while (resp != 'BBIO1'):
            tries += 1
            if (tries > 20):
                raise Exception('Buspirate failed to enter binary mode after 20 attempts')
            #print(f'Buspirate entering binary mode attempt {tries}:')
            self.ser.write('\x00') #enter binary mode
            time.sleep(0.02)
            resp = self.ser.read(self.ser.inWaiting())
    def _bus_pirate_set_as_outputs(self,pin_names):
        #both writes and reads, its how the bus pirate works
        self.ser.read(self.ser.inWaiting())
        for pin_name in pin_names:
            self.output_enable_mask &= ~self._get_mask(pin_name)
        byte =  chr(0x40 | self.output_enable_mask)
        self.ser.write(byte) # write bits
        time.sleep(0.01)
        read_data = self.ser.read(self.ser.inWaiting())
        return read_data
    def _bus_pirate_get_pin_state(self):
        return ord(self._bus_pirate_set_as_outputs([]))
    def _bus_pirate_write_outputs(self):
        byte = chr(0xC0 | self.output_data)
        byte = chr(0xE0 | self.output_data)
        self.ser.write(byte) # write bits
        time.sleep(0.01)
        resp = self.ser.read(self.ser.inWaiting())
        #print bin(ord(resp))
    def _get_mask(self,pin_name):
        return self.pin_mask[pin_name]
    def add_channel(self,channel_name,pin_names,output,value=0):
        '''add channel by channel_name,
            ie to create a 3 bit digital output channel on pins CLK,MISO,MOSI add_channel("channel_name",["CLK",MISO",MOSI"],output=1)
            as always the FIRST pin is the MSB'''
        if isinstance(pin_names, type("")):
            pin_names = [pin_names] #convert to a list if a string was given
        pin_names = [pin_name.upper() for pin_name in pin_names]
        for pin_name in pin_names:
            if pin_name not in self.pin_names:
                raise Exception(f"{pin_name}: not a valid pin name")
        if output:
            new_channel = channel(channel_name,write_function=lambda value: self._write_pins(pin_names,value))
            new_channel.write(value)
            self._bus_pirate_set_as_outputs(pin_names)
        else:
            new_channel = channel(channel_name,read_function=lambda: self._read_pins(pin_names))
        return self._add_channel(new_channel)
    def _write_pins(self,pin_names,value):
        '''Write named channel to value.  Value is an integer which counts by "1".
            The value is automatically truncated and shifted according to the location information
            provided to add_channel().  The remainder of the digital word not included in the channel remains unchanged.'''
        if value > pow(2,len(pin_names)):
            raise Exception(f'Buspirate {pin_names}: value {value} too large')
        for pin_name in reversed(pin_names):
            pin_mask = self._get_mask(pin_name)
            if value & 1 == 1:
                self.output_data |= pin_mask
            else:
                self.output_data &= ~pin_mask
            value >>= 1
        self._bus_pirate_write_outputs()
    def _read_pins(self,pin_names):
        '''Return the forcing value for the named channel.'''
        data = 0
        pin_data = self._bus_pirate_get_pin_state()
        for pin_name in pin_names:
            data <<= 1
            if pin_data & self.pin_mask[pin_name]:
                data |= 1
        return data
