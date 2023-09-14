'''
SPI Interface Hardware Drivers
==============================

Created on Feb 23, 2015
Heavily modified August 2016 to be more generic.

@author: JKapasi
@author: DSimmons

The SPI interface is composed of two separate classes: 

1) shift_register
    abstracts individual bit-fields into integer representing contents of full-length shift register
2) spiInterface: Defines the hardware interface including baudrate, mode (CPOL/CPHA), CS operation.
    Specific hardware implementations should overload this class and implement _shift_data method.

'''

# Notes:
# 1) spiSlave removed. 
    # Generically, SPI data does not represent registers or addresses memory.
    # There's no guarantee that returned data has same meaning as transmitted data.
    # Likewise, SPI doesn't fit well with the SPI_instrument class generically.
    # Specifically, the 7-bit address and command code is very SMBus specific and should probably be removed to a slave-specific file.
# 2) The beaglebond SPI master got broken.
    # The spiInterface parent class had significant changes to support generic-length SPI DUTs and arbitrary SPI Master hardware requirements.
    # Because we can't test/debug operation of the beaglebone port, it's commented out until someone has a physical test bench.


try:
    from Adafruit_BBIO.SPI import SPI
    SPI_BBIO_missing = False
except ImportError as e:
    SPI_BBIO_missing = True

import struct, array, time, numbers, collections, random
from abc import ABCMeta, abstractmethod

class shift_register(object):
    '''helper class to assemble multiple bit-fields together into a single larger integer and to disassemble received data into individual bit-fields.'''
    def __init__(self, name=''):
        '''Linear shift register model.
        
        Add bit_fields later in msb->lsb order using repeated calls to add_bit_field()'''
        self._bit_field_bit_counts = []
        self._bit_field_names = []
        self._bit_field_descriptions = []
        self.name = name
    def __len__(self):
        '''support len() builtin to return total number of bits in shift register'''
        bit_count = 0
        for bfc in self._bit_field_bit_counts:
            bit_count += bfc
        return bit_count
    def __str__(self):
        '''graphical view of register structure if object is printed'''
        hr = '--'
        line1 = ' |'
        line2 = ' |'
        offset = 0
        for name,size in reversed(list(zip(self._bit_field_names,self._bit_field_bit_counts))):
            if size == 1:
                sr = '{}'.format(offset)
                bf = '{}[0]'.format(name)                
            else:
                sr = '{}:{}'.format(offset+size-1,offset)
                bf = '{}[{}:0]'.format(name,size-1)
            offset += size
            chars = max(len(sr),len(bf))
            hr += '-' * (chars + 3)
            line1 = ' | {}{}'.format(sr.center(chars),line1)
            line2 = ' | {}{}'.format(bf.center(chars),line2)
        line1 = line1[1:] + '\n'
        line2 = line2[1:] + '\n'
        hr = hr[1:] + '\n'
        return 'SPI Shift Register Data Mapping Object\n' + hr + line1 + hr + line2 + hr
    def __add__(self,other):
        '''support concatenation of multiple instances using '+' operator'''
        assert isinstance(other,shift_register)
        for bf in list(self.keys()):
            if bf in list(other.keys()):
                raise Exception('Duplicated bit field name not allowed when concatenating shift_register instances: {}'.format(bf))
        new_sr = shift_register(name='{} + {}'.format(self.get_name(), other.get_name()))
        new_sr._bit_field_bit_counts = self._bit_field_bit_counts + other._bit_field_bit_counts
        new_sr._bit_field_names = self._bit_field_names + other._bit_field_names
        new_sr._bit_field_descriptions = self._bit_field_descriptions + other._bit_field_descriptions
        return new_sr
    def __iter__(self):
        '''iterate over bit field names ms field to ls field'''
        return iter(self._bit_field_names)
    def __getitem__(self, key):
        '''return size (bit count) of named bit field.
        use with dictionary-style lookup: my_shift_register['my_key']'''
        index = self._bit_field_names.index(key)
        return self._bit_field_bit_counts[index]
    def _check_size(self, data, clk_count):
        '''make sure externally supplied data can fit within allocated bit field width'''
        assert isinstance(data, numbers.Integral)
        assert isinstance(clk_count, numbers.Integral)
        assert data >= 0 
        assert data < 2**clk_count
        return True
    def add_bit_field(self, bit_field_name, bit_field_bit_count, description=''):
        '''build SPI shift register data protocol sequentially MSB->LSB with repeated calls to add_bit_field'''
        assert isinstance(bit_field_name, str)
        assert isinstance(bit_field_bit_count, numbers.Integral)
        assert bit_field_bit_count > 0
        try:
            dup_index = self._bit_field_names.index(bit_field_name)
        except ValueError: #bit field name not already used
            self._bit_field_names.append(bit_field_name)
            self._bit_field_bit_counts.append(bit_field_bit_count)
            self._bit_field_descriptions.append(description)
        else:
            raise ValueError('Duplicated bit field name: {} at position: {}.'.format(bit_field_name, dup_index))
    def keys(self):
        '''return list of bit-field names registered with instance'''
        return self._bit_field_names[:]
    def display(self):
        '''print ascii register structure graphic'''
        print(str(self))
    def get_description(self, key):
        '''return bit field description string'''
        index = self._bit_field_names.index(key)
        return self._bit_field_descriptions[index]
    def get_name(self):
        '''return shift register name'''
        return self.name
    def pack(self, bit_field_data_dict):
        '''pack bit fields into single larger integer. also return accumulated clk_count.
        Suitable for passing directly to spiInterface.transceive(*shift_register.pack(bit_field_data_dict))
        bit_field_data_dict should contain one key-value pair for each defined bit_field'''
        #don't check for extra entries in bit_field_data_dict that don't go with this shift register. Any reason to???
        val = 0
        offset = 0
        for name,size in reversed(list(zip(self._bit_field_names,self._bit_field_bit_counts))):
            self._check_size(bit_field_data_dict[name], size)
            val += bit_field_data_dict[name] << offset
            offset += size
        return (val, offset)
    def unpack(self, data):
        '''unpack single integer representing full-width shift register data into individual bit field values according to instance-defined boundaries.
        return dictionary with key-value pairs for each defined bit_field_name and bit_field data.
        '''
        bf_data = []
        for size in reversed(self._bit_field_bit_counts): #iterate backwards because accumulated shift offsets are not yet known.
            bf_data.insert(0,int(data & 2**size-1))
            data = data >> size
        res = collections.OrderedDict()
        for i,name in enumerate(self._bit_field_names): #reverse order back to MSByte first
            res[name] = bf_data[i]
        return res
    def copy(self, prepend_str='', append_str='', keep_name=False):
        '''return new shift register with identical structure to self, but with bit field names augmented with prepend_str and append_str

        by default, shift register name will also be augmented with prepend_str and append_str. Suppress this behavior by setting keep_name=False.'''
        if keep_name:
            name = self.get_name()
        else:
            name = '{}{}{}'.format(prepend_str, self.get_name(), append_str)
        selfcopy = shift_register(name=name)
        selfcopy._bit_field_bit_counts = [count for count in self._bit_field_bit_counts]
        selfcopy._bit_field_names = ['{}{}{}'.format(prepend_str, name, append_str) for name in self._bit_field_names]
        selfcopy._bit_field_descriptions = [description for description in self._bit_field_descriptions]
        return selfcopy

class spiInterface(object, metaclass=ABCMeta):
    def __init__(self,CPOL,CPHA,ss_ctrl,word_size):
        '''mode controls polarity and phase: 0 => CPOL=0, CPHA=0
                                             1 => CPOL=0, CPHA=1
                                             2 => CPOL=1, CPHA=0
                                             3 => CPOL=1, CPHA=1
           ss_ctrl function takes boolean argument to control SS/_CS if necessary for hardware.
            Select slave if argument evaluates to True.
          word size defines SPI master shirt register length. ex 1,8,16 bits. Transactions must be (automatically) padded by modulo word_size. to align correctly.
          
          TODO: add option to send data LSB first?'''
        self.CPOL = CPOL
        self.CPHA = CPHA
        if self.CPOL == 0 and self.CPHA == 0:
            self.mode = 0
        elif self.CPOL == 0 and self.CPHA == 1:
            self.mode = 1
        elif self.CPOL == 1 and self.CPHA == 0:
            self.mode = 2
        elif self.CPOL == 1 and self.CPHA == 1:
            self.mode = 3
        else:
            raise SPIMasterError('Invalid CPOL/CPHA setting')
        self.set_ss_ctrl(ss_ctrl_function = ss_ctrl)
        self.word_size = word_size
        self.set_strict_alignment(True)
    def set_strict_alignment(self, strict):
        '''If true, enforce that SPI master and slave hardware lengths match.
        If false, enable automatic padding to correct alignment.'''
        self._strict_alignment = strict
        self._warned_once = False
    def set_ss_ctrl(self, ss_ctrl_function):
        '''change ss_ctrl function after instantiation.
        function should take single boolean argument.
        If true, assert slave select. If false, deassert slave select.
        There will typically be a logic inversion inside ss_ctrl to achieve active low _cs.
        '''
        self._ss_ctrl = ss_ctrl_function
    @abstractmethod
    def _shift_data(self, data_out, clk_count):
        '''Hardware-specific Function that will shift data in/out of the SPI interface.
        data_out is transmitted via MOSI
        return data received bia MISO
        data formats are as in integer, MSB (first clock) to LSB (last clock)
        pack and unpack methods may be helpful to break integer data into interface hardware-aligned chunks.
        shift_register class may be helpful to pack DUT bit field chunks into full shift register width integer
        Subclass implementation should raise SPIMasterError exception if unable to send message of length clk_count
        (ie hardware limited to byte-aligned messages)'''
        raise SPIMasterError('Overload required.')
    @staticmethod
    def _check_size(data, bits):
        '''make sure data fits within word of length  "bits"'''
        assert isinstance(data, numbers.Integral)
        assert isinstance(bits, numbers.Integral)
        assert data >= 0 
        assert data < 2**bits
        return True
    @staticmethod
    def pack(data_list, word_size=8):
        '''pack byte,word aligned pieces (list) from communication hardware into single integer comprising full shift register width.
        integer can then be broken up by shift_register object into bit field aligned pieces.'''
        res = 0
        offset = 0
        for i in reversed(data_list):
            res += i << offset
            offset += word_size
        return res
    def unpack(self, data, bit_count, word_size=8):
        '''break full shift register width integer into byte,word aligned pieces. Return list of pieces MS first, LS last.
        helper to send byte-aligned pieces to hardware even if bit fields span bytes (or 1-bit, 16-bit 32-bit, etc words for other hardware)'''
        assert bit_count % word_size == 0 #partially filled blocks create aligment ambiguity
        self._check_size(data, bit_count)
        res = []
        while bit_count > 0:
            res.insert(0, data & 2**word_size-1)
            data = data >> word_size
            bit_count -= word_size
        return res
    def transceive(self, data, clk_count):
        '''send data word out MOSI with clk_count clocks.
        return word of same size read simultaneously on MISO.
        Frame entire transaction with slave select.'''
        self._check_size(data,clk_count)
        framing_excess = clk_count % self.word_size
        if framing_excess != 0:
            if self._strict_alignment:
                raise SPIMasterError('Slave shift register length: {} does not match SPI Master hardware word size: {}. {} bit{} are left over. Call spiInterface.set_strict_alignment(False) to enable automatic data padding.'.format(clk_count, self.word_size, framing_excess, 's' if framing_excess > 1 else ''))
            else:
                pad_bits = self.word_size - framing_excess
                if not self._warned_once:
                    print("WARNING: SPI transaction padded {} bit{} to {} bits to align with {} bit SPI master hardware".format(pad_bits, 's' if pad_bits > 1 else '', clk_count+pad_bits, self.word_size))
                    self._warned_once = True
        else:
            pad_bits = 0
        result = None
        self._ss_ctrl(True)
        try:
            result = self._shift_data(data, clk_count+pad_bits) #MSB first; pad bits are zero, go in first, and should shift out the end of slave hardware.
        finally:
            self._ss_ctrl(False) #don't leave bus hung
        if result is not None:
            result = result >> pad_bits #MSB first; Slave data comes out first, followed by meaningless data caused by extra pad clocks.
        return result

class spi_bbone(spiInterface):
    '''The Beaglebone black will use the Adafruit BBIO,
    thus we can initialize this package for all purposes
    This instrument probably got a broken when the parent class interface was modified to support multiple interface hardware boards and more general SPI communication.
    Needs testing/repair.'''
    # def __init__(self,baudrate,timeout,device_num, mode=0, ss_ctrl=lambda ss: None):
        # '''device num is a tuple eg. (0,0)
        # '''
        # spiInterface.__init__(self,mode,ss_ctrl)
        # self.baudrate = baudrate
        # self.timeout = timeout #does this do anything???
        # if not isinstance(device_num, tuple):
            # raise TypeError
        # if SPI_BBIO_missing:
            # print "The SPI module is missing.  This is expected if you are not using a Beaglebone single board computer."
            # raise SPIMasterError("AdaFruit_BBIO is missing on this computer")
        # else:
            # self.spi = SPI(*device_num)
            # self.spi.msh=baudrate
            # self.spi.mode=mode #CPOL/CPHA
    # def __del__(self):
        # self.spi.close()
    # def _shift_data(self, transfer_list):
        # return self.spi.xfer2(transfer_list)
    # @staticmethod
    # def get_byte_list(input_num, format_code='>B'):
        # '''Take number as input and output as a byte list.
        # The format_code should be of the form "XY", where 
        # X is > (Big-endian) or < (Little-endian) and
        # Y is H/L/Q (unsigned short/long/long_long)''' 
        # # eg. input_int = 0xC0DEDBAD
        # s = struct.pack(format_code, input_num)
        # a = array.array("B")  # B: Unsigned bytes
        # a.fromstring(s)
        # result = a.tolist()
        # # print "byte list", result # [192, 222, 219, 173]
        # return result
    # @staticmethod
    # def get_data(input_list, format_code):
        # '''Take an input_list, a list of bytes, and pack into an unsigned short/long/long_long.
        # The format_code should be of the form "XY", where 
        # X is > (Big-endian) or < (Little-endian) and
        # Y is H/L/Q (unsigned short/long/long_long)'''    
        # a = array.array("B")  # B: Unsigned bytes
        # a.fromlist(input_list)
        # s = a.tostring()
        # h = struct.unpack(format_code, s)[0] 
        # return h
        
class spi_cfgpro(spiInterface):
    def __init__(self,visa_interface, CPOL, CPHA, baudrate=1e6, ss_ctrl=None):
        self.interface = visa_interface
        if ss_ctrl is None:
            self.ss_ctrl = self.cs
        else:
            self.ss_ctrl = ss_ctrl
        spiInterface.__init__(self, CPOL, CPHA, ss_ctrl=self.ss_ctrl, word_size=8)

        self.interface.write(':SPI:ENable 0')
        self.interface.write(':SPI:ENable 1')
        self.interface.write(':SPI:Dorder 0') #MSB first
        if float(baudrate) == 4e6:
            self.interface.write(':SPI:CLOCk:RATE 0')
        elif float(baudrate) == 1e6:
            self.interface.write(':SPI:CLOCk:RATE 1')
        elif float(baudrate) == 250e3:
            self.interface.write(':SPI:CLOCk:RATE 2')
        elif float(baudrate) == 125e3:
            self.interface.write(':SPI:CLOCk:RATE 3')
        elif float(baudrate) == 8e6:
            self.interface.write(':SPI:CLOCk:RATE 4')
        elif float(baudrate) == 2e6:
            self.interface.write(':SPI:CLOCk:RATE 5')
        elif float(baudrate) == 500e3:
            self.interface.write(':SPI:CLOCk:RATE 6')
        elif float(baudrate) == 250e3: #yes, it's really duplicated
            self.interface.write(':SPI:CLOCk:RATE 7')
        else:
            raise SPIMasterError('Invalid SPI baud rate for Configurator Pro interface: {}'.format(float(baudrate)))
        if CPOL == 0:
            self.interface.write('SPI:CLOCk:POLarity 0')
        else:
            self.interface.write('SPI:CLOCk:POLarity 1')
        if CPHA == 0:
            self.interface.write('SPI:CLOCk:PHASe 0')
        else:
            self.interface.write('SPI:CLOCk:PHASe 1')
    def cs(self, select):
        if select:
            self.interface.write('SPI:SSELect:ENable')
        else:
            self.interface.write('SPI:SSELect:DISable')
    def __del__(self):
        self.interface.close()
    def _shift_data(self, data_out, clk_count):
        resp = []
        for byte in self.unpack(data_out, clk_count, self.word_size):
            resp.append(int(self.interface.ask(':SPI:TRANsceive? {:02X}'.format(byte)),16))
        return self.pack(resp, self.word_size)

class spi_dc590(spiInterface):
    def __init__(self,interface_stream, ss_ctrl=None):
        '''no remote computer control over CPOL/CPHA mode or baudrate using DC590 sketch...
            Atmega328P does support variable baudrates and clock polarity/phase. See datasheet section 23.4, pp219-222.
            DC590B Enhanced Linduino sketch supports this options, but PyICe doesn't yet. See 'M' command hierarchy new subcommands '0','1','2','3'.
            Also, SPI communication seems to be broken with PyICe DC590ListRead.ino sketch for unknown reasons. Stock DC590 sketch works. 'C' command in set_gpio conflicts with list read stream enable and doesn't seem to correspond to current or past Linduino/DC590 command set either!'''
        self.interface = interface_stream
        if ss_ctrl is None:
            ss_ctrl = lambda ss: self.set_cs(not ss) #active low
        spiInterface.__init__(self, CPOL=0, CPHA=0, ss_ctrl=ss_ctrl, word_size=8)
        self.init_spi()
    def set_cs(self, level):
        '''control DC590 CS pin.
        If true, pin high. No active low inversion here.'''
        if level:
            self.interface.write('X')
        else:
            self.interface.write('x')
    def set_gpio(self, level):
        '''control DC590 Pin 14 GPIO pin as output.
        If true, pin high.'''
        if level:
            self.interface.write('COG')
        else:
            self.interface.write('COg')
    def init_spi(self):
        time.sleep(2.5) #Linduino bootloader delay!
        self.interface.write('\n'*10) 
        time.sleep(2.5) #Linduino bootloader delay!
        print('DC590 init response: {}'.format(self.interface.read(None)[0])) #discard any responses
        self.interface.write('O') #Enable isolated power
        try:
            self.spi_mode()
        except SPIMasterError as e:
            print(e)
    def spi_mode(self):
        '''Switch DC590 I2C/SPI mux to SPI'''
        self.interface.write('MS') #Switch to isolated SPI Mode
        time.sleep(0.1)
        buffer = self.interface.read(None)[0]
        if len(buffer):
            raise SPIMasterError('Error switching DC590 to SPI Mode. Unexpected data in buffer:{}'.format(buffer))
    def __del__(self):
        self.interface.close()
    def _shift_data(self, data_out, clk_count):
        resp = []
        for byte in self.unpack(data_out, clk_count, self.word_size):
            self.interface.write('T{:02X}'.format(byte))
            stream_resp = self.interface.read(2)
            if len(stream_resp[0]) != 2:
                raise SPIMasterError('Short response to SPI transceive: {}. SPI mode enabled?'.format(stream_resp[0]))
            elif stream_resp[1] != 0:
                raise SPIMasterError('Long response to SPI transceive: {} then {}'.format(stream_resp[0]), elf.interface.read(None)[0])
            else:
                resp.append(int(stream_resp[0], 16))
        return self.pack(resp, self.word_size)

class spi_buspirate(spiInterface):
    def __init__(self,interface_raw_serial, CPOL=0, CPHA=0, baudrate=1e6, ss_ctrl=None):
        self.ser = interface_raw_serial
        if ss_ctrl is None:
            self.ss_ctrl = self.cs
        else:
            self.ss_ctrl = ss_ctrl
        spiInterface.__init__(self, CPOL, CPHA, ss_ctrl=self.ss_ctrl, word_size=8)
        self.__init_spi()
        self.set_baudrate(baudrate)
        self.set_mode() #uses self.mode from parent class __init__
    def __init_spi(self):
        self.ser.write('\n'*10) #exit any menus
        self.ser.write('#') #reset
        self.ser.read(self.ser.inWaiting())
        #get into binary mode
        resp = ''
        tries = 0
        while (resp != 'BBIO1'):
            tries += 1
            if tries > 20:
                raise SPIMasterError('Buspirate failed to enter binary mode after 20 attempts')
            print('Buspirate entering binary mode attempt {}: '.format(tries), end=' ')
            self.ser.write('\x00') #enter binary mode
            time.sleep(0.05)
            resp = self.ser.read(self.ser.inWaiting())
            print(resp)
        #get into i2c mode
        self.ser.write('\x01') #enter binary SPI mode
        time.sleep(0.05)
        resp = self.ser.read(self.ser.inWaiting())
        if resp != 'SPI1':
             raise SPIMasterError('Buspirate failed to enter SPI mode: {}'.format(resp))
        #set voltage levels
        #self.ser.write('\x4C') #power and pullups on
        self.ser.write('\x4D') #power and pullups on
        resp = self.ser.read(1)
        if resp != '\x01':
             raise SPIMasterError('Buspirate failed to enable supply and pullups: {}'.format(resp))
        #vpullup select not yet implemented 7/16/2013.  3.3V shorted to Vpu on board temporarily
        #self.ser.write('\x51') #3.3v pullup
        #resp = self.ser.read(1)
        #if resp != '\x01':
        #     raise SPIMasterError('Buspirate failed to set pullup voltage to 3.3v: {}'.format(resp))
    def set_baudrate(self, baudrate):
        baudrate = float(baudrate)
        self.baudrate = baudrate
        if baudrate == 30e3:
            self.ser.write('\x60')
        elif baudrate == 125e3:
            self.ser.write('\x61')
        elif baudrate == 250e3:
            self.ser.write('\x62')
        elif baudrate == 1e6:
            self.ser.write('\x63')
        elif baudrate == 2e6:
            self.ser.write('\x64')
        elif baudrate == 2.6e6:
            self.ser.write('\x65')
        elif baudrate == 4e6:
            self.ser.write('\x66')
        elif baudrate == 8e6:
            self.ser.write('\x67')
        resp = self.ser.read(1) #does it really return a byte? Undocumented...
        if resp != '\x01':
             raise SPIMasterError('Buspirate failed to set SPI baudrate to {}: {}'.format(baudrate,resp))
    def set_mode(self):
        #looks like CKE is reversed from CPHA standard....
        #bit 8 CKE: SPIx Clock Edge Select bit(1)
            #1 = Serial output data changes on transition from active clock state to Idle clock state (see bit 6)
            #0 = Serial output data changes on transition from Idle clock state to active clock state (see bit 6)
        if self.mode == 0:
            self.ser.write('\x8A')
        elif self.mode == 1:
            self.ser.write('\x89')
        elif self.mode == 2:
            self.ser.write('\x8E')
        elif self.mode == 3:
            self.ser.write('\x8C')
        else:
            raise SPIMasterError('Something went wrong setting Mode')
        resp = self.ser.read(1) #does it really return a byte? Undocumented...
        if resp != '\x01':
             raise SPIMasterError('Buspirate failed to set SPI mode to {}: {}'.format(self.mode,resp))
    def cs(self, select):
        '''select is active low'''
        if select:
            self.ser.write('\x02')
        else:
            self.ser.write('\x03')
        resp = self.ser.read(1)
        if resp != '\x01':
             raise SPIMasterError('Buspirate failed to set SPI _SS: {}'.format(ord(resp)))
    def __del__(self):
        self.ser.close()
    def _shift_data(self, data_out, clk_count):
        resp = []
        bytes = self.unpack(data_out, clk_count, self.word_size)
        while len(bytes) > 16:
            self.ser.write('\x1F') #bulk write and read 16 bytes
            resp_chr = self.ser.read(1) 
            if resp_chr != '\x01':
                raise SPIMasterError('Buspirate failed response to SPI bulk read/write: {}'.format(ord(resp_chr)))
            for byte in bytes[0:16]:
                self.ser.write(chr(byte)) #send MOSI byte
                resp.append(ord(self.ser.read(1))) #get MISO byte back
            bytes = bytes[16:]
        remaining_bytes = len(bytes)
        self.ser.write(chr(0x10 + remaining_bytes - 1)) #bulk write and read remaining bytes
        resp_chr = self.ser.read(1) 
        if resp_chr != '\x01':
            raise SPIMasterError('Buspirate failed response to SPI bulk read/write: {}'.format(ord(resp_chr)))
        for byte in bytes:
            self.ser.write(chr(byte)) #send MOSI byte
            resp.append(ord(self.ser.read(1))) #get MISO byte back
        return self.pack(resp, self.word_size)
        
class spi_bitbang(spiInterface):
    def __init__(self, SCK_channel, MOSI_channel=None, MISO_channel=None, SS_channel=None, CPOL=0, CPHA=0, SS_POL=0, low_level=0, high_level=1):
        '''bit-bangable SPI port made of any writeable channels (power supply, gpio, etc).
        SCK_channel, MOSI_channel and SS_channel are writable channel objects.
        MISO_channel is a readable channel object.
        MOSI_channel or MISO_channel may be set equal to None for unidirectinal communication.
        SS_channel may be set equal to None if not required.
        CPOL, CPHA set SPI clock polarity and clock phase respectively. CPHA != 0 not currently supported.
        SS_POL is the active state of slave/chip select (ie 0 for typical active low).
        low_level and high_level will be written to the writable channels to set the logic low and logic high states respectively. The average will set the ADC threshold for the MISO channel.
        If a channel is not required, it can be faked with lab_core.master.add_channel_dummy('fake_MISO_channel').
        '''
        self.SCK_channel = SCK_channel
        self.MOSI_channel = MOSI_channel
        self.MISO_channel = MISO_channel
        self.SS_channel = SS_channel
        self.SS_POL = SS_POL
        self.set_levels(low_level, high_level)
        spiInterface.__init__(self, CPOL, CPHA, ss_ctrl=self.cs, word_size=1)
        if not self.CPOL:
            #clock resting state 0
            self.SCK_channel.write(self.low)
        else:
            #clock resting state 1
            self.SCK_channel.write(self.high)
        assert CPHA == 0 #CHPA == 1 not implemented. https://en.wikipedia.org/wiki/Serial_Peripheral_Interface_Bus#Clock_polarity_and_phase
    def set_levels(self, low=0, high=1):
        '''set values to write to SCK_channel, MOSI_channel and SS_channel.
        values are also used to digitize MISO_channel readings.
        for example, to use a power supply at 5V logic levels set high=5'''
        self.low = low
        self.high = high
    def cs(self, select):
        '''select is active low'''
        if self.SS_channel is not None:
            if select and not self.SS_POL:
                self.SS_channel.write(self.low)
            elif not select and not self.SS_POL:
                self.SS_channel.write(self.high)
            elif select and self.SS_POL: #active high SS
                self.SS_channel.write(self.high)
            elif not select and self.SS_POL: #active high SS
                self.SS_channel.write(self.low)
    def _shift_data(self, data_out, clk_count):
        resp = []
        bits = self.unpack(data_out, clk_count, self.word_size)
        for bit in bits:
            #set up data
            if self.MOSI_channel is not None:
                self.MOSI_channel.write(self.high if bit else self.low)
            #clk active
            self.SCK_channel.write(self.high if not self.CPOL else self.low)
            #receive data
            if self.MISO_channel is not None:
                raw_data = self.MISO_channel.read()
                if raw_data > (self.high + self.low)/2.0: #ADC
                    resp.append(1)
                else:
                    resp.append(0)
            #clk inactive
            self.SCK_channel.write(self.low if not self.CPOL else self.high)
        if self.MISO_channel is not None:
            return self.pack(resp, self.word_size)

class spi_dummy(spiInterface):
    def __init__(self, delay=0, word_size=1):
        self.delay = delay
        spiInterface.__init__(self, CPOL=0, CPHA=0, ss_ctrl=self.cs, word_size=word_size)
    def cs(self, select):
        if select:
            print("Writing slave_select ACTIVE.")
        else:
            print("Writing slave_select INACTIVE.")
    def _shift_data(self, data_out, clk_count):
        resp = []
        words = self.unpack(data_out, clk_count, self.word_size)
        for word in words:
            resp.append(random.randint(0,2**self.word_size-1))
        ret_val = self.pack(resp, self.word_size)
        print("{{}} bit dummy SPI transaction. Wrote: 0x{{:0{digits}X}} Read:0x{{:0{digits}X}}".format(digits=(clk_count-1)//4+1).format(clk_count, data_out, ret_val))
        time.sleep(self.delay)
        return ret_val

class SPIMasterError(Exception):
    pass

if __name__ == "__main__":
    from . import lab_core
    m = lab_core.master()
    def dummy_print(ch_name, data):
        print('{}:{}'.format(ch_name, data))
    clk_ch = m.add_channel_virtual('sck', write_function = lambda data: dummy_print('sck',data))
    mosi_ch = m.add_channel_virtual('mosi', write_function = lambda data: dummy_print('mosi',data))
    ss_ch = m.add_channel_virtual('_ss', write_function = lambda data: dummy_print('/ss',data))
    miso_ch = m.add_channel_virtual('miso', read_function = lambda: dummy_print('miso','Read'))
    sr = shift_register()
    sr.add_bit_field(bit_field_name='top_nibble', bit_field_bit_count=4)
    sr.add_bit_field(bit_field_name='bottom_half_nibble', bit_field_bit_count=2)
    sr.add_bit_field(bit_field_name='bit_1', bit_field_bit_count=1)
    sr.add_bit_field(bit_field_name='bit_0', bit_field_bit_count=1)
    print(sr)
    for bf in sr:
        print('{}:{}'.format(bf,sr[bf]))
    #sp = spi_bitbang(SCK_channel=clk_ch, MOSI_channel=mosi_ch, MISO_channel=miso_ch, SS_channel=ss_ch)
    sp = spi_dummy()
    sp.transceive(0x05a,9)
    data = {}
    data['top_nibble'] = 0xA
    data['bottom_half_nibble'] = 1
    data['bit_1'] = 0
    data['bit_0'] = 1
    print(sr.unpack(sp.transceive(*sr.pack(data))))
