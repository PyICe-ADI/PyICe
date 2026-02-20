'''
SMBus Interface Hardware Drivers
================================
'''
import time, random, abc, itertools
from PyICe import visa_wrappers
try:
    import serial
except ImportError:
    pass
import logging
debug_logging = logging.getLogger(__name__)
'''Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])'''
STR_ENCODING = 'latin-1'
class twi_interface(object, metaclass=abc.ABCMeta):
    '''this is the master i2c class, all other i2c adapters inherit from this

    All SMBus Protocols are implemented generically with I2C Primitives
    Board specific subclasses should overload as necessary for increased performance
    addr7 is the 7-bit chip address  The 8-bit read/write addresses are computed locally

    The twi_instrument will preferentially call read_register_list, then read_register. The named protocols can be used internally by the various hardware devices, but should generally not be called by other PyICe libraries. twi_instrument writes will call write_register.
    '''
    def close(self):
        '''close the underlying (serial) interface'''
        pass
    '''I2C Generic Protocol Methods - Must be implemented in hardware/firmware specific classes'''
    @abc.abstractmethod
    def start(self):
        '''I2C Start  - Falling SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    def restart(self):
        '''I2C Re-Start  - Falling SDA with SCL high between start and stop condition.
        Implement only if restart requires a different action than a normal start in underlying hardware.
        Returns True or False to indicate successful arbitration'''
        return self.start()
    @abc.abstractmethod
    def stop(self):
        '''I2C Stop  - Rising SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    @abc.abstractmethod
    def write(self,data8):
        '''Transmit 8 bits plus 9th acknowledge clock.  Returns True or False to indicate slave acknowledge'''
        raise i2cUnimplementedError()
    @abc.abstractmethod
    def read_ack(self):
        '''Read 8 bits from slave transmitter  and assert SDA during 9th acknowledge clock.  Returns 8 bit data'''
        raise i2cUnimplementedError()
    @abc.abstractmethod
    def read_nack(self):
        '''Read 8 bits from slave transmitter  and release SDA during 9th acknowledge clock to request end of transmission.  Returns 8 bit data'''
        raise i2cUnimplementedError()
    def resync_communication(self):
        '''attempt to correct problems caused by dropped/duplicate characters in serial buffer, etc.
            Don't do anything here.  Method must be overloaded to implement hardware-specific recovery procedure.
        '''
        pass
    def set_frequency(self, frequency):
        raise i2cUnimplementedError()

    ###Utilities###
    def scan(self):
        '''Find all devices on bus by checking acknowledge of each address in turn.'''
        responses = []
        for addr in range(0,255,2):
            self.start()
            if self.write(addr):
                responses.append(addr)
        return responses
    @classmethod
    def check_size(cls, data, bits):
        '''make sure data fits within word of length  "bits"'''
        assert data >= 0
        assert data < 2**bits
        return True
    @classmethod
    def read_addr(cls,addr7):
        '''compute 8-bit read address from 7-bit address'''
        cls.check_size(addr7, 7)
        return ((addr7 << 1) + 1)
    @classmethod
    def write_addr(cls, addr7):
        '''compute 8-bit write address from 7-bit address'''
        cls.check_size(addr7, 7)
        return (addr7 << 1)
    @classmethod
    def pec(cls,byteList):
        '''
        http://smbus.org/specs/smbus20.pdf
        Each bus transaction requires a Packet Error Code (PEC) calculation by both the transmitter and receiver
        within each packet. The PEC uses an 8-bit cyclic redundancy check (CRC-8) of each read or write bus
        transaction to calculate a Packet Error Code (PEC). The PEC may be calculated in any way that conforms
        to a CRC-8 represented by the polynomial, C(x) = x8 + x2 + x1 + 1 and must be calculated in the order of
        the bits as received.
        Calculating the PEC for transmission or reception is implemented in a method chosen by the device
        manufacturer. It is possible to perform the check with low-cost hardware or firmware algorithm that could
        process the message bit-by-bit or with a byte-wise look-up table. The SMBus web page provides some
        example CRC-8 methods.
        The PEC is appended to the message as dictated by the protocols in section 5.5. The PEC calculation
        includes all bytes in the transmission, including address, command and data. The PEC calculation does not
        include ACK, NACK, START, STOP nor Repeated START bits. This means that the PEC is computed
        over the entire message from the first START condition.
        Whether a device implements packet error checking may be determined by the specification revision code
        that is present in the SpecificationInfo() command for a Smart Battery, Smart Battery Charger or Smart
        Battery Selector. See these individual specifications for exact revision coding identities. It may also be
        discovered in the UDID, defined in section 5.6.1, for other devices.

        Here is an arbitrary length solution rather than bytewise solution
        "  x^8 + x^2 + x^1 + 1"
        "            876543210"
        "            X     XXX"
        CRC_POLY = 0b100000111
        crc_length = 9 # len(bin(CRC_POLY)[2:])
        def pec_smbus(value):
            value <<= crc_length
            while (value >> crc_length) != 0:
                value ^= CRC_POLY << (len(bin(value)[2:]) - crc_length)
            return value >> 1
        '''
        #byteList is an ordered list of every byte in the transaction including address, command code (subaddr) and data
        #http://en.wikipedia.org/wiki/Cyclic_redundancy_check
        #http://en.wikipedia.org/wiki/Computation_of_CRC
        #https://en.wikipedia.org/wiki/Mathematics_of_cyclic_redundancy_checks
        #http://www.repairfaq.org/filipg/LINK/F_crc_v3.html
        #http://ghsi.de/CRC/
        #http://smbus.org/faq/crc8Applet.htm
        #http://www.hackersdelight.org/crc.pdf
        
        crc = 0
        poly = 0x07 #x^8 + x^2 + x^1 + 1, discard x^8 term
        for byte in byteList:
            #big endian -> msb goes in first
            crc ^= byte
            for cycle in range(8):
                crc <<= 1
                if (crc & 0x100): #msb was set before left shift ( & 0x80)
                    #xor with crc if pre-shift msb was 1
                    crc ^= poly
        return int(crc & 0xFF)
    @classmethod
    def get_byte(cls, data, bytenum):
            '''Select specified byte from data of any size.  bytenum=0 returns the least-significant byte.'''
            return (data >> (bytenum*8)) & 0xFF
    @classmethod
    def word(cls, byteList):
        '''Return a word of arbitrary size assembled from bytes.
            Must provide byteList assembled with least-significant byte first (little-endian), like SMBus'''
        assert isinstance(byteList, (list, tuple))
        word_value = 0
        for i,byte in enumerate(byteList):
            cls.check_size(byte, 8)
            word_value += byte << (8*i)
        return word_value
    def read_register(self, addr7, commandCode, data_size, use_pec):
        '''read data (8,16,32, or 64b) with optional additional PEC byte read from slave.'''
        self.print_warning(operation=f"read_register Data Size={data_size}, PEC={use_pec}")
        debug_logging.debug("Performing deprecated twi_interface.read_register for commandCode=%s, data_size=%s, use_pec=%s",commandCode,data_size,use_pec)
        if data_size in (8, 16, 32, 64):
            self.check_size(commandCode, 8)
        elif data_size in (-1, 0):
            # -1 for quick_command (unimplemented)
            # 0 for receive_byte
            assert commandCode is None
        else:
            raise Exception('Unimplemented data size: {}. Not within set (-1, 0, 8, 16, 32, 64)'.format(data_size))
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        
        try:
            if data_size in (8, 16, 32, 64):
                byteList.append(self.write_addr(addr7))
                if not self.write(self.write_addr(addr7)):
                    raise i2cWriteAddressAcknowledgeError()
                byteList.append(commandCode)
                if not self.write(commandCode):
                    raise i2cCommandCodeAcknowledgeError()
                if not self.restart():
                    raise i2cStartStopError()
                byteList.append(self.read_addr(addr7))
                if not self.write(self.read_addr(addr7)):
                    raise i2cReadAddressAcknowledgeError()
                dataByteList = []
                for i in range(data_size // 8):
                    if (i < ((data_size // 8)-1)) or use_pec:
                        dataByteList.append(self.read_ack())
                    else:
                        dataByteList.append(self.read_nack())
                byteList += dataByteList
            elif data_size == 0:
                byteList.append(self.read_addr(addr7))
                if not self.write(self.read_addr(addr7)):
                    raise i2cReadAddressAcknowledgeError()
                if use_pec:
                    dataByteList = [self.read_ack()]
                else:
                    dataByteList = [self.read_nack()]
                byteList += dataByteList
            elif data_size == -1:
                if not self.write(self.read_addr(addr7)):
                    raise i2cReadAddressAcknowledgeError()
        except i2cAcknowledgeError as e:
            self.stop()
            raise e
        if use_pec:
            pec = self.read_nack()
            if not self.stop():
                raise i2cStartStopError()
            if pec != self.pec(byteList):
                raise i2cPECError('PEC Failure: expected 0x{:X} but got 0x{:X}'.format(self.pec(byteList), pec))
        else:
            if not self.stop():
                raise i2cStartStopError()
        return self.word(dataByteList)
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        self.print_warning(operation=f"write_register Data Size={data_size}, PEC={use_pec}")
        '''write_word with optional additional PEC byte written to slave.'''
        if data_size in (8, 16, 32, 64):
            self.check_size(commandCode, 8)
            self.check_size(data, data_size)
        elif data_size == 0:
            # send_byte
            self.check_size(commandCode, 8)
            assert data is None
        elif data_size == -1:
            # quick_command
            assert commandCode is None
            assert data is None
            # use_pec meaningless
        else:
            raise Exception('Unimplemented data size: {}. Not within set (-1, 0, 8, 16, 32, 64)'.format(data_size))
        dataByteList = []
        for i in range(data_size // 8):
            dataByteList.append(self.get_byte(data,i))
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        try:
            byteList.append(self.write_addr(addr7))
            if not self.write(self.write_addr(addr7)):
                raise i2cWriteAddressAcknowledgeError()
            if data_size > -1:
                byteList.append(commandCode)
                if not self.write(commandCode):
                    raise i2cCommandCodeAcknowledgeError()
            for dataByte in dataByteList:
                if not self.write(dataByte):
                    raise i2cDataAcknowledgeError()
            byteList += dataByteList
            if use_pec:
                if not self.write(self.pec(byteList)):
                    raise i2cDataPECAcknowledgeError()
        finally:
            if not self.stop():
                raise i2cStartStopError()

    '''SMBus Protocols implemented with I2C Primitives
    Board specific subclasses should overload as necessary for increased performance
    addr7 is the 7-bit chip address  The 8-bit read/write addresses are computed locally'''
    def quick_command_rd(self,addr7):
        '''Here, part of the slave address denotes the command – the R/W# bit. The R/W# bit may be used to simply
            turn a device function on or off, or enable/disable a low-power standby mode. There is no data sent or
            received.
            The quick command implementation is good for very small devices that have limited support for the
            SMBus specification. It also limits data on the bus for simple devices.'''
        self.print_warning(operation="quick_command_rd")
        if not self.start():
            raise i2cStartStopError('I2C Error: Failed to Assert Start Signal during quick_command_rd')
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError('I2C Error: Slave read address failed to acknowledge during quick_command_rd')
        if not self.stop():
            raise i2cStartStopError('I2C Error: Failed to Assert Stop Signal during quick_command_rd')
    def quick_command_wr(self,addr7):
        '''Here, part of the slave address denotes the command – the R/W# bit. The R/W# bit may be used to simply
            turn a device function on or off, or enable/disable a low-power standby mode. There is no data sent or
            received.
            The quick command implementation is good for very small devices that have limited support for the
            SMBus specification. It also limits data on the bus for simple devices.'''
        # self.print_warning(operation="quick_command_wr")
        if not self.start():
            raise i2cStartStopError('I2C Error: Failed to Assert Start Signal during quick_command_wr')
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError('I2C Error: Slave write address failed to acknowledge during quick_command_wr')
        if not self.stop():
            raise i2cStartStopError('I2C Error: Failed to Assert Stop Signal during quick_command_wr')
    def send_byte(self,addr7,data8):
        '''A simple device may recognize its own slave address and accept up to 256 possible encoded commands in
            the form of a byte that follows the slave address.
            All or parts of the Send Byte may contribute to the command. For example, the highest 7 bits of the
            command code might specify an access to a feature, while the least significant bit would tell the device to
            turn the feature on or off. Or, a device may set the “volume” of its output based on the value it received
            from the Send Byte protocol.'''
        self.write_register(addr7, commandCode=data8, data=None, data_size=0, use_pec=False)
    def send_byte_pec(self,addr7,data8):
        '''send_byte with additional PEC byte written to slave.'''
        self.write_register(addr7, commandCode=data8, data=None, data_size=0, use_pec=True)
    def receive_byte(self, addr7):
        '''The Receive Byte is similar to a Send Byte, the only difference being the direction of data transfer. A
            simple device may have information that the host needs. It can do so with the Receive Byte protocol. The
            same device may accept both Send Byte and Receive Byte protocols. A NACK (a ‘1’ in the ACK bit
            position) signifies the end of a read transfer.'''
        return self.read_register(self, addr7, commandCode=None, data_size=0, use_pec=False)
    def receive_byte_pec(self, addr7):
        '''receive_byte with additional PEC byte read from slave.'''
        return self.read_register(self, addr7, commandCode=None, data_size=0, use_pec=True)
    def alert_response(self):
        '''Another optional signal is an interrupt line for devices that want to trade their ability to master for a pin.
        SMBALERT# is a wired-AND signal just as the SMBCLK and SMBDAT signals are. SMBALERT# is
        used in conjunction with the SMBus General Call Address. Messages invoked with the SMBus are 2 bytes
        long.
        A slave-only device can signal the host through SMBALERT# that it wants to talk. The host processes the
        interrupt and simultaneously accesses all SMBALERT# devices through the Alert Response Address
        (ARA). Only the device(s) which pulled SMBALERT# low will acknowledge the Alert Response Address.
        The host performs a modified Receive Byte operation. The 7 bit device address provided by the slave
        transmit device is placed in the 7 most significant bits of the byte. The eighth bit can be a zero or one.

        Returns 7 bit address of responding device.
        Returns None if no response to ARA.'''
        self.print_warning(operation="alert_response")
        if not self.start():
            raise i2cStartStopError()
        if not self.write(self.read_addr(0xC)):
            self.stop()
            return None #no response to Alert Response Address
        data8 = self.read_nack()
        if not self.stop():
            raise i2cStartStopError()
        return data8 >> 1
    def alert_response_pec(self):
        '''Alert Response Query to SMBALERT# interrupt with Packet Error Check.
            Returns 7 bit address of responding device.
            Returns None if no response to ARA.'''
        self.print_warning(operation="alert_response_pec")
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        byteList.append(self.read_addr(0xC))
        if not self.write(self.read_addr(0xC)):
            self.stop()
            return None #no response to Alert Response Address
        data8 = self.read_ack()
        byteList.append(data8)
        pec = self.read_nack()
        byteList.append(pec)
        if not self.stop():
            raise i2cStartStopError()
        if self.pec(byteList):
            raise i2cPECError("I2C Error: Failed PEC check")
        return data8 >> 1
    def write_byte(self, addr7, commandCode, data8):
        '''The first byte of a Write Byte access is the command code. The next byte
            is the data to be written. In this example the master asserts the slave device address followed by the write
            bit. The device acknowledges and the master delivers the command code. The slave again acknowledges
            before the master sends the data byte. The slave acknowledges each byte, and the
            entire transaction is finished with a STOP condition.'''
        self.write_register(addr7, commandCode, data8, data_size=8, use_pec=False)
    def write_byte_pec(self, addr7, commandCode, data8):
        '''write_byte with additional PEC byte written to slave.'''
        self.write_register(addr7, commandCode, data8, data_size=8, use_pec=True)
    def write_word(self, addr7, commandCode, data16):
        '''The first byte of a Write Word access is the command code. The next two bytes
            are the data to be written. In this example the master asserts the slave device address followed by the write
            bit. The device acknowledges and the master delivers the command code. The slave again acknowledges
            before the master sends the data word (low byte first). The slave acknowledges each byte, and the
            entire transaction is finished with a STOP condition.'''
        self.write_register(addr7, commandCode, data16, data_size=16, use_pec=False)
    def write_word_pec(self, addr7, commandCode, data16):
        '''write_word with additional PEC byte written to slave.'''
        self.write_register(addr7, commandCode, data16, data_size=16, use_pec=True)
    def read_byte(self,addr7,commandCode):
        '''Reading data is slightly more complicated than writing data. First the host must write a command to the
            slave device. Then it must follow that command with a repeated START condition to denote a read from
            that device’s address. The slave then returns one byte of data.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        return self.read_register(addr7, commandCode, data_size=8, use_pec=False)
    def read_byte_pec(self,addr7,commandCode):
        '''read_byte with additional PEC byte read from slave.'''
        return self.read_register(addr7, commandCode, data_size=8, use_pec=True)
    def read_word(self,addr7,commandCode):
        '''Reading data is slightly more complicated than writing data. First the host must write a command to the
            slave device. Then it must follow that command with a repeated START condition to denote a read from
            that device’s address. The slave then returns two bytes of data.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        return self.read_register(addr7, commandCode, data_size=16, use_pec=False)
    def read_word_pec(self,addr7,commandCode):
        '''read_word with additional PEC byte read from slave.'''
        return self.read_register(addr7, commandCode, data_size=16, use_pec=True)
    def process_call(self, addr7, commandCode, data16):
        '''The process call is so named because a command sends data and waits for the slave to return a value
            dependent on that data. The protocol is simply a Write Word followed by a Read Word without the Read-
            Word command field and the Write-Word STOP bit.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        self.print_warning(operation="process_call")
        self.check_size(commandCode, 8)
        dataLow = self.get_byte(data16,0)
        dataHigh = self.get_byte(data16,1)
        if not self.start():
            raise i2cStartStopError()
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        if not self.write(dataLow):
            raise i2cDataLowAcknowledgeError()
        if not self.write(dataHigh):
            raise i2cDataHighAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        dataLow = self.read_ack()
        dataHigh = self.read_nack()
        if not self.stop():
            raise i2cStartStopError()
        return self.word([dataLow, dataHigh])
    def process_call_pec(self, addr7, commandCode, data16):
        '''process_call with additional PEC byte read from slave.'''
        self.print_warning(operation="process_call_pec")
        self.check_size(commandCode, 8)
        dataLow = self.get_byte(data16,0)
        dataHigh = self.get_byte(data16,1)
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        byteList.append(self.write_addr(addr7))
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        byteList.append(commandCode)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        byteList.append(dataLow)
        if not self.write(dataLow):
            raise i2cDataLowAcknowledgeError()
        byteList.append(dataHigh)
        if not self.write(dataHigh):
            raise i2cDataHighAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        byteList.append(self.read_addr(addr7))
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        dataLow = self.read_ack()
        byteList.append(dataLow)
        dataHigh = self.read_ack()
        byteList.append(dataHigh)
        pec = self.read_nack()
        if not self.stop():
            raise i2cStartStopError()
        if pec != self.pec(byteList):
            raise i2cPECError('PEC Failure: expected 0x{:X} but got 0x{:X}'.format(self.pec(byteList), pec))
        return self.word([dataLow, dataHigh])
    def block_write(self,addr7,commandCode,dataByteList):
        '''The Block Write begins with a slave address and a write condition. After the command code the host
            issues a byte count which describes how many more bytes will follow in the message. If a slave has 20
            bytes to send, the byte count field will have the value 20 (14h), followed by the 20 bytes of data. The byte
            count does not include the PEC byte. The byte count may not be 0. A Block Read or Write is allowed to
            transfer a maximum of 32 data bytes.'''
        self.print_warning(operation="block_write")
        if not self.start():
            raise i2cStartStopError()
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        byteCount = len(dataByteList)
        if byteCount > 32:
            raise i2cError("I2C Error: Block Write requires maximum 32 data bytes")
        if not self.write(byteCount):
            raise i2cDataAcknowledgeError()
        for byte in dataByteList:
            self.check_size(byte, 8)
            if not self.write(byte):
                raise i2cDataAcknowledgeError()
        if not self.stop():
            raise i2cStartStopError()
    def block_write_pec(self,addr7,commandCode,dataByteList):
        '''block_write with additional PEC byte written to slave.'''
        self.print_warning(operation="block_write_pec")
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        byteList.append(self.write_addr(addr7))
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        byteList.append(commandCode)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        byteCount = len(dataByteList)
        if byteCount > 32:
            raise i2cError("I2C Error: Block Write requires maximum 32 data bytes")
        byteList.append(byteCount)
        if not self.write(byteCount):
            raise i2cDataAcknowledgeError()
        for byte in dataByteList:
            self.check_size(byte, 8)
            byteList.append(byte)
            if not self.write(byte):
                raise i2cDataAcknowledgeError()
        if not self.write(self.pec(byteList)):
            raise i2cDataPECAcknowledgeError()
        if not self.stop():
            raise i2cStartStopError()
    def block_read(self,addr7,commandCode):
        '''A Block Read differs from a block write in that the repeated START condition exists to satisfy the
            requirement for a change in the transfer direction. A NACK immediately preceding the STOP condition
            signifies the end of the read transfer.'''
        self.print_warning(operation="block_read")
        if not self.start():
            raise i2cStartStopError()
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        byteCount = self.read_ack()
        if byteCount > 32:
            raise i2cError("I2C Error: Block Write requires maximum 32 data bytes")
        dataByteList = []
        for i in range(0,byteCount-1):
            byte = self.read_ack()
            dataByteList.append(byte)
        byte = self.read_nack()
        dataByteList.append(byte)
        if not self.stop():
            raise i2cStartStopError()
        return dataByteList
    def block_read_pec(self,addr7,commandCode):
        '''block_read with additional PEC byte read from slave.'''
        self.print_warning(operation="block_read_pec")
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        byteList.append(self.write_addr(addr7))
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        byteList.append(commandCode)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        byteList.append(self.read_addr(addr7))
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        byteCount = self.read_ack()
        byteList.append(byteCount)
        if byteCount > 32:
            raise i2cError("I2C Error: Block Write requires maximum 32 data bytes")
        dataByteList = []
        for i in range(0,byteCount):
            byte = self.read_ack()
            byteList.append(byte)
            dataByteList.append(byte)
        pec = self.read_nack()
        if not self.stop():
            raise i2cStartStopError()
        if pec != self.pec(byteList):
            raise i2cPECError('PEC Failure: expected 0x{:X} but got 0x{:X}'.format(self.pec(byteList), pec))
        return dataByteList
    def block_process_call(self,addr7,commandCode,dataByteListWrite):
        '''The block write-block read process call is a two-part message. The call begins with a slave address and a
            write condition. After the command code the host issues a write byte count (M) that describes how many
            more bytes will be written in the first part of the message. If a master has 6 bytes to send, the byte count
            field will have the value 6 (0000 0110b), followed by the 6 bytes of data. The write byte count (M) cannot
            be zero.
            The second part of the message is a block of read data beginning with a repeated start condition followed
            by the slave address and a Read bit. The next byte is the read byte count (N), which may differ from the
            write byte count (M). The read byte count (N) cannot be zero.
            The combined data payload must not exceed 32 bytes. The byte length restrictions of this process call are
            summarized as follows:
            • M ≥ 1 byte
            • N ≥ 1 byte
            • M + N ≤ 32 bytes
            The read byte count does not include the PEC byte. The PEC is computed on the total message beginning
            with the first slave address and using the normal PEC computational rules. It is highly recommended that a
            PEC byte be used with the Block Write-Block Read Process Call.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        self.print_warning(operation="block_process_call")
        if not self.start():
            raise i2cStartStopError()
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        byteCountWrite = len(dataByteListWrite)
        if byteCountWrite > 31 or byteCountWrite < 1: #slave must return at least 1 byte and total limitation is 32
            raise i2cError("I2C Error: Block Process Call requires maximum 32 data bytes")
        if not self.write(byteCountWrite):
            raise i2cDataAcknowledgeError()
        for byte in dataByteListWrite:
            self.check_size(byte, 8)
            if not self.write(byte):
                raise i2cDataAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        byteCountRead = self.read_ack()
        if byteCountRead < 1 or (byteCountWrite+byteCountRead) > 32:
            raise i2cError("I2C Error: Block Process Call requires maximum 32 data bytes")
        dataByteListRead = []
        for i in range(0,byteCountRead-1):
            dataByteListRead.append(self.read_ack())
        dataByteListRead.append(self.read_nack())
        if not self.stop():
            raise i2cStartStopError()
        return dataByteListRead
    def block_process_call_pec(self,addr7,commandCode,dataByteListWrite):
        '''block write-block read process call with additional PEC byte read from slave.'''
        self.print_warning(operation="block_process_call_pec")
        byteList = []
        if not self.start():
            raise i2cStartStopError()
        byteList.append(self.write_addr(addr7))
        if not self.write(self.write_addr(addr7)):
            raise i2cWriteAddressAcknowledgeError()
        self.check_size(commandCode, 8)
        byteList.append(commandCode)
        if not self.write(commandCode):
            raise i2cCommandCodeAcknowledgeError()
        byteCountWrite = len(dataByteListWrite)
        if byteCountWrite > 31 or byteCountWrite < 1: #slave must return at least 1 byte and total limitation is 32
            raise i2cError("I2C Error: Block Process Call requires maximum 32 data bytes")
        byteList.append(byteCountWrite)
        if not self.write(byteCountWrite):
            raise i2cDataAcknowledgeError()
        for byte in dataByteListWrite:
            self.check_size(byte, 8)
            byteList.append(byte)
            if not self.write(byte):
                raise i2cDataAcknowledgeError()
        if not self.restart():
            raise i2cStartStopError()
        byteList.append(self.read_addr(addr7))
        if not self.write(self.read_addr(addr7)):
            raise i2cReadAddressAcknowledgeError()
        byteCountRead = self.read_ack()
        byteList.append(byteCountRead)
        if byteCountRead < 1 or (byteCountWrite+byteCountRead) > 32:
            raise i2cError("I2C Error: Block Process Call requires maximum 32 data bytes")
        dataByteListRead = []
        for i in range(0,byteCountRead):
            byte = self.read_ack()
            byteList.append(byte)
            dataByteListRead.append(byte)
        pec = self.read_nack()
        if not self.stop():
            raise i2cStartStopError()
        if pec != self.pec(byteList):
            raise i2cPECError('PEC Failure: expected 0x{:X} but got 0x{:X}'.format(self.pec(byteList), pec))
        return dataByteListRead

    ###List reading aggregation commands###
    def _read_x_list(self, addr7, cc_list, rd_function):
        '''Return dictionary of read results.
        Reads each commandCode of cc_list in turn at chip address addr7 using rd_function protocol.
        '''
        self.print_warning(operation="_read_x_list")
        cc_data = {}
        for cc in cc_list:
            cc_data[cc] = rd_function(addr7, cc)
        return cc_data
    def read_byte_list(self, addr7, cc_list):
        '''Return dictionary of read_byte results.
        Reads each commandCode of cc_list in turn at chip address addr7
        Overload this method to improve communication speed when the instrument supports it.
        '''
        self.print_warning(operation="read_byte_list")
        return self._read_x_list(addr7, cc_list, self.read_byte)
    def read_byte_list_pec(self, addr7, cc_list):
        '''Return dictionary of read_byte_pec results.
        Reads each commandCode of cc_list in turn at chip address addr7
        Overload this method to improve communication speed when the instrument supports it.
        '''
        self.print_warning(operation="read_byte_list_pec")
        return self._read_x_list(addr7, cc_list, self.read_byte_pec)
    def read_word_list(self, addr7, cc_list):
        '''Return dictionary of read_word results.
        Reads each commandCode of cc_list in turn at chip address addr7
        Overload this method to improve communication speed when the instrument supports it.
        '''
        self.print_warning(operation="read_word_list")
        return self._read_x_list(addr7, cc_list, self.read_word)
    def read_word_list_pec(self, addr7, cc_list):
        '''Return dictionary of read_word_pec results.
        Reads each commandCode of cc_list in turn at chip address addr7
        Overload this method to improve communication speed when the instrument supports it.
        '''
        self.print_warning(operation="read_word_list_pec")
        return self._read_x_list(addr7, cc_list, self.read_word_pec)
    def read_register_list(self, addr7, cc_list, data_size, use_pec):
        return self._read_x_list(addr7, cc_list, lambda addr7, cc: self.read_register(addr7, cc, data_size, use_pec))
    def print_warning(self, operation):
        debug_logging.debug("WARNING: Using deprecated/potentially slow SMBus access method '%s.twi_interface.%s' Switch to hardware-accelerated/protocol-specific methods for best performance, if available.", __name__, operation)
        if not hasattr(self, "{}_warning_printed".format(operation)):
            setattr(self, "{}_warning_printed".format(operation), True)
            print(("WARNING: Using deprecated/potentially slow SMBus access method '{module}.twi_interface.{op}'.\n"
                   "         Switch to hardware-accelerated/protocol-specific methods for best performance,\n"
                   "         if available.").format(op=operation, module=__name__))
class i2c_dummy(twi_interface):
    '''dummy interface for testing without any hardware.  No actual communication occurs.'''
    def __init__(self,delay=0,p_change=0.005,verbose=False):
        self._delay = delay
        self._cc_size = 8
        self._p_change = p_change
        self._verbose = verbose
        self._cc_data = {}
    def start(self):
        '''don't do anything.  Return value indicates that transaction was successful.'''
        time.sleep(self._delay)
        if self._verbose:
            print("i2c_dummy Start")
        return True
    def stop(self):
        '''don't do anything.  Return value indicates that transaction was successful.'''
        time.sleep(self._delay)
        if self._verbose:
            print("i2c_dummy Stop")
        return True
    def write(self,data8):
        '''don't do anything.  Return value indicates that transaction was successful.'''
        time.sleep(self._delay)
        if self._verbose:
            print("i2c_dummy write 0x{:02X}".format(data8))
        return True
    def read_ack(self):
        '''don't do anything.  Return random 8-bit value'''
        time.sleep(self._delay)
        rd = random.randint(0, 255)
        if self._verbose:
            print("i2c_dummy read 0x{:02X} with ack".format(rd))
        return rd
    def read_nack(self):
        '''don't do anything.  Return random 8-bit value'''
        time.sleep(self._delay)
        rd = random.randint(0, 255)
        if self._verbose:
            print("i2c_dummy read 0x{:02X} with nack".format(rd))
        return rd
    def resync_communication(self):
        '''don't do anything.'''
        time.sleep(self._delay)
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        if data_size in (8, 16, 32, 64):
            self.check_size(commandCode, self._cc_size)
            self.check_size(data, data_size)
        elif data_size == 0:
            # send_byte
            self.check_size(commandCode,  self._cc_size)
            assert data is None
        elif data_size == -1:
            # quick_command (unimplemented)
            assert commandCode is None
            assert data is None
            # use_pec meaningless
        else:
            raise Exception('Unimplemented data size: {}. Not within set (0, 8, 16, 32, 64)'.format(data_size))
        self._cc_data[commandCode] = data
        if self._verbose:
            data_str = '0x{{:0{}X}}'.format(data_size // 8 + 1).format(data) if data_size > 0 else None
            print("i2c_dummy write {} to 0x{:02X}{}".format(data_str, commandCode, " with PEC" if use_pec else ""))
    def read_register(self, addr7, commandCode, data_size, use_pec, no_delay=False):
        '''read data (8,16,32, or 64b) with optional additional PEC byte read from slave.'''
        if data_size in (8, 16, 32, 64):
            self.check_size(commandCode, self._cc_size)
        elif data_size in (-1, 0):
            # -1 for quick_command (unimplemented)
            # 0 for receive_byte
            assert commandCode is None
        else:
            raise Exception('Unimplemented data size: {}. Not within set (-1, 0, 8, 16, 32, 64)'.format(data_size))
        if not no_delay:
            time.sleep(self._delay)
        if random.random() > self._p_change:
            try:
                rd = self._cc_data[commandCode]
            except KeyError:
                rd = random.randint(0,2**data_size-1)
        else:
            if data_size == 0:
                #receive byte command is really byte oriented.
                data_size = 8
            rd = random.randint(0,2**data_size-1)
        self._cc_data[commandCode] = rd
        if self._verbose:
            data_str = '0x{{:0{}X}}'.format(data_size // 8 + 1).format(rd) if data_size > -1 else None
            cc_str = '0x{:02X}'.format(commandCode) if commandCode is not None else None
            print("i2c_dummy read {} from {}{}".format(data_str, cc_str, " with PEC" if use_pec else "")) #this doesn't make sense for receive_byte. Needs more implementation work someday.
        return self._cc_data[commandCode]
    def read_register_list(self, addr7, cc_list, data_size, use_pec):
        time.sleep(self._delay)
        return {cc: self.read_register(addr7, cc, data_size, use_pec, no_delay=True) for cc in cc_list}
class i2c_buspirate(twi_interface):
    '''dangerous prototypes bus pirate communication board'''
    def __init__(self,interface_raw_serial):
        self.ser = interface_raw_serial
        self.__init_i2c()
        self.commands = {}
        self.commands['start'] = 0x02 #responds 0x01
        self.commands['stop'] = 0x03 #responds 0x01
        self.commands['read'] = 0x04 #responds with byte
        self.commands['ack'] = 0x06  #responds 0x01
        self.commands['nack'] = 0x07  #responds 0x01
        self.commands['writeread'] = 0x08
        self.commands['writebyte'] = 0x10  #responds 0x01 then 0x00 ACK or 0x01 NACK
        self.commands['writeword'] = 0x11  #responds 0x01 then (0x00 ACK or 0x01 NACK) for each byte
        self.commands['write3'] = 0x12  #responds 0x01 then (0x00 ACK or 0x01 NACK) for each byte
        self.commands['write4'] = 0x13  #responds 0x01 then (0x00 ACK or 0x01 NACK) for each byte
    def __del__(self):
        self.ser.close()
    def __init_i2c(self):
        self.ser.write('\n'*10) #exit any menus
        self.ser.write('#') #reset
        self.ser.read(self.ser.inWaiting())
        #get into binary mode
        resp = ''
        tries = 0
        while (resp != 'BBIO1'):
            tries += 1
            if tries > 20:
                raise i2cMasterError('Buspirate failed to enter binary mode after 20 attempts')
            print('Buspirate entering binary mode attempt {}: '.format(tries), end=' ')
            self.ser.write('\x00') #enter binary mode
            time.sleep(0.05)
            resp = self.ser.read(self.ser.inWaiting())
            print(resp)
        #get into i2c mode
        self.ser.write('\x02') #enter binary i2c mode
        time.sleep(0.05)
        resp = self.ser.read(self.ser.inWaiting())
        if resp != 'I2C1':
             raise i2cMasterError('Buspirate failed to enter I2C mode: {}'.format(resp))
        #set voltage levels
        self.ser.write('\x4C') #power and pullups on
        resp = self.ser.read(1)
        if resp != '\x01':
             raise i2cMasterError('Buspirate failed to enable supply and pullups: {}'.format(resp))
        #vpullup select not yet implemented 7/16/2013.  3.3V shorted to Vpu on board temporarily
        #self.ser.write('\x51') #3.3v pullup
        #resp = self.ser.read(1)
        #if resp != '\x01':
        #     raise i2cMasterError('Buspirate failed to set pullup voltage to 3.3v: {}'.format(resp))
        self.ser.write('\x63') #speed 400kHz
        resp = self.ser.read(1)
        if resp != '\x01':
             raise i2cMasterError('Buspirate failed to set bus speedto 400kHz: {}'.format(resp))
    def close(self):
        '''close the underlying (serial) interface'''
        self.ser.close()
    def start(self):
        '''I2C Start  - Falling SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        self.ser.write(self.commands['start'])
        resp = self.ser.read(1)
        if resp == '\x01':
            return True
        else:
            return False
    def stop(self):
        '''I2C Start  - Rising SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        self.ser.write(self.commands['stop'])
        resp = self.ser.read(1)
        if resp == '\x01':
            return True
        else:
            return False
    def write(self,data8):
        '''Transmit 8 bits plus 9th acknowledge clock.  Returns True or False to indicate slave acknowledge'''
        self.ser.write(bytearray([self.commands['writebyte'], data8]))
        #buspirate returns 0x01 to acknowledge command
        #then returns 0x00 for ACK or 0x01 for NACK
        resp = self.ser.read(2)
        if resp == '\x01\x00':
            return True
        elif resp == '\x01\x01':
            return False
        else:
            raise i2cMasterError('Buspirate write unxepected communication: {}'.format(resp))
    def read_ack(self):
        '''Read 8 bits from slave transmitter  and assert SDA during 9th acknowledge clock.  Returns 8 bit data'''
        #read returns byte
        #ack returns 0x01
        self.ser.write(bytearray([self.commands['read'], self.commands['ack']]))
        resp = self.ser.read(2)
        if len(resp) != 2 or resp[1] != 0x01:
            raise i2cMasterError('Buspirate unexpected response to read_nack: {}'.format(resp))
        return bytearray(resp)[0]
    def read_nack(self):
        '''Read 8 bits from slave transmitter  and release SDA during 9th acknowledge clock to request end of transmission.  Returns 8 bit data'''
        #read returns byte
        #nack returns 0x01
        self.ser.write(bytearray([self.commands['read'], self.commands['nack']]))
        resp = self.ser.read(2)
        if len(resp) != 2 or resp[1] != 0x01:
            raise i2cMasterError('Buspirate unexpected response to read_nack: {}'.format(resp))
        return bytearray(resp)[0]
    def resync_communication(self):
        self.__init_i2c()

    def send_byte(self,addr7,data8):
        '''A simple device may recognize its own slave address and accept up to 256 possible encoded commands in
            the form of a byte that follows the slave address.
            All or parts of the Send Byte may contribute to the command. For example, the highest 7 bits of the
            command code might specify an access to a feature, while the least significant bit would tell the device to
            turn the feature on or off. Or, a device may set the “volume” of its output based on the value it received
            from the Send Byte protocol.'''
        #self.ser.write(bytearray([self.commands['start'], self.write_addr(addr7), data8, self.commands['stop']))
        self.ser.write(bytearray([self.commands['writeread'], 0x00, 0x02, 0x00, 0x00, self.write_addr(addr7), data8]))
        resp = self.ser.read(1)
        if len(resp) != 1 or resp[0] != 0x01:
             raise i2cMasterError('Buspirate unexpected response to send_byte: {}'.format(resp))

    def receive_byte(self, addr7):
        '''The Receive Byte is similar to a Send Byte, the only difference being the direction of data transfer. A
            simple device may have information that the host needs. It can do so with the Receive Byte protocol. The
            same device may accept both Send Byte and Receive Byte protocols. A NACK (a ‘1’ in the ACK bit
            position) signifies the end of a read transfer.'''
        self.ser.write(bytearray([self.commands['writeread'], 0x00, 0x01, 0x00, 0x01, self.read_addr(addr7)]))
        resp = self.ser.read(2)
        if len(resp) != 2 or resp[0] != 0x01:
             raise i2cMasterError('Buspirate unexpected response to receive_byte: {}'.format(resp))
        return bytearray(resp)[1]

    def write_byte(self, addr7, commandCode, data8):
        '''The first byte of a Write Byte access is the command code. The next byte
            is the data to be written. In this example the master asserts the slave device address followed by the write
            bit. The device acknowledges and the master delivers the command code. The slave again acknowledges
            before the master sends the data byte. The slave acknowledges each byte, and the
            entire transaction is finished with a STOP condition.'''
        self.ser.write(bytearray([self.commands['writeread'], 0x00, 0x03, 0x00, 0x00, self.write_addr(addr7), commandCode, data8]))
        resp = self.ser.read(1)
        if len(resp) != 1 or resp[0] != 0x01:
             raise i2cMasterError('Buspirate unexpected response to send_byte: {}'.format(resp))

    def write_word(self, addr7, commandCode, data16):
        '''The first byte of a Write Word access is the command code. The next two bytes
            are the data to be written. In this example the master asserts the slave device address followed by the write
            bit. The device acknowledges and the master delivers the command code. The slave again acknowledges
            before the master sends the data word (low byte first). The slave acknowledges each byte, and the
            entire transaction is finished with a STOP condition.'''
        self.ser.write(bytearray([self.commands['writeread'], 0x00, 0x04, 0x00, 0x00, self.write_addr(addr7), commandCode, self.get_byte(data16,0), self.get_byte(data16,1)]))
        resp = self.ser.read(1)
        if len(resp) != 1 or resp[0] != 0x01:
             raise i2cMasterError('Buspirate unexpected response to write_word: {}'.format(resp))

    def read_byte(self,addr7,commandCode):
        '''Reading data is slightly more complicated than writing data. First the host must write a command to the
            slave device. Then it must follow that command with a repeated START condition to denote a read from
            that device’s address. The slave then returns one byte of data.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        self.ser.write(bytearray([self.commands['start'], self.commands['writeword'], self.write_addr(addr7), commandCode, self.commands['start'], self.commands['writebyte'], self.read_addr(addr7), self.commands['read'], self.commands['nack'], self.commands['stop']]))
        resp = self.ser.read(10)
        if len(resp) != 10:
            raise i2cMasterError('Buspirate short response to read_byte: {}'.format(resp))
        elif resp[0] != 0x01: #start
            raise i2cMasterError('Buspirate read_byte start failure: {}'.format(resp))
        elif resp[1] != 0x01: #write command response
            raise i2cMasterError('Buspirate unexpected response to read_byte: {}'.format(resp))
        elif resp[2] != 0x00: #write addr ack
            raise i2cWriteAddressAcknowledgeError('Buspirate read_byte write address acknowledge failure: {}'.format(resp))
        elif resp[3] != 0x00: #command code ack
            raise i2cCommandCodeAcknowledgeError('Buspirate read_byte command code acknowledge failure: {}'.format(resp))
        elif resp[4] != 0x01: #start
            raise i2cMasterError('Buspirate read_byte restart failure: {}'.format(resp))
        elif resp[5] != 0x01: #write command response
            raise i2cMasterError('Buspirate unexpected response to read_byte: {}'.format(resp))
        elif resp[6] != 0x00: #read addr ack
            raise i2cReadAddressAcknowledgeError('Buspirate read_byte read address acknowledge failure: {}'.format(resp))
        elif resp[8] != 0x01: #nack command response
            raise i2cMasterError('Buspirate unexpected response to read_byte: {}'.format(resp))
        elif resp[9] != 0x01: #stop
            raise i2cMasterError('Buspirate unexpected read_byte stop failure: {}'.format(resp))
        return bytearray(resp)[7]

    def read_word(self,addr7,commandCode):
        '''Reading data is slightly more complicated than writing data. First the host must write a command to the
            slave device. Then it must follow that command with a repeated START condition to denote a read from
            that device’s address. The slave then returns two bytes of data.
            Note that there is no STOP condition before the repeated START condition, and that a NACK signifies the
            end of the read transfer.'''
        self.ser.write(bytearray([self.commands['start'], self.commands['writeword'], self.write_addr(addr7), commandCode, self.commands['start'], self.commands['writebyte'], self.read_addr(addr7), self.commands['read'], self.commands['ack'], self.commands['read'], self.commands['nack'], self.commands['stop']]))
        resp = self.ser.read(12)
        if len(resp) != 12:
            raise i2cMasterError('Buspirate short response to read_word: {}'.format(resp))
        elif resp[0] != 0x01: #start
            raise i2cMasterError('Buspirate read_word start failure: {}'.format(resp))
        elif resp[1] != 0x01: #write command response
            raise i2cMasterError('Buspirate unexpected response to read_word: {}'.format(resp))
        elif resp[2] != 0x00: #write addr ack
            raise i2cWriteAddressAcknowledgeError('Buspirate read_word write address acknowledge failure: {}'.format(resp))
        elif resp[3] != 0x00: #command code ack
            raise i2cCommandCodeAcknowledgeError('Buspirate read_word command code acknowledge failure: {}'.format(resp))
        elif resp[4] != 0x01: #start
            raise i2cMasterError('Buspirate read_word restart failure: {}'.format(resp))
        elif resp[5] != 0x01: #write command response
            raise i2cMasterError('Buspirate unexpected response to read_word: {}'.format(resp))
        elif resp[6] != 0x00: #read addr ack
            raise i2cReadAddressAcknowledgeError('Buspirate read_word read address acknowledge failure: {}'.format(resp))
        #LSByte is resp[7]
        elif resp[8] != 0x01: #ack command response
            raise i2cMasterError('Buspirate unexpected response to read_word: {}'.format(resp))
        #MSByte is resp[9]
        elif resp[10] != 0x01: #nack command response
            raise i2cMasterError('Buspirate unexpected response to read_word: {}'.format(resp))
        elif resp[11] != 0x01: #stop
            raise i2cMasterError('Buspirate read_word stop failure: {}'.format(resp))
        return self.word([bytearray(resp)[7], bytearray(resp)[9]])
class i2c_pic(twi_interface):
    '''communication class to simplify talking to dave's external i2c interface firmware on George's development board (pic18F4553 and similar)
        requires pySerial
    '''
    def __init__(self,interface_raw_serial):
        self.ser = interface_raw_serial
        self.__init_i2c()
    def __del__(self):
        self.ser.close()
    def __init_i2c(self):
        self.ser.read(self.ser.inWaiting())
        self.ser.write("\x03")  #ctl-c
        for i in range(0,6):
            self.ser.write("\r")  #carriage return
        self.ser.write("e")     #select the external interface
        loopcount = 0
        char = self.ser.read(1)
        while(char != "\x02"): # read characters until start of text
            if loopcount > 10000:
                raise i2cMasterError('Failed to set PIC to external interface menu: loopcount')
            if char == '':
                raise i2cMasterError('Failed to set PIC to external interface menu: timeout')
            loopcount += 1
            char = self.ser.read(1)
        self.start()
        self.write(int("E8",16))
        self.write(int("AA",16))
        self.stop()
    def close(self):
        '''close the underlying (serial) interface'''
        self.ser.close()
    def resync_communication(self):
        self.__init_i2c()

    #implement i2c primitives
    def start(self):
        self.ser.write("s")
        ret_str = self.ser.read(4)
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Bad Start")
        elif len(ret_str) >= 3:
            if ret_str[2] != "S":
                raise i2cMasterError("I2C Error: Bad Start")
        #return (ret_str[2:] == "S") #The Pic doesn't know if bus arbitration succeeded - failure to return start indicates USB failure
        return True
    def stop(self):
        self.ser.write("p")
        ret_str = self.ser.read(2)
        if len(ret_str) < 1 or ret_str[0] != "P":
            raise i2cMasterError("I2C Error: Bad Stop")
        #return (ret_str[0] == "P") #The Pic doesn't know if bus arbitration succeeded - failure to return stop indicates USB failure
        return True
    def write(self,data8):
        data8 = int(data8) & 0xFF
        write_str = hex(data8)[2:].rjust(2,"0")
        self.ser.write(write_str)
        ret_str = self.ser.read(5)
        if len(ret_str) < 4 or (ret_str[3] != "K" and ret_str[3] != "N"):
            raise i2cMasterError("I2C Error: Bad Write")
        return (ret_str[3] == "K")
    def read_ack(self):
        self.ser.write("RK")
        ret_str = ""
        num = 0
        ret_str = self.ser.read(3)
        if ret_str[2] != " " or len(ret_str) != 3:
            raise i2cMasterError("I2C Error: Bad communication during read_ack: {}".format(ret_str))
        return int(ret_str[:2],16)
    def read_nack(self):
        self.ser.write("RN")
        ret_str = self.ser.read(3)
        if ret_str[2] != " " or len(ret_str) != 3:
            raise i2cMasterError("I2C Error: Bad communication during read_nack: {}".format(ret_str))
        return int(ret_str[:2],16)

    #overload for faster access
    def read_word(self,addr7,commandCode):
        '''faster way to do an smbus read word'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        addr_r = hex(self.read_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        cmd = "s" + addr_w + commandCode + "s" + addr_r + "RKRNP"
        cmd = cmd
        self.ser.write(cmd)
        ret_str = self.ser.read(31)
        if len(ret_str) != 31:
            raise i2cMasterError("I2C Error: Short response to read_word:{}".format(ret_str))
        if ret_str[7] != "K":
            raise i2cWriteAddressAcknowledgeError("I2C Error: Write address acknowledge fail during read_word")
        if ret_str[12] != "K":
            raise i2cCommandCodeAcknowledgeError("I2C Error: Command code acknowledge fail during read_word")
        if ret_str[21] != "K":
            raise i2cReadAddressAcknowledgeError("I2C Error: Read address acknowledge fail during read_word")
        lsb = ret_str[23:25]
        lsb = int(lsb,16)
        msb = ret_str[26:28]
        msb = int(msb,16)
        data16 = (msb << 8) + lsb
        return data16
class i2c_scpi(twi_interface):
    '''communication class to simplify talking to atmega32u4 with Steve/Eric SCPI firmware requires pySerial'''
    def __init__(self, visa_interface, **kwargs):
        self.interface = visa_interface
        self._cc_list = None
        super().__init__(name="Configurator MCU native i2c port", **kwargs)
        self.set_frequency(400e3)
    def __del__(self):
        self.interface.close()
    def init_i2c(self):
        self.reset_twi()
        #modified this to remove the pyserial inWaiting, now its a plain visa interface
        timeout = self.interface.timeout
        self.interface.timeout = 0.02
        try:
            while len(self.interface.readline()):
                pass
        except visa_wrappers.visaWrapperException:
            pass
        self.interface.timeout = timeout
    def resync_communication(self):
        print("***** i2c_scpi: Attempting RE-SYNC *****")
        self.init_i2c()
    def close(self):
        '''close the underlying (serial) interface'''
        self.interface.close()
    def bus_scan(self):
        self.interface.write('W?;')
        return self.interface.readline().rstrip().lstrip('(@').rstrip(')').split(',')
    def port_status(self):
        results = {}
        self.interface.write(':I2C:PORT:TWSR?;')
        results['TWSR'] = self.interface.readline().strip()
        self.interface.write(':I2C:PORT:TWCR?;')
        results['TWCR'] = self.interface.readline().strip()
        return results
    def reset_twi(self):
        self.interface.write(':I2C:PORT:RST;')
    def set_frequency(self, frequency):
        FCLK = 16e6
        TWBR = int(round(((FCLK / frequency - 16) / 2)))
        assert TWBR <= 255 and TWBR >= 0
        self.interface.write(f':I2C:PORT:TWBR {TWBR};')
        self.reset_twi()
    ###I2C Primitives###
    def start(self):
        self.interface.write(':S?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to start: {}, check and/or cycle COM port.".format(ret_str))
        elif ret_str[0] != "S" :
            raise i2cStartStopError("I2C Error: Bad Start: {}".format(ret_str))
        return (ret_str[0] == "S")
    def stop(self):
        self.interface.write(':P?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to stop: {}".format(ret_str))
        elif ret_str[0] != "P" :
            raise i2cStartStopError("I2C Error: Bad Stop: {}".format(ret_str))
        return (ret_str[0] == "P")
    def write(self,data8):
        data8 = int(data8) & 0xFF
        write_str_b = hex(data8)[2:].rjust(2,"0")
        write_str = ':0X?{};'.format(write_str_b)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to write: {}".format(ret_str))
        return (ret_str[0] == "K")
    def read_ack(self):
        self.interface.write(':RK?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to read_ack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to read_ack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to read_ack: {}".format(ret_str))
        return int(ret_str[:2],16)
    def read_nack(self):
        self.interface.write(':RN?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to read_nack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to read_nack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to read_nack: {}".format(ret_str))
        return int(ret_str[:2],16)
    ###SMBus Overloads###
    def read_word(self,addr7,commandCode):
        '''faster way to do an smbus read word'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        addr_r = hex(self.read_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        write_str = 'SMB:RW?(@{},{});'.format(addr_w,commandCode)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 11:
            raise i2cMasterError("I2C Error: Short Response to read_word: {}".format(ret_str))
        if len(ret_str) > 11:
            raise i2cMasterError("I2C Error: Long Response to read_word: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return int(ret_str[4:8],16)
    def read_word_pec(self,addr7,commandCode):
        '''faster way to do an smbus read word'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        addr_r = hex(self.read_addr(addr7))[2:].rjust(2,"0")
        commandCodeStr = hex(commandCode)[2:].rjust(2,"0")
        write_str = 'SMB:RW:PEC?(@{},{});'.format(addr_w,commandCodeStr)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 14:
            raise i2cMasterError("I2C Error: Short Response to read_word: {}".format(ret_str))
        if len(ret_str) > 14:
            raise i2cMasterError("I2C Error: Long Response to read_word: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        pec = int(ret_str[9:11],16)
        lsb = int(ret_str[6:8],16)
        msb = int(ret_str[4:6],16)
        if self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),lsb,msb,pec]):
            raise i2cPECError("I2C Error: read_word Failed PEC check. Received:{} Expected:{}".format(pec,self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),lsb,msb])))
        return int(ret_str[4:8],16)
    def read_byte(self,addr7,commandCode):
        '''faster way to do an smbus read byte'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        addr_r = hex(self.read_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        write_str = ':SMB:RB?(@{},{});'.format(addr_w,commandCode)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 9:
            raise i2cMasterError("I2C Error: Short Response to read_byte: {}".format(ret_str))
        if len(ret_str) > 9:
            raise i2cMasterError("I2C Error: Long Response to read_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return int(ret_str[4:6],16)
    def read_byte_pec(self,addr7,commandCode):
        '''faster way to do an smbus read byte'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        addr_r = hex(self.read_addr(addr7))[2:].rjust(2,"0")
        commandCodeStr = hex(commandCode)[2:].rjust(2,"0")
        write_str = ':SMB:RB:PEC?(@{},{});'.format(addr_w,commandCodeStr)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 12:
            raise i2cMasterError("I2C Error: Short Response to read_byte: {}".format(ret_str))
        if len(ret_str) > 12:
            raise i2cMasterError("I2C Error: Long Response to read_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        data8 = int(ret_str[4:6],16)
        pec = int(ret_str[7:9],16)
        if self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),data8,pec]):
            raise i2cPECError("I2C Error: read_byte Failed PEC check. Received:{} Expected:{}".format(pec,self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),data8])))
        return data8
    def write_byte(self,addr7,commandCode,data8):
        '''faster way to do an smbus write byte'''
        data8 = int(data8) & 0xFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data8)[2:].rjust(2,"0")
        write_str = ':SMB:WB?(@{},{},{});'.format(addr_w,commandCode,data_w)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError(f"I2C Error: Short Response to write_byte: {ret_str}")
        if len(ret_str) > 6:
            raise i2cMasterError(f"I2C Error: Long Response to write_byte: {ret_str}")
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error writing command code: {commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def write_byte_pec(self,addr7,commandCode,data8):
        '''faster way to do an smbus write byte'''
        data8 = int(data8) & 0xFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCodeStr = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data8)[2:].rjust(2,"0")
        pec = hex(self.pec([self.write_addr(addr7),commandCode,data8]))[2:].rjust(2,"0")
        write_str = ':SMB:WB:PEC?(@{},{},{},{});'.format(addr_w,commandCodeStr,data_w,pec)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError("I2C Error: Short Response to write_byte: {}".format(ret_str))
        if len(ret_str) > 6:
            raise i2cMasterError("I2C Error: Long Response to write_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Error in write_byte_pec (Possible PEC failure). Got:{ret_str} (at addr7:{hex(addr7)}, Commandcode:{commandCode}, data:{data8})")
        return True
    def write_word(self,addr7,commandCode,data16):
        '''faster way to do an smbus write word'''
        data16 = int(data16) & 0xFFFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data16)[2:].rjust(4,"0")
        write_str = ':SMB:WW?(@{},{},{});'.format(addr_w,commandCode,data_w)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError("I2C Error: Short Response to write_word: {}".format(ret_str))
        if len(ret_str) > 6:
            raise i2cMasterError("I2C Error: Long Response to write_word: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error writing command code: {commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def write_word_pec(self,addr7,commandCode,data16):
        '''faster way to do an smbus write word'''
        data16 = int(data16) & 0xFFFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCodeStr = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data16)[2:].rjust(4,"0")
        pec = hex(self.pec([self.write_addr(addr7),commandCode,self.get_byte(data16,0),self.get_byte(data16,1)]))[2:].rjust(2,"0")
        write_str = ':SMB:WW:PEC?(@{},{},{},{});'.format(addr_w,commandCodeStr,data_w,pec)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError("I2C Error: Short Response to write_word: {}".format(ret_str))
        if len(ret_str) > 6:
            raise i2cMasterError("I2C Error: Long Response to write_word: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Error in write_byte_pec (Possible PEC failure). Got:{ret_str} (at addr7: {hex(addr7)}, Commandcode:{commandCode}, data:{data16})")
        return True
    def alert_response(self):
        '''Another optional signal is an interrupt line for devices that want to trade their ability to master for a pin.
        SMBALERT# is a wired-AND signal just as the SMBCLK and SMBDAT signals are. SMBALERT# is
        used in conjunction with the SMBus General Call Address. Messages invoked with the SMBus are 2 bytes
        long.
        A slave-only device can signal the host through SMBALERT# that it wants to talk. The host processes the
        interrupt and simultaneously accesses all SMBALERT# devices through the Alert Response Address
        (ARA). Only the device(s) which pulled SMBALERT# low will acknowledge the Alert Response Address.
        The host performs a modified Receive Byte operation. The 7 bit device address provided by the slave
        transmit device is placed in the 7 most significant bits of the byte. The eighth bit can be a zero or one.

        Returns 7 bit address of responding device.
        Returns None if no response to ARA'''
        self.interface.write(':SMB:ARA?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 9:
            raise i2cMasterError("I2C Error: Short Response to alert_response: {}".format(ret_str))
        if len(ret_str) > 9:
            raise i2cMasterError("I2C Error: Long Response to alert_response: {}".format(ret_str))
        if ret_str[2] != "1":
            return None #no response
        resp_addr = int(ret_str[4:6],16)
        return resp_addr >> 1
    def alert_response_pec(self):
        '''Alert Response Query to SMBALERT# interrupt with Packet Error Check
            Returns 7 bit address of responding device.
            Returns None if no response to ARA'''
        self.interface.write(':SMB:ARA:PEC?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 12:
            raise i2cMasterError("I2C Error: Short Response to alert_response_pec: {}".format(ret_str))
        if len(ret_str) > 12:
            raise i2cMasterError("I2C Error: Long Response to alert_response_pec: {}".format(ret_str))
        if ret_str[2] != "1":
            return None
        resp_addr = int(ret_str[4:6],16)
        pec = int(ret_str[7:9],16)
        if self.pec([self.read_addr(0xC),resp_addr,pec]):
            raise i2cPECError("I2C Error: ARA Failed PEC check")
        return resp_addr >> 1
    def _read_list(self, cmd_bytes,fmt_str, pec, addr7, cc_list):
        assert isinstance(cmd_bytes, bytes)
        pec_str = "B" if pec else ""
        cc_list = sorted(set(cc_list))
        if self._cc_list is None or set(self._cc_list) != set(cc_list):
            write_str = ":TWIBlock:SET "
            for cc in cc_list:
                write_str += "{},".format(cc)
            write_str = write_str.rstrip(',')
            self.interface.write(write_str)
            self._cc_list = cc_list[:] #copy the list values
        write_b = cmd_bytes + f'{self.write_addr(addr7):02x}'.encode(STR_ENCODING) # Note this is b'D2' (2 ASCII bytes), not \xD2 single byte.
        try:
            data = self.interface.ask_for_values_binary(write_b,format_str=f"{fmt_str}{pec_str}", byte_order='>', terminationCharacter='')
        except visa_wrappers.visaWrapperException as e:
            raise i2cIOError("VISA error: {}".format(e))
        if fmt_str == 'H':
            #the cfgpro emits two error code bytes at the beginning of its response; both are absorbed into data[0] by unsigned short format
            #unfortunately, with PEC the error is aligned with the second and third (fake PEC) byte locations. The first byte is always 0.
            if pec:
                #error in this case is in the second (msbyte of word) and third (fake PEC) bytes (data[0:1])
                if data[0] != 0 or data[1] != 0:
                    raise i2cMasterError("I2C communication error at command code:{}. Error count:{}".format(data[2] | data[3], data[0] | data[1]))
            else:
                if data[0] != 0:
                    raise i2cMasterError("I2C communication error at command code:{}. Error count:{}".format(data[1], data[0]))
            data = data[1:]
        elif fmt_str == 'B':
            #the cfgpro emits two error code bytes at the beginning of its response; they remain in data[0:1] with unsigned char format
            if data[0] != 0 or data[1] != 0:
                raise i2cMasterError(f"I²C communication error at I²C addr7: 0x{addr7:02X}, command code:{data[2] << 8 | data[3]}. Error count:{data[0] << 8 | data[1]}")
            data = data[2:]
        else:
            raise Exception("Implementation incomplete")
        results = {}
        if pec:
            if fmt_str == 'H':
                #fake PEC at [0] for acknowledge status flag
                data_list = data[1::2]
                pec_list = data[2::2]
            elif fmt_str == 'B':
                #data already aligned correctly
                data_list = data[0::2]
                pec_list = data[1::2]
            else:
                raise Exception("Implementation incomplete")
            for cc,value,pec in zip(cc_list,data_list,pec_list):
                if fmt_str == 'H':
                    if self.pec([self.write_addr(addr7),cc,self.read_addr(addr7),self.get_byte(value,0),self.get_byte(value,1),pec]):
                        raise i2cPECError('PEC failure at address: {}, command code: {}. Read: {}. Expected: {}'.format(addr7, cc, pec, self.pec([self.write_addr(addr7),cc,self.read_addr(addr7),self.get_byte(value,0),self.get_byte(value,1)])))
                elif fmt_str == 'B':
                    if self.pec([self.write_addr(addr7),cc,self.read_addr(addr7),value,pec]):
                        raise i2cPECError('PEC failure at address: {}, command code: {}. Read: {}. Expected: {}'.format(addr7, cc, pec, self.pec([self.write_addr(addr7),cc,self.read_addr(addr7),value])))
                else:
                    raise Exception("Implementation incomplete")
                results[cc] = value
        else:
            for cc,value in zip(cc_list,data):
                results[cc] = value
        return results
    def read_register_list(self, addr7, cc_list, data_size, use_pec):
        if data_size == 16 and use_pec:
            return self._read_list(cmd_bytes=b'\xE8',fmt_str='H',pec=True,addr7=addr7, cc_list=cc_list) #binary trigger skips SCPI parser
        elif data_size == 16 and not use_pec:
            return self._read_list(cmd_bytes=b'\xE7',fmt_str='H',pec=False,addr7=addr7, cc_list=cc_list) #binary trigger skips SCPI parser
        elif data_size == 8 and use_pec:
            return self._read_list(cmd_bytes=b'\xE6',fmt_str='B',pec=True,addr7=addr7, cc_list=cc_list) #binary trigger skips SCPI parser
        elif data_size == 8 and not use_pec:
            return self._read_list(cmd_bytes=b'\xE5',fmt_str='B',pec=False,addr7=addr7, cc_list=cc_list) #binary trigger skips SCPI parser
        else:
            return twi_interface.read_register_list(self, addr7, cc_list, data_size, use_pec)
    def read_register(self, addr7, commandCode, data_size, use_pec):
        '''read data (8,16,32, or 64b) with optional additional PEC byte read from slave.'''
        if data_size == 8 and use_pec:
            return self.read_byte_pec(addr7, commandCode)
        elif data_size == 8 and not use_pec:
            return self.read_byte(addr7, commandCode)
        elif data_size == 16 and use_pec:
            return self.read_word_pec(addr7, commandCode)
        elif data_size == 16 and not use_pec:
            return self.read_word(addr7, commandCode)
        else:
            return twi_interface.read_register(self, addr7, commandCode, data_size, use_pec)
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        '''write_word with optional additional PEC byte written to slave.'''
        if data_size == 8 and use_pec:
            self.write_byte_pec(addr7, commandCode, data)
        elif data_size == 8 and not use_pec:
            self.write_byte(addr7, commandCode, data)
        elif data_size == 16 and use_pec:
            self.write_word_pec(addr7, commandCode, data)
        elif data_size == 16 and not use_pec:
            self.write_word(addr7, commandCode, data)
        else:
            twi_interface.write_register(self, addr7, commandCode, data, data_size, use_pec)
class i2c_scpi_sp(twi_interface):
    '''communication class to simplify talking to atmega32u4 softport with Steve/Eric SCPI firmware
    requires pySerial
    '''
    def __init__(self,visa_interface, portnum, sclpin, sdapin, pullup_en, **kwargs):
        '''create I2C software port out of any GPIO pins
        visa_interface'''
        self.interface = visa_interface
        self.cmd = f":I2CSP{portnum}"
        self.configure_twi(sclpin = sclpin, sdapin = sdapin, pullup_en = pullup_en)
        name = "i2c softport scl={}, sda={}, pullup_en={}".format(sclpin, sdapin, pullup_en)
        super().__init__(name, **kwargs)
    def __del__(self):
        self.interface.close()
    def init_i2c(self):
        time.sleep(0.1)
        #modified this to remove the pyserial inWaiting, now its a plain visa interface
        timeout = self.interface.timeout
        self.interface.timeout = 0.02
        while len(self.interface.readline()):
            pass
        self.interface.timeout = timeout
    def resync_communication(self):
        pass
    def close(self):
        '''close the underlying (serial) interface'''
        self.interface.close()
    def bus_scan(self):
        self.interface.write('{}:W?;'.format(self.cmd))
        return self.interface.readline().rstrip().lstrip('(@').rstrip(')').split(',')
    def scan_addr7_range(self, addr7_range):
        addr7s_found = []
        for addr7 in addr7_range:
            self.interface.write(f'{self.cmd}:SMB:RECE? (@{hex(self.write_addr(addr7))[2:].rjust(2,"0")},00);')
            ret_str = self.interface.readline()
            if ret_str[2] == "1":
                addr7s_found.append(addr7)
        return addr7s_found
    def port_status(self):
        results = {}
        return results
    def configure_twi(self, sclpin, sdapin, pullup_en):
        self.interface.write('{}:PORT:SDApin {};'.format(self.cmd, sdapin))
        self.interface.write('{}:PORT:SCLpin {};'.format(self.cmd, sclpin))
        if pullup_en:
            self.interface.write('{}:PORT:PUEN;'.format(self.cmd))
        else:
            self.interface.write('{}:PORT:EN;'.format(self.cmd))
    ###I2C Primitives###
    def start(self):
        self.interface.write('{}:S?;'.format(self.cmd))
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to start: {}, check and/or cycle COM port.".format(ret_str))
        elif ret_str[0] != "S" :
            raise i2cStartStopError("I2C Error: Bad Start: {}".format(ret_str))
        return (ret_str[0] == "S")
    def stop(self):
        self.interface.write('{}:P?;'.format(self.cmd))
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to stop: {}".format(ret_str))
        elif ret_str[0] != "P" :
            raise i2cStartStopError("I2C Error: Bad Stop: {}".format(ret_str))
        return (ret_str[0] == "P")
    def write(self,data8):
        data8 = int(data8) & 0xFF
        write_str_b = hex(data8)[2:].rjust(2,"0")
        write_str = ':0X?{};'.format(write_str_b)
        self.interface.write('{}{}'.format(self.cmd, write_str))
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to write: {}".format(ret_str))
        return (ret_str[0] == "K")
    def read_ack(self):
        self.interface.write('{}:RK?;'.format(self.cmd))
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to read_ack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to read_ack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to read_ack: {}".format(ret_str))
        return int(ret_str[:2],16)
    def read_nack(self):
        self.interface.write('{}:RN?;'.format(self.cmd))
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to read_nack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to read_nack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to read_nack: {}".format(ret_str))
        return int(ret_str[:2],16)
    ###SMBus Overloads###
    def receive_byte(self, addr7):
        '''Sent data looks like: "I2CSPx:SMB:RECE?(@AA,00);"
        The 00 command code is ignored for receive_byte.'''
        self.interface.write(f'{self.cmd}:SMB:RECE?(@{self.write_addr(addr7):02x},00);')        # 00 is ignored but needed.
        ret_str = self.interface.readline()
        if len(ret_str) < 9:
            raise i2cMasterError("I2C Error: Short Response to read_byte: {}".format(ret_str))
        if len(ret_str) > 9:
            raise i2cMasterError("I2C Error: Long Response to read_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error addr7: {hex(addr7)}. Got: {ret_str}")
        word = ret_str[4:6]
        data8 = int(word,16)
        return data8
    def receive_byte_pec(self, addr7):
        print("\nReceive byte PEC from i2c_scpi_sp unimplemented. Contact PyICe-developers@analog.com for more information.\n")
        return False
    def send_byte(self, addr7, data8):
        '''Sent data looks like: "I2CSPx:SMB:SEND?(@AA,00,DD);"
        The 00 command code is ignored for sendbyte and the data is _NOT_ moved to the command code location at at the firmware interface.'''
        try:
            ret_str = self.interface.ask(f'{self.cmd}:SMB:SEND?(@{hex(self.write_addr(addr7))[2:].rjust(2,"0")},00,{hex(int(data8) & 0xFF)[2:].rjust(2,"0")});')
        except visa_wrappers.visaWrapperException as e:
            error = self.interface.ask("SYST:ERR?")
            while error != '+0,"No error"':
                print(f"ConfigXT Error Buffer Purge: {error}")
                error = self.interface.ask("SYST:ERR?")
            print(f"\nYou are likely using deprecated Configurator firmware. Strongly consider upgrading your firmware. See Steve Martin. Old firmware will be supported until January 31, 2021.\n")
            return twi_interface.write_register(self, addr7, commandCode=data8, data=None, data_size=0, use_pec=False)
        if len(ret_str) < 4:
            raise i2cMasterError(f"I2C Error: Short Response to send_byte: {ret_str}")
        if len(ret_str) > 4:
            raise i2cMasterError(f"I2C Error: Long Response to send_byte: {ret_str}")
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error sending byte: {data8} to addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def send_byte_pec(self, addr7, data8):
        '''Sent data looks like: "I2CSPx:SMB:SEND:PEC?(@AA,00,DD);"
        The 00 command code is ignored for sendbyte and the data is _NOT_ moved to the command code location at at the firmware interface.'''
        print("\nWarning, send_byte_pec from inside i2c_scpi_sp never tested. If you find it works, please ask PyICe-developers@analog.com to remove this line.\n")
        try:
            ret_str = self.interface.ask(f'{self.cmd}:SMB:SEND:PEC?(@{hex(self.write_addr(addr7))[2:].rjust(2,"0")},00,{hex(int(data8) & 0xFF)[2:].rjust(2,"0")});')
        except visa_wrappers.visaWrapperException as e:
            error = self.interface.ask("SYST:ERR?")
            while error != '+0,"No error"':
                print(f"ConfigXT Error Buffer Purge: {error}")
                error = self.interface.ask("SYST:ERR?")
            print(f"\nYou are likely using deprecated Configurator firmware. Strongly consider upgrading your firmware. See Steve Martin. Old firmware will be supported until January 31, 2021.\n")
            return twi_interface.write_register(self, addr7, commandCode=data8, data=None, data_size=0, use_pec=False)
        if len(ret_str) < 4:
            raise i2cMasterError(f"I2C Error: Short Response to send_byte PEC: {ret_str}")
        if len(ret_str) > 4:
            raise i2cMasterError(f"I2C Error: Long Response to send_byte PEC: {ret_str}")
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error sending byte: {data8} at addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def read_word(self,addr7,commandCode):
        '''faster way to do an smbus read word'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        write_str = ':SMB:RW?(@{},{});'.format(addr_w,commandCode)
        self.interface.write('{}{}'.format(self.cmd, write_str))
        ret_str = self.interface.readline()
        if len(ret_str) < 11:
            raise i2cMasterError("I2C Error: Short Response to read_word: {}".format(ret_str))
        if len(ret_str) > 11:
            raise i2cMasterError("I2C Error: Long Response to read_word: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        word = ret_str[4:8]
        data16 = int(word,16)
        return data16
    def read_byte(self,addr7,commandCode):
        '''faster way to do an smbus read byte'''
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        write_str = ':SMB:RB?(@{},{});'.format(addr_w,commandCode)
        self.interface.write('{}{}'.format(self.cmd, write_str))
        ret_str = self.interface.readline()
        if len(ret_str) < 9:
            raise i2cMasterError("I2C Error: Short Response to read_byte: {}".format(ret_str))
        if len(ret_str) > 9:
            raise i2cMasterError("I2C Error: Long Response to read_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error reading command code:{commandCode} at addr7: {hex(addr7)}. Resp={ret_str}")
        word = ret_str[4:6]
        data8 = int(word,16)
        return data8
    def write_byte(self,addr7,commandCode,data8):
        '''faster way to do an smbus write byte'''
        data8 = int(data8) & 0xFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data8)[2:].rjust(2,"0")
        write_str = ':SMB:WB?(@{},{},{});'.format(addr_w,commandCode,data_w)
        self.interface.write('{}{}'.format(self.cmd, write_str))
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError("I2C Error: Short Response to write_byte: {}".format(ret_str))
        if len(ret_str) > 6:
            raise i2cMasterError("I2C Error: Long Response to write_byte: {}".format(ret_str))
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error writing command code: {commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def write_word(self,addr7,commandCode,data16):
        '''faster way to do an smbus write word'''
        data16 = int(data16) & 0xFFFF
        addr_w = hex(self.write_addr(addr7))[2:].rjust(2,"0")
        commandCode = hex(commandCode)[2:].rjust(2,"0")
        data_w = hex(data16)[2:].rjust(4,"0")
        write_str = ':SMB:WW?(@{},{},{});'.format(addr_w,commandCode,data_w)
        self.interface.write('{}{}'.format(self.cmd, write_str))
        ret_str = self.interface.readline()
        if len(ret_str) < 6:
            raise i2cMasterError(f"I2C Error: Short Response to write_word: {ret_str}")
        if len(ret_str) > 6:
            raise i2cMasterError(f"I2C Error: Long Response to write_word: {ret_str}")
        if ret_str[2] != "1":
            raise i2cAcknowledgeError(f"I2C Acknowledge Error writing command code: {commandCode} at addr7: {hex(addr7)}. Got: {ret_str}")
        return True
    def write_softport_speed(self,sclk_freq):
        def freq_to_counts(sclk_freq):
            return int(round((1./sclk_freq - 24.374e-6) / 2.625e-6))
        def counts_to_freq(counts):
            return 1./(counts * 2.625e-6 + 24.374e-6)
        counts = freq_to_counts(sclk_freq)
        if counts < 0 or counts > 255:
            raise ValueError("Softport delay must be in [0..255], frequency range is limited to {} to {}".format(counts_to_freq(255),counts_to_freq(0)))
        self.interface.write('{}:PORT:DELAY {}'.format(self.cmd, counts))
        if self.interface.ask('ERR?')[1] != "0":
            raise SyntaxError("Softport delay must be in [0..255], frequency range is limited to {} to {}".format(counts_to_freq(255),counts_to_freq(0)))
    def read_register(self, addr7, commandCode, data_size, use_pec):
        '''read data (8,16,32, or 64b) with optional additional PEC byte read from slave.'''
        if data_size == 8 and not use_pec:
            return self.read_byte(addr7, commandCode)
        elif data_size == 16 and not use_pec:
            return self.read_word(addr7, commandCode)
        elif data_size == 0 and use_pec:
            assert commandCode is None
            return self.receive_byte_pec(addr7)
        elif data_size == 0 and not use_pec:
            assert commandCode is None
            return self.receive_byte(addr7)
        else:
            return twi_interface.read_register(self, addr7, commandCode, data_size, use_pec)
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        '''write_word with optional additional PEC byte written to slave.'''
        if data_size == 8 and not use_pec:
            self.write_byte(addr7, commandCode, data)
        elif data_size == 16 and not use_pec:
            self.write_word(addr7, commandCode, data)
        elif data_size == 0 and use_pec:
            assert data is None
            return self.send_byte_pec(addr7, commandCode) # This is miserable. Why move the data to the CC.
        elif data_size == 0 and not use_pec:
            assert data is None
            return self.send_byte(addr7, commandCode) # This is miserable. Why move the data to the CC.
        else:
            twi_interface.write_register(self, addr7, commandCode, data, data_size, use_pec)
# needs to be moved to lab, not twi
class i2c_scpi_testhook(i2c_scpi):
    def __init__(self,serial_port):
        i2c_scpi.__init__(self, serial_port)
        self.channels = {}
        self.name = "i2c_scpi_testhook at {}".format(serial_port) #what is the str repr of a serial port object?
    ###lab.py instrument driver methods###
    def add_channel(self,channel_name,pin_name):
        '''Adds a channel of name channel_name, associated with physical pin pin_name.
        When written to, the pin state is changed.
        Valid pin_names are: HOOK1, HOOK2, HOOK3, HOOK4,
        PAD_TP_1, PAD_TP_2, PAD_TP_3, PAD_TP_4, PAD_TP_5,
        PAD_TP_6, PAD_TP_7, PAD_TP_8, PAD_TP_9, GPIO'''
        pin_name = self.check_name(pin_name)
        self.channels[channel_name] = pin_name
    def read_channel(self,channel_name):
        '''When read, this channel returns the state of the pin (not necessarily what it was set to).
        Possible responses are:
        0,1,Z,P
        Where Z is high-z
        and P is weak pullup'''
        return self.read_pin(self.channels[channel_name]) #perhaps this should return what the pin was set to, not what was read-back (wired-nor)?
    def write_channel(self,channel_name,value):
        '''When channel is written to, the pin state is updated.
        Valid values are:
        0,1,Z,P
        Where Z is high-z
        and P is weak pullup'''
        self.set_pin(self.channels[channel_name], value)
    ###purple-board specific hardware driver methods###
    def set_dvcc(self, voltage):
        self.aux_start()
        self.aux_write(0xE8)
        data = int(max(min(voltage, 5), 0.8)/5.0*63.0) & 0x3F
        self.aux_write(data)
        self.aux_stop()
    def set_pin(self, pin_name, value):
        '''Pins are: HOOK1, HOOK2, HOOK3, HOOK4,
        PAD_TP_1, PAD_TP_2, PAD_TP_3, PAD_TP_4, PAD_TP_5,
        PAD_TP_6, PAD_TP_7, PAD_TP_8, PAD_TP_9, GPIO

        Value is 0,1,Z,P
        Where Z is high-z
        and P is weak pullup
        '''
        if value == True or value == 1 or value == '1':
            value = 1
        elif value == False or value == 0 or value == '0':
            value = 0
        elif value == 'Z' or value == 'z' or value == 'P' or value == 'p':
            pass
        else:
            raise Exception('Bad value argument passed for pin: {}'.format(value))
        pin_name = self.check_name(pin_name)
        write_str = ':SETPin(@{},{});:SETPin?(@{});'.format(pin_name,value,pin_name) #set the pin and read back its state to make sure there were no usb communication problems
        self.interface.write(write_str)
        ret_str = self.interface.read(3)
        if len(ret_str) < 3:
            raise i2cMasterError("I2C Error: Short Response to set_pin: {}".format(ret_str))
        if len(ret_str) > 3:
            raise i2cMasterError("I2C Error: Long Response to set_pin: {}".format(ret_str))
        if ret_str[1:] != '\r\n':
            raise i2cMasterError("I2C Error: Bad Response to set_pin: {}".format(ret_str))
        if ret_str[0] != str(value).upper():
            raise i2cMasterError("I2C Error: Failed to set_pin: {}".format(ret_str))
    def read_pin(self, pin_name):
        pin_name = self.check_name(pin_name)
        write_str = ':SETPin?(@{});'.format(pin_name)
        self.interface.write(write_str)
        ret_str = self.interface.read(3)
        if len(ret_str) < 3:
            raise i2cMasterError("I2C Error: Short Response to read_pin: {}".format(ret_str))
        if len(ret_str) > 3:
            raise i2cMasterError("I2C Error: Long Response to read_pin: {}".format(ret_str))
        if ret_str[1:] != '\r\n':
            raise i2cMasterError("I2C Error: Bad Response to read_pin: {}".format(ret_str))
        return ret_str[0]
    def check_name(self, name):
        pin_names = ['HOOK1', 'HOOK2', 'HOOK3', 'HOOK4',
        'PAD_TP_1', 'PAD_TP_2', 'PAD_TP_3', 'PAD_TP_4', 'PAD_TP_5',
        'PAD_TP_6', 'PAD_TP_7', 'PAD_TP_8', 'PAD_TP_9', 'GPIO']
        uname = name.upper()
        if uname in pin_names:
            return uname
        else:
            raise Exception('Invalid pin name {}'.format(name))
    ###Secondary I2C Port Primitives###
    def aux_start(self):
        self.interface.write(':I2CAux:S?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to aux port start: {}".format(ret_str))
        elif ret_str[0] != "S" :
            raise i2cStartStopError("I2C Error: Bad aux port Start: {}".format(ret_str))
        return (ret_str[0] == "S")
    def aux_stop(self):
        self.interface.write(':I2CAux:P?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to aux port stop: {}".format(ret_str))
        elif ret_str[0] != "P" :
            raise i2cStartStopError("I2C Error: Bad aux port Stop: {}".format(ret_str))
        return (ret_str[0] == "P")
    def aux_write(self,data8):
        data8 = int(data8) & 0xFF
        write_str_b = hex(data8)[2:].rjust(2,"0")
        write_str = ':I2CAux:0X?{};'.format(write_str_b)
        self.interface.write(write_str)
        ret_str = self.interface.readline()
        if len(ret_str) < 2:
            raise i2cMasterError("I2C Error: Short Response to aux port write: {}".format(ret_str))
        return (ret_str[0] == "K")
    def aux_read_ack(self):
        self.interface.write(':I2CAux:RK?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to aux port read_ack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to aux port read_ack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to aux port read_ack: {}".format(ret_str))
        return int(ret_str[:2],16)
    def aux_read_nack(self):
        self.interface.write(':I2CAux:RN?;')
        ret_str = self.interface.readline()
        if len(ret_str) < 4:
            raise i2cMasterError("I2C Error: Short Response to aux port read_nack: {}".format(ret_str))
        if len(ret_str) > 4:
            raise i2cMasterError("I2C Error: Long Response to aux port read_nack: {}".format(ret_str))
        if ret_str[3] != "\n":
            raise i2cMasterError("I2C Error: Bad Response to aux port read_nack: {}".format(ret_str))
        return int(ret_str[:2],16)
class i2c_dc590(twi_interface):
    '''Generic DC590/Linduino Driver.
     Note that DC590 will not communicate unless it detects pullups on auxillary i2c port.
     To avoid being halted by the need for an EEPROM tie PIN 2 to PIN 9 VCC-SDA_AUX.
     Linduino does not have above limitiation.'''
    def __init__(self, interface_stream):
        self.iface = interface_stream
        self.init_i2c()
        self.set_gpio(True) #Hi-Z with PyICe list read sketch; GPIO read not yet implemented...
    def __del__(self):
        self.close()
    def init_i2c(self):
        time.sleep(2.5) #Linduino bootloader delay!
        self.iface.write(('\n'*10))
        time.sleep(2.5) #Linduino bootloader delay!
        print('DC590 init response: {}'.format(self.iface.read(None)[0])) #discard any responses
        self.iface.write('O') #Enable isolated power
        try:
            self.i2c_mode()
        except i2cMasterError as e:
            print(e)
    def i2c_mode(self):
        '''Switch DC590 I2C/SPI mux to SPI'''
        self.iface.write('MI') #Switch to isolated I2C Mode
        time.sleep(0.1)
        buffer = self.iface.read(None)[0]
        if len(buffer):
            raise i2cMasterError('Error switching DC590 to I2C Mode. Unexpected data in buffer:{}'.format(buffer))
    def _hex_str(self, integer):
        '''return integer formatted correctly for transmission over DC590 serial link'''
        return hex(integer).rstrip("L")[2:].rjust(2,"0").upper()
    def start(self):
        self.iface.write('s') #no response expected
        return True
    def stop(self):
        self.iface.write('p') #no response expected
        return True
    def write(self,data8):
        data8 = int(data8) & 0xFF
        write_str = 'S' + hex(data8)[2:].rjust(2,"0").upper()
        self.iface.write(write_str)
        time.sleep(0.02) #how long do we have to wait to see if the dc590 is going to "N"ack
        ret_str = self.iface.read(None)[0]
        if len(ret_str) == 1 and ret_str[0] == 'N':
            return False #failed acknowledge
        elif len(ret_str) == 1 and ret_str[0] == 'X':
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {}'.format(ret_str))
        elif len(ret_str) == 0:
            return True
        else:
            raise i2cMasterError('Bad response to DC590 write command: {}'.format(ret_str))
    def read_ack(self):
        self.iface.write("Q")
        resp = self.iface.read(2)
        ret_str = resp[0]
        if len(ret_str) != 2:
            raise i2cMasterError('Short response to DC590 read_ack command, EEPROM Present?: {}'.format(ret_str))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cMasterError('Long response to DC590 read_ack command: {} then {}'.format(ret_str, ret_extra))
        return int(ret_str,16)
    def read_nack(self):
        self.iface.write("R")
        resp = self.iface.read(2)
        ret_str = resp[0]
        if len(ret_str) != 2:
            raise i2cMasterError('Short response to DC590 read_nack command, EEPROM Present?: {}'.format(ret_str))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cMasterError('Long response to DC590 read_nack command: {} then {}'.format(ret_str, ret_extra))
        return int(ret_str,16)
    def set_gpio(self, pin_high):
        if pin_high:
            self.iface.write("G") #sets tristate for list_read sketch. C and r commands from 590 not implemented.
        else:
            self.iface.write("g")
    def read_register(self, addr7, commandCode, data_size, use_pec):
        '''read data (8,16,32, or 64b) with optional additional PEC byte read from slave.'''
        if data_size == 8 and use_pec:
            return self.read_byte_pec(addr7, commandCode)
        elif data_size == 8 and not use_pec:
            return self.read_byte(addr7, commandCode)
        elif data_size == 16 and use_pec:
            return self.read_word_pec(addr7, commandCode)
        elif data_size == 16 and not use_pec:
            return self.read_word(addr7, commandCode)
        elif data_size == 32 and use_pec:
            return self.read_32_pec(addr7, commandCode)
        elif data_size == 32 and not use_pec:
            return self.read_32(addr7, commandCode)
        else:
            return twi_interface.read_register(self, addr7, commandCode, data_size, use_pec)
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        '''write_word with optional additional PEC byte written to slave.'''
        if data_size == 8 and use_pec:
            self.write_byte_pec(addr7, commandCode, data)
        elif data_size == 8 and not use_pec:
            self.write_byte(addr7, commandCode, data)
        elif data_size == 16 and use_pec:
            self.write_word_pec(addr7, commandCode, data)
        elif data_size == 16 and not use_pec:
            self.write_word(addr7, commandCode, data)
        elif data_size == 32 and use_pec:
            self.write_32_pec(addr7, commandCode, data)
        elif data_size == 32 and not use_pec:
            self.write_32(addr7, commandCode, data)
        elif data_size == 0 and not use_pec:
            self.send_byte(addr7, commandCode)
        else:
            twi_interface.write_register(self, addr7, commandCode, data, data_size, use_pec)
    ###SMBus Overloads
    def read_byte(self,addr7,commandCode):
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}Rp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(2)
        ret_str = resp[0]
        if len(ret_str) != 2:
            raise i2cMasterError('Short response to DC590 read_byte command, EEPROM Present?: {}'.format(ret_str))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cMasterError('Long response to DC590 read_byte command: {} then {}'.format(ret_str, ret_extra))
        return int(ret_str,16)
    def read_byte_pec(self, addr7, commandCode):
        '''SMBus Read Byte Protocol with Packet Error Checking.
        Slave device address specified in 7-bit format.
        Returns 8-bit data from slave.'''
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}QRp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(4)
        ret_str = resp[0]
        if (len(ret_str) != 4):
            raise i2cMasterError('Short response to DC590 read_byte_pec command, EEPROM Present?: %s' % ret_str)
        byteList.append(int(ret_str[0:2],16))
        byteList.append(int(ret_str[2:4],16))
        if self.pec(byteList):
            raise i2cPECError('DC590 read_byte_pec command failed PEC')
        if ('N' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cAcknowledgeError('DC590 read_byte_pec failed acknowledge: {} then {}'.format(ret_str, ret_extra))
        if ('X' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {} then {}'.format(ret_str, ret_extra))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('Long response to DC590 read_byte_pec command: {} then {}'.format(ret_str, ret_extra))
        return byteList[-2]
    def read_word(self,addr7,commandCode):
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}QRp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(4)
        ret_str = resp[0]
        if len(ret_str) != 4:
            raise i2cMasterError('Short response to DC590 read_word command, EEPROM Present?: {}'.format(ret_str))
        if 'N' in ret_str:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cError('DC590 read_word failed acknowledge: {} then {}'.format(ret_str, ret_extra))
        if 'X' in ret_str:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {} then {}'.format(ret_str, ret_extra))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)[0]
            raise i2cMasterError('Long response to DC590 read_word command: {} then {}'.format(ret_str, ret_extra))
        return self.word([int(ret_str[0:2],16), int(ret_str[2:4],16)])
    def read_word_pec(self, addr7, commandCode):
        '''SMBus Read Word Protocol with Packet Error Checking.
        Slave device address specified in 7-bit format.
        Returns 16-bit data from slave.'''
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}QQRp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(6)
        ret_str = resp[0]
        if (len(ret_str) != 6):
            raise i2cMasterError('Short response to DC590 read_word_pec command, EEPROM Present?: %s' % ret_str)
        byteList.append(int(ret_str[0:2],16))
        byteList.append(int(ret_str[2:4],16))
        if int(ret_str[4:6],16) != self.pec(byteList):
            raise i2cPECError('DC590 read_word_pec command failed PEC')
        if ('N' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cAcknowledgeError('DC590 read_word_pec failed acknowledge: {} then {}'.format(ret_str, ret_extra))
        if ('X' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {} then {}'.format(ret_str, ret_extra))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('Long response to DC590 read_word_pec command: {} then {}'.format(ret_str, ret_extra))
        return self.word([int(ret_str[0:2],16), int(ret_str[2:4],16)])
    def read_32(self, addr7, commandCode):
        '''SMBus Read 32-bit Protocol without Packet Error Checking.
        Slave device address specified in 7-bit format.
        Returns 32-bit data from slave.'''
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}QQQRp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(8)
        ret_str = resp[0]
        if (len(ret_str) != 8):
            raise i2cMasterError('Short response to DC590 read_32 command, EEPROM Present?: %s' % ret_str)
        if ('N' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cAcknowledgeError('DC590 read_32 failed acknowledge: {} then {}'.format(ret_str, ret_extra))
        if ('X' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {} then {}'.format(ret_str, ret_extra))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('Long response to DC590 read_32 command: {} then {}'.format(ret_str, ret_extra))
        return self.word([int(ret_str[0:2],16), int(ret_str[2:4],16), int(ret_str[4:6],16), int(ret_str[6:8],16)])
    def read_32_pec(self, addr7, commandCode):
        '''SMBus Read 32-bit Protocol with Packet Error Checking.
        Slave device address specified in 7-bit format.
        Returns 32-bit data from slave.'''
        self.check_size(commandCode,8)
        byteList = [self.write_addr(addr7), commandCode, self.read_addr(addr7)]
        write_str = 'sS{}S{}sS{}QQQQRp'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(10)
        ret_str = resp[0]
        if (len(ret_str) != 10):
            raise i2cMasterError('Short response to DC590 read_32_pec command, EEPROM Present?: %s' % ret_str)
        byteList.append(int(ret_str[0:2],16))
        byteList.append(int(ret_str[2:4],16))
        byteList.append(int(ret_str[4:6],16))
        byteList.append(int(ret_str[6:8],16))
        if int(ret_str[8:10],16) != self.pec(byteList):
            raise i2cPECError('DC590 read_32_pec command failed PEC')
        if ('N' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cAcknowledgeError('DC590 read_32_pec failed acknowledge: {} then {}'.format(ret_str, ret_extra))
        if ('X' in ret_str):
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('DC590 EEPROM detection failed, communications disabled: {} then {}'.format(ret_str, ret_extra))
        if resp[1]:
            time.sleep(.1)
            ret_extra = self.iface.read(None)
            raise i2cMasterError('Long response to DC590 read_31_pec command: {} then {}'.format(ret_str, ret_extra))
        return self.word([int(ret_str[0:2],16), int(ret_str[2:4],16), int(ret_str[4:6],16), int(ret_str[6:8],16)])
    def write_byte(self,addr7,commandCode,data8):
        self.check_size(commandCode,8)
        self.check_size(data8,8)
        byteList = [self.write_addr(addr7), commandCode, data8]
        write_str = 'sS{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Response: {} from DC590 write_byte command'.format(ret_str))
    def write_byte_pec(self,addr7,commandCode,data8):
        self.check_size(commandCode,8)
        self.check_size(data8,8)
        byteList = [self.write_addr(addr7), commandCode, data8]
        byteList.append(self.pec(byteList))
        write_str = 'sS{}S{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Bad response: {} from DC590 write_byte_pec command'.format(ret_str))
    def write_word(self,addr7,commandCode,data16):
        self.check_size(commandCode,8)
        self.check_size(data16,16)
        byteList = [self.write_addr(addr7), commandCode, self.get_byte(data16,0), self.get_byte(data16,1)]
        write_str = 'sS{}S{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Response: {} from DC590 write_word command'.format(ret_str))
    def write_word_pec(self,addr7,commandCode,data16):
        self.check_size(commandCode,8)
        self.check_size(data16,16)
        byteList = [self.write_addr(addr7), commandCode, self.get_byte(data16,0), self.get_byte(data16,1)]
        byteList.append(self.pec(byteList))
        write_str = 'sS{}S{}S{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Bad response: {} from DC590 write_word_pec command'.format(ret_str))
    def write_32(self,addr7,commandCode,data32):
        self.check_size(commandCode,8)
        self.check_size(data32,32)
        byteList = [self.write_addr(addr7), commandCode, self.get_byte(data32,0), self.get_byte(data32,1), self.get_byte(data32,2), self.get_byte(data32,3)]
        write_str = 'sS{}S{}S{}S{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Bad response: {} from DC590 write_32 command'.format(ret_str))
    def write_32_pec(self,addr7,commandCode,data32):
        self.check_size(commandCode,8)
        self.check_size(data32,32)
        byteList = [self.write_addr(addr7), commandCode, self.get_byte(data32,0), self.get_byte(data32,1), self.get_byte(data32,2), self.get_byte(data32,3)]
        byteList.append(self.pec(byteList))
        write_str = 'sS{}S{}S{}S{}S{}S{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Bad response: {} from DC590 write_32_pec command'.format(ret_str))
    def send_byte(self,addr7,data8):
        self.check_size(data8,8)
        byteList = [self.write_addr(addr7), data8]
        write_str = 'sS{}S{}p'.format(*list(map(self._hex_str, byteList)))
        self.iface.write(write_str)
        resp = self.iface.read(None)
        ret_str = resp[0]
        if len(ret_str) != 0:
            raise i2cError('Response: {} from DC590 send_byte command'.format(ret_str))
    def resync_communication(self):
        self.iface.read(None)

class i2c_firmata(twi_interface):
    '''i2c communication class using Firmata protocol.
    
    NB: This package is not actively maintained. It has been replaced by Telemetrix. Consider using Telemetrix instead.

      Firmata is a protocol for communicating with microcontrollers from software on a host computer.
    The protocol can be implemented in firmware on any microcontroller architecture as well as software on any host computer software package.
    The Arduino repository described here is a Firmata library for Arduino and Arduino-compatible devices. If you would like to contribute to Firmata, please see the Contributing section below.

    Usage
    The model supported by PyICe is to load a general purpose sketch called StandardFirmata
    on the Arduino board and then use the host computer exclusively to interact with the Arduino board.

    *** Arduino/Linduno specific:
    *** StandardFirmata is located in the Arduino IDE in File -> Examples -> Firmata.
    *** This sketch must be flashed onto the microcontroller board to use this instrument driver.

    *** Other microcontrollers:
    *** Must flash architechture-specific compiled embedded server.

    https://github.com/firmata/protocol/blob/master/README.md

    https://github.com/firmata/arduino/blob/master/readme.md

    https://github.com/MrYsLab/PyMata/blob/master/README.md
    '''
    def __init__(self,firmata_instance):
        '''Because of shared serial port, twi driver requires an existing instance of lab_instruments.firmata (PyMata wrapper)'''
        print("Consider switching from Firmata to Telemetrix")
        self.firmata = firmata_instance.firmata_board
        self.init_i2c()
    def init_i2c(self):
        self.firmata.i2c_config(read_delay_time=0, pin_type=None, clk_pin=0, data_pin=0)
    ###I2C Primitives###
    def start(self):
        raise i2cUnimplementedError('Firmata I2C primitives not implemented')
    def stop(self):
        raise i2cUnimplementedError('Firmata I2C primitives not implemented')
    def write(self,data8):
        raise i2cUnimplementedError('Firmata I2C primitives not implemented')
    def read_ack(self):
        raise i2cUnimplementedError('Firmata I2C primitives not implemented')
    def read_nack(self):
        raise i2cUnimplementedError('Firmata I2C primitives not implemented')
    ###SMBus Overloads###
    def read_word(self,addr7,commandCode):
        '''smbus read word'''
        error = self.firmata.i2c_read(addr7, commandCode, number_of_bytes=2, read_type=self.firmata.I2C_READ, cb=None)
        if error is not None:
            raise i2cAcknowledgeError("".join(error))
        data = self.firmata.i2c_get_read_data(addr7)
        while data is None:
            data = self.firmata.i2c_get_read_data(addr7)
        err, lsb, msb = data
        return self.word([lsb, msb])
    def read_word_pec(self,addr7,commandCode):
        '''smbus read word with PEC'''
        error = self.firmata.i2c_read(addr7, commandCode, number_of_bytes=3, read_type=self.firmata.I2C_READ, cb=None)
        if error is not None:
            raise i2cAcknowledgeError("".join(error))
        data = self.firmata.i2c_get_read_data(addr7)
        while data is None:
            data = self.firmata.i2c_get_read_data(addr7)
        err, lsb, msb, pec = data
        #if self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),lsb,msb,pec]):
        if self.pec([self.read_addr(addr7),lsb,msb,pec]): #stop'ping half way through!
            raise i2cPECError("I2C Error: read_word Failed PEC check. Received:{} Expected:{}".format(pec,self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),lsb,msb])))
        return self.word([lsb, msb])
    def read_byte(self,addr7,commandCode):
        '''smbus read byte'''
        error = self.firmata.i2c_read(addr7, commandCode, number_of_bytes=1, read_type=self.firmata.I2C_READ, cb=None)
        if error is not None:
            raise i2cAcknowledgeError("".join(error))
        data = self.firmata.i2c_get_read_data(addr7)
        while data is None:
            data = self.firmata.i2c_get_read_data(addr7)
        return data[1]
    def read_byte_pec(self,addr7,commandCode):
        '''smbus read byte with PEC'''
        error = self.firmata.i2c_read(addr7, commandCode, number_of_bytes=2, read_type=self.firmata.I2C_READ, cb=None)
        if error is not None:
            raise i2cAcknowledgeError("".join(error))
        data = self.firmata.i2c_get_read_data(addr7)
        while data is None:
            data = self.firmata.i2c_get_read_data(addr7)
        err, data8, pec = data
        #if self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),data8,pec]):
        if self.pec([self.read_addr(addr7),data8,pec]): #stop'ping half way through!
            raise i2cPECError("I2C Error: read_byte Failed PEC check. Received:{} Expected:{}".format(pec,self.pec([self.write_addr(addr7),commandCode,self.read_addr(addr7),data8])))
        return data8
    def write_byte(self,addr7,commandCode,data8):
        '''smbus write byte'''
        self.firmata.i2c_write(addr7, commandCode, data8)
        return True
    def write_byte_pec(self,addr7,commandCode,data8):
        '''smbus write byte with PEC'''
        self.firmata.i2c_write(addr7, commandCode, data8, self.pec([self.write_addr(addr7),commandCode,data8]))
        return True
    def write_word(self,addr7,commandCode,data16):
        '''smbus write word'''
        self.firmata.i2c_write(addr7, commandCode, self.get_byte(data16,0), self.get_byte(data16,1))
        return True
    def write_word_pec(self,addr7,commandCode,data16):
        '''smbus write word with PEC'''
        self.firmata.i2c_write(addr7, commandCode, self.get_byte(data16,0), self.get_byte(data16,1), self.pec([self.write_addr(addr7),commandCode,self.get_byte(data16,0),self.get_byte(data16,1)]))
        return True
    def alert_response(self):
        '''smbus ARA'''
        raise i2cUnimplementedError('Firmata ARA not implemented')
        '''# self.interface.write(':SMB:ARA?;')
        # ret_str = self.interface.readline()
        # if len(ret_str) < 9:
            # raise i2cMasterError("I2C Error: Short Response to alert_response: {}".format(ret_str))
        # if len(ret_str) > 9:
            # raise i2cMasterError("I2C Error: Long Response to alert_response: {}".format(ret_str))
        # if ret_str[2] != "1":
            # return None #no response
        # resp_addr = int(ret_str[4:6],16)
        # return resp_addr >> 1'''
    def alert_response_pec(self):
        '''Alert Response Query to SMBALERT# interrupt with Packet Error Check
            Returns 7 bit address of responding device.
            Returns None if no response to ARA'''
        raise i2cUnimplementedError('Firmata ARA not implemented')
        '''# self.interface.write(':SMB:ARA:PEC?;')
        # ret_str = self.interface.readline()
        # if len(ret_str) < 12:
            # raise i2cMasterError("I2C Error: Short Response to alert_response_pec: {}".format(ret_str))
        # if len(ret_str) > 12:
            # raise i2cMasterError("I2C Error: Long Response to alert_response_pec: {}".format(ret_str))
        # if ret_str[2] != "1":
            # return None
        # resp_addr = int(ret_str[4:6],16)
        # pec = int(ret_str[7:9],16)
        # if self.pec([self.read_addr(0xC),resp_addr,pec]):
            # raise i2cPECError("I2C Error: ARA Failed PEC check")
        # return resp_addr >> 1'''
class x0020_SMBUS:
    '''This demoboard SMBUS module understands commands of the form:
        typedef struct
        {
            uint8_t noun;   /* BYTE, BYTE_PEC, WORD, WORD_PEC,
                               ALERT, LIST_SETUP, LIST_DATA */
            uint8_t verb;   /* READ or WRITE */
            union
            {
                /* verb noun = READ (BYTE or BYTE_PEC or WORD or WORD_PEC) */
                struct
                {
                    uint8_t addr7;
                    uint8_t smbus_reg;
                } read_args;

                /* verb noun = WRITE BYTE */
                struct
                {
                    uint8_t addr7;
                    uint8_t smbus_reg;
                    uint8_t data;
                } write_byte_args;

                /* verb noun = WRITE WORD */
                struct
                {
                    uint8_t addr7;
                    uint8_t smbus_reg;
                    uint16_t data;
                } write_word_args;

                /* verb noun = WRITE BYTE_PEC */
                struct
                {
                    uint8_t addr7;
                    uint8_t smbus_reg;
                    uint8_t data;
                    uint8_t pec;
                } write_byte_pec_args;

                /* verb noun = WRITE WORD_PEC */
                struct
                {
                    uint8_t addr7;
                    uint8_t smbus_reg;
                    uint16_t data;
                    uint8_t pec;
                } write_word_pec_args;

                /* verb noun = WRITE LIST_SETUP (distinguish by command argument size)*/
                struct
                {
                    uint8_t addr7;
                } write_list_reg_setup_addr;

                /* verb noun = WRITE LIST_SETUP (distinguish by command argument size)*/
                struct
                {
                    uint8_t addr7;
                    uint16_t first_reg;
                    uint16_t num_reg;
                    uint8_t bitmap_reg[0];
                } write_list_reg_setup;
            };
        } module_0x0020_SMBUS_command;    '''
    class noun:
        BYTE = 0x00
        WORD = 0x01
        BYTE_PEC = 0x02
        WORD_PEC = 0x03
        ALERT = 0x04
        LIST_SETUP = 0x05
        LIST_DATA = 0x06    # Note: This might be using PEC now. Check with Bobby.
        STATELESS_WORD_LIST_PEC = 0x07
        ARA = 0x08
        ARA_PEC = 0x09
        WORD_PEC_V2 = 0x0a
        STATELESS_WORD_LIST_PEC_V2 = 0x0b
        BYTE_V2 = 0x0c        # Read/Write/etc. byte commands with transaction tags
                              # and timestamps
        WORD_V2 = 0x0d        # Read/Write/etc. word commands with transaction tags
                              # and timestamps
        STATELESS_WORD_LIST = 0x0e
        BYTE_PEC_V2 = 0x0F
        STATELESS_BYTE_LIST_PEC_V2 = 0x10
    class verb:
        READ = 0
        WRITE = 1
        RESET = 2
    MAX_NUMBER_OF_COMMAND_CODES = 2**8  # This module assumes 8-bit command codes.
    BITS_PER_BYTE = 8
class i2c_bobbytalk(twi_interface):
    '''An i2c_bobbytalk object sends and receives bobbytalk protocol packets to tell a Linduino running
       bobbytalk F/W to perform i2c reads and writes.'''
    def __init__(self, bobbytalk_interface, src_id, dest_id=None,
                 recv_timeout=1.0, cmd_tries=2, per_cmd_recv_tries=4, debug=False):
        '''Create an i2c_bobbytalk object by specifying the bobbytalk interface, packet source id to use
        in command packets, and optionally the destination module id to use to communicate
        (which must be an SMBUS module).'''
        from . import lab_interfaces, bobbytalk
        assert isinstance(bobbytalk_interface, lab_interfaces.interface_bobbytalk)
        if dest_id is None:
            dest_id = bobbytalk.SMBUS_module_id
        assert isinstance(dest_id, int) and dest_id < 2**(8*bobbytalk.packet.DEST_ID_SIZE)
        assert isinstance(src_id, int) and dest_id < 2**(8*bobbytalk.packet.SRC_ID_SIZE)
        self.intf = bobbytalk_interface
        self._src_id = src_id
        self._dest_id = dest_id
        self._recv_timeout = recv_timeout
        self._cmd_tries = cmd_tries
        self._recv_tries = per_cmd_recv_tries
        self.debug = debug
    #
    # Documented settable properties.
    #
    @property
    def src_id(self):
        "Source ID to use when sending bobbytalk packets to the remote SMBUS module."
        return self._src_id
    @src_id.setter
    def src_id(self, val):
        from . import bobbytalk
        assert isinstance(val, int)
        self.check_size(val, 8*bobbytalk.packet.SRC_ID_SIZE)
        self._src_id = val
    @property
    def dest_id(self):
        "Destination ID to use when sending bobbytalk packets to the remote SMBUS module."
        return self._dest_id
    @dest_id.setter
    def dest_id(self, val):
        from . import bobbytalk
        assert isinstance(val, int)
        self.check_size(val, 8*bobbytalk.packet.DEST_ID_SIZE)
        self._dest_id = val
    @property
    def recv_timeout(self):
        "Total amount of time to spend waiting to receive packets per method call before giving up."
        return self._recv_timeout
    @recv_timeout.setter
    def recv_timeout(self, val):
        from numbers import Real
        assert isinstance(val, Real) and val >= 0
        self._recv_timeout = float(val)
    @property
    def cmd_tries(self):
        '''The max number of times to try to send a command packet over the bobbytalk link
        for each SMBUS operation (e.g. read word, read byte, write word, etc.).
        Must be at least 1.'''
        return self._cmd_tries
    @cmd_tries.setter
    def cmd_tries(self, val):
        assert isinstance(val, int) and val >= 1
        self._cmd_tries = val
    @property
    def recv_tries(self):
        '''The max number of times to try to receive a response packet over the bobbytalk link
        for each command packet we've sent. Must be at least 1.'''
        return self._recv_tries
    @recv_tries.setter
    def recv_tries(self, val):
        assert isinstance(val, int) and val >= 1
        self._recv_tries = val
    #
    # Utility methods:
    #
    def get_bobbytalk_interface(self):
        "Returns my underlying bobbytalk packet interface."
        return self.intf
    def read_register_list(self, addr7, command_codes, data_size, use_pec):
        """SMBUS list read, all protocols {read|write} {word|byte} {PEC|no-PEC}.
        Expects the following data payload in bobbytalk packets from the demoboard:
        struct __attribute__((packed))
          {
            uint8_t noun;                                         // specifies SMBus command type.
            uint8_t verb;                                         // specifies whether read/write
            uint8_t addr7;                                        // 7 bit i2c address
            uint8_t bitmap_reg[(UINT8_MAX+1)/BITS_PER_BYTE];      // bitmap of registers read.
            uint32_t timestamp;                                   // timestamp in rolling 32 bit counter
            uint16_t data[0];                                     // data words read, number of words is as requested
            uint8_t bitmap_success[(UINT8_MAX+1)/BITS_PER_BYTE];  // bitmap of success reading registers.
          } read_list_and_data_response_struct;
        """
        if not (data_size == 16 and use_pec == True):
            return super(i2c_bobbytalk, self).read_register_list(addr7, command_codes, data_size, use_pec)
        # TODO: Implement all protocols. Only read word list with PEC is implemented right now.
        # We get here if we're reading word list with PEC.
        self.check_size(addr7, bits=x0020_SMBUS.BITS_PER_BYTE)
        for cc in command_codes:
            self.check_size(cc, bits=x0020_SMBUS.BITS_PER_BYTE)
        # DONE sanity-checking arguments
        #
        # Build bitmap representing command codes to read,
        # 1 bit for each of the possible command codes
        #
        cc_set = set(command_codes)
        sorted_cc_list = sorted(list(cc_set))
        cc_bitmap = [0 for i in range(x0020_SMBUS.MAX_NUMBER_OF_COMMAND_CODES//x0020_SMBUS.BITS_PER_BYTE)]
        for cc in range(256):
            if cc in cc_set:
                cc_bitmap[cc//x0020_SMBUS.BITS_PER_BYTE] |= (1 << (cc % 8))
        # print "cc_bitmap: {}".format(cc_bitmap)
        import struct, threading
        SMnoun = x0020_SMBUS.noun # Abbreviation.
        SMverb = x0020_SMBUS.verb # Abbreviation.
        cmdbytes = struct.pack('BBB{}B'.format(len(cc_bitmap)), SMnoun.STATELESS_WORD_LIST_PEC, SMverb.READ, addr7, *cc_bitmap)
        # print "cmdbytes to send: {}".format(" ".join((hex(ord(c)) for c in cmdbytes)))
        from PyICe.lab_core import ChannelReadException
        results_dict = { cc: ChannelReadException('listread unknown err') for cc in sorted_cc_list } # Start with results dictionary filled with ChannelReadException(s).
        for send_try in range(self.cmd_tries):
            watchdog = threading.Timer(5.0, lambda: logging.error('Watchdog expired waiting for send_packet()'))
            watchdog.start()
            send_retcode = self.intf.send_packet(src_id=self.src_id, dest_id=self.dest_id, buffer=cmdbytes)
            watchdog.cancel()
            if not send_retcode:
                continue  # Retry sending if time and retries permit.
            # time.sleep(0.01)   # For unknown reasons, with a Linduino it is crucial that this delay >= 3ms
                               # for a reply packet to be received successfully
                               # in the recv_packet() call below.
                               # The M0+ based demoboards don't appear to need this.
            for recv_try in range(self.recv_tries):
                watchdog = threading.Timer(5.0, lambda: logging.error('Watchdog expired waiting for recv_packet()'))
                watchdog.start()
                resp = self.intf.recv_packet(src_id=self.dest_id,
                                             timeout=float(self.recv_timeout)/self.recv_tries,
                                             dest_id=self.src_id)
                watchdog.cancel()
                if resp is None:
                    results_dict = { cc: ChannelReadException('listread no FW response') for cc in sorted_cc_list }
                    continue  # Received nothing this time. Retry receiving if time and retries permit.
                offset = 0
                fmt = "BBB"
                (noun, verb, rcvd_addr7) = struct.unpack_from(fmt, resp.data, offset)
                offset += struct.calcsize(fmt)
                fmt = "32B"
                rcvd_cc_bitmap = struct.unpack_from(fmt, resp.data, offset)
                offset += struct.calcsize(fmt)
                # print "rcvd_cc_bitmap: {} {}".format(rcvd_cc_bitmap, "matches sent" if rcvd_cc_bitmap == tuple(cc_bitmap) else "MISMATCHES sent") #FIXME
                if rcvd_cc_bitmap != tuple(cc_bitmap):
                    print("Rcvd pkt had different command code bitmap than what I requested.")
                    continue # Try receiving another packet if time permits.
                fmt = ">L"
                (timestamp, ) = struct.unpack_from(fmt, resp.data, offset)
                offset += struct.calcsize(fmt)
                #
                # Parse variable-length list of 2-byte big-endian words into results_dict.
                # These are the read-word-list-PEC results.
                #
                fmt = ">{}H".format(len(sorted_cc_list))
                rcvd_words_tuple = struct.unpack_from(fmt, resp.data, offset)
                results_dict = dict(list(zip(sorted_cc_list, rcvd_words_tuple)))
                offset += struct.calcsize(fmt)
                # Then grab the error bitmap.
                fmt = "32B"
                rcvd_err_bitmap = struct.unpack_from(fmt, resp.data, offset)
                offset += struct.calcsize(fmt)
                # print "Parsed {} / {} bytes".format(offset, len(resp.data))
                if (noun != SMnoun.STATELESS_WORD_LIST_PEC or verb != SMverb.READ or rcvd_addr7 != addr7):
                    if self.debug:
                        print("[Rcvd pkt wasn't the one I wanted. I got: ", end=' ')
                        if noun == SMnoun.STATELESS_WORD_LIST_PEC:
                            print("STATELESS_WORD_LIST_PEC ", end=' ')
                        else:
                            print("(noun=0x{:02x} ".format(noun), end=' ')
                        if verb == SMverb.READ:
                            print("READ ", end=' ')
                        elif verb == SMverb.WRITE:
                            print("WRITE ", end=' ')
                        else:
                            print("(verb=0x{:02x}) ".format(verb), end=' ')
                        print("addr7=0x{:02x}".format(rcvd_addr7))
                    continue  # Wrong packet received in response. Try receiving another packet
                              # if time and retries permit.
                elif rcvd_cc_bitmap != rcvd_err_bitmap:
                    # print "RD_ERR!"
                    # if "y" in raw_input("  'y' ENTER to debug, or ENTER alone to continue. ").lower():
                        # import pdb; pdb.set_trace()
                    #
                    # At least one read-word gave an error. Find out which ones
                    # and overwrite their entries in results_dict to 'READ_ERROR'.
                    #
                    for cc in sorted_cc_list:
                        if rcvd_err_bitmap[cc // 8] & (1 << (cc % 8)) == 0:
                            # import pdb; pdb.set_trace()
                            results_dict[cc] = ChannelReadException('NAK/PEC ERR')
                #
                # Populate a results list with the words that were read successfully.
                # Words which had errors will read as None.
                #
                # print "noun={:02x} verb={:02x} addr7={:02x}".format(noun, verb, rcvd_addr7)
                #
                # All checks passed. Return results dictionary
                break
            break
        return results_dict
    def read_register(self, addr7, commandCode, data_size, use_pec):
        if data_size == 16:
            if use_pec:
                return self.read_word_pec(addr7=addr7, commandCode=commandCode)
            else:
                print("UNIMPLEMENTED: twi_interface.i2c_bobbytalk.read_word() without PEC")
                return None
        elif data_size == 8:
            if use_pec:
                return self.read_byte_pec(addr7=addr7, commandCode=commandCode)
            else:
                print("UNIMPLEMENTED: twi_interface.i2c_bobbytalk.read_byte(_PEC)?()")
                return None
    def read_word_pec(self, addr7, commandCode):
        "SMBUS read word with PEC"
        self.check_size(commandCode, bits=8)
        self.check_size(addr7, bits=8)
        import struct
        SMnoun = x0020_SMBUS.noun # Abbreviation.
        SMverb = x0020_SMBUS.verb # Abbreviation.
        data16 = None  # Return this by default if the read_word_pec fails.
        cmdbytes = struct.pack('BBBB', SMnoun.WORD_PEC, SMverb.READ, addr7, commandCode)
        from PyICe.lab_core import ChannelReadException
        for send_try in range(self.cmd_tries):
            if not self.intf.send_packet(src_id=self.src_id, dest_id=self.dest_id, buffer=cmdbytes):
                continue  # Retry sending if time and retries permit.
            time.sleep(0.01)   # For unknown reasons, it is crucial that this delay >= 3ms
                               # for a reply packet to be received successfully
                               # in the recv_packet() call below.
            for recv_try in range(self.recv_tries):
                resp = self.intf.recv_packet(src_id=self.dest_id,
                                             timeout=float(self.recv_timeout)/self.recv_tries,
                                             dest_id=self.src_id)
                if resp is None:
                    data16 = ChannelReadException('read_word_pec() got no response from firmware')
                    continue  # Received nothing this time. Retry receiving if time and retries permit.
                noun, verb, rcvd_addr7, rcvd_cc, data16, rcvd_pec = struct.unpack_from(">BBBBHB", resp.data)
                if (noun != SMnoun.WORD_PEC or verb != SMverb.READ or rcvd_addr7 != addr7
                    or rcvd_cc != commandCode):
                    if self.debug:
                        print("[Rcvd pkt wasn't the one I wanted. I got: ", end=' ')
                        if noun == SMnoun.WORD_PEC:
                            print("WORD_PEC ", end=' ')
                        else:
                            print("(noun=0x{:02x} ".format(noun), end=' ')
                        if verb == SMverb.READ:
                            print("READ ", end=' ')
                        elif verb == SMverb.WRITE:
                            print("WRITE ", end=' ')
                        else:
                            print("(verb=0x{:02x}) ".format(verb), end=' ')
                        print("addr7=0x{:02x} cc=0x{:02x} data16=0x{:04x}]".format(addr7, rcvd_cc, data16))
                    continue  # Wrong packet received in response. Try receiving another packet
                              # if time and retries permit.
                calcd_pec = self.pec([self.write_addr(addr7), commandCode, self.read_addr(addr7),
                                      self.get_byte(data16,0), self.get_byte(data16,1)])
                if rcvd_pec != calcd_pec:
                    raise i2cPECError(("Expected PEC 0x{:02x} didn't match received PEC 0x{:02x}\n"
                                        ).format(calcd_pec, rcvd_pec))
                # All checks passed. Return data word.
                break
            break
        return data16
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        if data_size == 16:
            if use_pec:
                return self.write_word_pec(addr7=addr7, commandCode=commandCode, data16=data)
            else:
                print("UNIMPLEMENTED: twi_interface.i2c_bobbytalk.write_word() without PEC")
                return None
        elif data_size == 8:
            if use_pec:
                return self.write_byte_pec(addr7=addr7, commandCode=commandCode, data8=data)
            else:
                print("UNIMPLEMENTED: twi_interface.i2c_bobbytalk.{{write_byte}}()")
                return None
    def write_word_pec(self, addr7, commandCode, data16):
        "SMBUS write word with PEC"
        self.check_size(commandCode, bits=8)
        self.check_size(addr7, bits=8)
        import struct
        SMnoun = x0020_SMBUS.noun # Abbreviation.
        SMverb = x0020_SMBUS.verb # Abbreviation.
        pec = self.pec([self.write_addr(addr7), commandCode, self.get_byte(data16,0), self.get_byte(data16,1)])
        cmdbytes = struct.pack('>BBBBHB', SMnoun.WORD_PEC, SMverb.WRITE,
                               addr7, commandCode, data16, pec)
        for send_try in range(self.cmd_tries):
            if self.intf.send_packet(src_id=self.src_id, dest_id=self.dest_id, buffer=cmdbytes):
                break
        else: # for send_try ...
            raise i2cError(("Failed sending bobbytalk packet to dest_id 0x{:04x} (SMBUS module) to perform\n"
                             "  SMBUS WRITE WORD_PEC to addr7=0x{:02x}, commandCode=0x{:02x}, data16=0x{:04x}"
                             ).format(self.dest_id, addr7, commandCode, data16))
        time.sleep(0.01) # See note about this wait in read_word_pec().
        # Read the response to our write command.
        rcvd_data16 = None
        for recv_try in range(self.recv_tries):
            resp = self.intf.recv_packet(src_id=self.dest_id,
                                         timeout=float(self.recv_timeout)/self.recv_tries,
                                         dest_id=self.src_id)
            if resp is None:
                continue  # Received nothing this time. Retry receiving if time and retries permit.
            # else resp now contains our SMBUS Write Word PEC response, so parse it:
            noun, verb, rcvd_addr7, rcvd_cc, rcvd_data16, rcvd_pec = struct.unpack_from(">BBBBHB", resp.data)
            if (noun != SMnoun.WORD_PEC or verb != SMverb.WRITE or rcvd_addr7 != addr7
                or rcvd_cc != commandCode):
                if self.debug:
                    print("[Rcvd pkt wasn't the one I wanted. I got: ", end=' ')
                    if noun == SMnoun.WORD_PEC:
                        print("WORD_PEC ", end=' ')
                    else:
                        print("(noun=0x{:02x} ".format(noun), end=' ')
                    if verb == SMverb.WRITE:
                        print("WRITE ", end=' ')
                    elif verb == SMverb.READ:
                        print("READ ", end=' ')
                    else:
                        print("(verb=0x{:02x}) ".format(verb), end=' ')
                    print("addr7=0x{:02x} cc=0x{:02x} data16=0x{:04x}]".format(addr7, rcvd_cc, data16))
                continue  # Wrong packet received in response. Try receiving another packet
                          # if time and retries permit.
            calcd_pec = self.pec([self.write_addr(addr7), commandCode, self.read_addr(addr7),
                                  self.get_byte(data16,0), self.get_byte(data16,1)])
            if rcvd_pec != calcd_pec:
                raise i2cPECError(("Expected PEC 0x{:02x} didn't match received PEC 0x{:02x}\n"
                                    ).format(calcd_pec, rcvd_pec))
            # All checks passed. Return data word.
            break
        return rcvd_data16
    def read_byte_pec(self, addr7, commandCode):
        "SMBUS read byte with PEC"
        self.check_size(commandCode, bits=8)
        self.check_size(addr7, bits=8)
        import struct
        SMnoun = x0020_SMBUS.noun # Abbreviation.
        SMverb = x0020_SMBUS.verb # Abbreviation.
        data8 = None  # Return this by default if the read_byte_pec fails.
        cmdbytes = struct.pack('BBBBL', SMnoun.BYTE_PEC_V2, SMverb.READ, addr7, commandCode, 0x0001) #needs tag
        from PyICe.lab_core import ChannelReadException
        for send_try in range(self.cmd_tries):
            if not self.intf.send_packet(src_id=self.src_id, dest_id=self.dest_id, buffer=cmdbytes):
                continue  # Retry sending if time and retries permit.
            time.sleep(0.01)   # For unknown reasons, it is crucial that this delay >= 3ms
                               # for a reply packet to be received successfully
                               # in the recv_packet() call below.
            for recv_try in range(self.recv_tries):
                resp = self.intf.recv_packet(src_id=self.dest_id,
                                             timeout=float(self.recv_timeout)/self.recv_tries,
                                             dest_id=self.src_id)
                if resp is None:
                    data8 = ChannelReadException('read_byte_pec() got no response from firmware')
                    continue  # Received nothing this time. Retry receiving if time and retries permit.
                #noun, verb, rcvd_addr7, rcvd_cc, data8, rcvd_pec = struct.unpack_from(">BBBBBB", resp.data)
                noun, verb, rcvd_addr7, rcvd_cc, data8 = struct.unpack_from(">BBBBB", resp.data) #for v2, pec is checked on the firmware side
                print([noun, verb, rcvd_addr7, rcvd_cc, data8])
                if (noun != SMnoun.BYTE_PEC_V2 or verb != SMverb.READ or rcvd_addr7 != addr7
                    or rcvd_cc != commandCode):
                    if self.debug:
                        print("[Rcvd pkt wasn't the one I wanted. I got: ", end=' ')
                        if noun == SMnoun.BYTE_PEC_V2:
                            print("BYTE_PEC_V2 ", end=' ')
                        else:
                            print("(noun=0x{:02x} ".format(noun), end=' ')
                        if verb == SMverb.READ:
                            print("READ ", end=' ')
                        elif verb == SMverb.WRITE:
                            print("WRITE ", end=' ')
                        else:
                            print("(verb=0x{:02x}) ".format(verb), end=' ')
                        print("addr7=0x{:02x} cc=0x{:02x} data8=0x{:04x}]".format(addr7, rcvd_cc, data8))
                    continue  # Wrong packet received in response. Try receiving another packet
                              # if time and retries permit.
                #calcd_pec = self.pec([self.write_addr(addr7), commandCode, self.read_addr(addr7), data8])
                # if rcvd_pec != calcd_pec: #for v2, pec is checked on the firmware side
                    # raise i2cPECError(("Expected PEC 0x{:02x} didn't match received PEC 0x{:02x}\n"
                                        # ).format(calcd_pec, rcvd_pec))
                # All checks passed. Return data word.
                break
            break
        return data8
    def write_byte_pec(self, addr7, commandCode, data8):
        "SMBUS write word with PEC"
        self.check_size(commandCode, bits=8)
        self.check_size(addr7, bits=8)
        import struct
        SMnoun = x0020_SMBUS.noun # Abbreviation.
        SMverb = x0020_SMBUS.verb # Abbreviation.
        # pec = self.pec([self.write_addr(addr7), commandCode, data8])
        # cmdbytes = struct.pack('>BBBBBB', SMnoun.BYTE_PEC_V2, SMverb.WRITE, addr7, commandCode, data8, pec)
        cmdbytes = struct.pack('>BBBBB', SMnoun.BYTE_PEC_V2, SMverb.WRITE, addr7, commandCode, data8)
        for send_try in range(self.cmd_tries):
            if self.intf.send_packet(src_id=self.src_id, dest_id=self.dest_id, buffer=cmdbytes):
                break
        else: # for send_try ...
            raise i2cError(("Failed sending bobbytalk packet to dest_id 0x{:04x} (SMBUS module) to perform\n"
                             "  SMBUS WRITE BYTE_PEC_V2 to addr7=0x{:02x}, commandCode=0x{:02x}, data8=0x{:04x}"
                             ).format(self.dest_id, addr7, commandCode, data8))
        time.sleep(0.01) # See note about this wait in read_word_pec().
        # Read the response to our write command.
        rcvd_data8 = None
        for recv_try in range(self.recv_tries):
            resp = self.intf.recv_packet(src_id=self.dest_id,
                                         timeout=float(self.recv_timeout)/self.recv_tries,
                                         dest_id=self.src_id)
            if resp is None:
                continue  # Received nothing this time. Retry receiving if time and retries permit.
            # else resp now contains our SMBUS Write Word PEC response, so parse it:
            # noun, verb, rcvd_addr7, rcvd_cc, rcvd_data8, rcvd_pec = struct.unpack_from(">BBBBBB", resp.data)
            noun, verb, rcvd_addr7, rcvd_cc, rcvd_data8 = struct.unpack_from(">BBBBB", resp.data)
            if (noun != SMnoun.BYTE_PEC_V2 or verb != SMverb.WRITE or rcvd_addr7 != addr7
                or rcvd_cc != commandCode):
                if self.debug:
                    print("[Rcvd pkt wasn't the one I wanted. I got: ", end=' ')
                    if noun == SMnoun.BYTE_PEC_V2:
                        print("BYTE_PEC_V2 ", end=' ')
                    else:
                        print("(noun=0x{:02x} ".format(noun), end=' ')
                    if verb == SMverb.WRITE:
                        print("WRITE ", end=' ')
                    elif verb == SMverb.READ:
                        print("READ ", end=' ')
                    else:
                        print("(verb=0x{:02x}) ".format(verb), end=' ')
                    print("addr7=0x{:02x} cc=0x{:02x} data8=0x{:04x}]".format(addr7, rcvd_cc, data8))
                continue  # Wrong packet received in response. Try receiving another packet
                          # if time and retries permit.
            # calcd_pec = self.pec([self.write_addr(addr7), commandCode, self.read_addr(addr7),  #for v2, pec is checked on the firmware side
                                  # data8])
            # if rcvd_pec != calcd_pec:
                # raise i2cPECError(("Expected PEC 0x{:02x} didn't match received PEC 0x{:02x}\n"
                                    # ).format(calcd_pec, rcvd_pec))
            # All checks passed. Return data word.
            break
        print(f'received: {rcvd_data8}')
        return rcvd_data8
    #
    # The following methods must exist to satisfy our twi_interface abstract base class,
    # but at the time of writing, 7/26/2017, we don't yet have i2c primitives implemented
    # on the firmware side.
    #
    def start(self):
        '''UNIMPLEMENTED - I2C Start primitive - Falling SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    def stop(self):
        '''UNIMPLEMENTED - I2C Stop primitive - Rising SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    def write(self,data8):
        '''UNIMPLEMENTED - I2C primitive to transmit 8 bits plus 9th acknowledge clock.  Returns True or False to indicate slave acknowledge'''
        raise i2cUnimplementedError()
    def read_ack(self):
        '''UNIMPLEMENTED - I2C primitive to read 8 bits from slave transmitter  and assert SDA during 9th acknowledge clock.  Returns 8 bit data'''
        raise i2cUnimplementedError()
    def read_nack(self):
        '''UNIMPLEMENTED - I2C primitive to read 8 bits from slave transmitter  and release SDA during 9th acknowledge clock to request end of transmission.  Returns 8 bit data'''
        raise i2cUnimplementedError()
class i2c_labcomm(twi_interface):
    def __init__(self, raw_serial_interface):
        self.interface = raw_serial_interface
        # Straight Through SMBus Transactions and Alternate Commands
        # ---------------------------------------------------------------
        self.SMBUS_QUICK_COMAND         = 1 # The R/W bit is the data
        self.SMBUS_SEND_BYTE            = 2 # Byte only
        self.SMBUS_RECEIVE_BYTE         = 3 # Byte only
        self.SMBUS_WRITE_REGISTER       = 4 # Byte and Word, With and without PEC
        self.SMBUS_READ_REGISTER        = 5 # Byte and Word, With and without PEC
        self.SMBUS_PROCESS_CALL         = 6 # With and without PEC
        self.SMBUS_BLOCK_WRITE          = 7 # With and without PEC
        self.SMBUS_BLOCK_READ           = 8 # With and without PEC
        self.SET_REGISTER_LIST          = 21
        self.READ_REGISTER_LIST         = 22
        self.ENABLE_STREAM_MODE         = 23
        self.DISABLE_STREAM_MODE        = 24
        self.WRITE_REGISTER_LIST        = 25
        self.SET_REG_LIST_AND_READ_LIST = 26
        self.SET_REG_LIST_AND_STREAM    = 27
        # ---------------------------------------------------------------
        # Payload Byte Positions
        # [TRANSACTION TYPE or COMMAND][ADDR7][COMMAND CODE][USE PEC][DATA SIZE(Bits)][REG 1][REG 2][REG 3]...
        self.TRANSACTION_TYPE   = 0 # See table above
        self.ADDR7              = 1 # Target 7-bit address
        self.COMMAND_CODE       = 2 # Command code
        self.USE_PEC            = 3 # Expect 1 or 0
        self.DATA_SIZE          = 4 # Should be 8 or 16
        self.START_OF_DATA_IN   = 5 # Data goes from here to remainder of the payload
        # ---------------------------------------------------------------
        self.ERROR_CODE_SMBUS_SUCCESS           = 0
        self.ERROR_CODE_SMBUS_NACK_ON_ADDRESS   = 1
        self.ERROR_CODE_SMBUS_NACK_ON_DATA      = 2
        self.ERROR_CODE_SMBUS_PEC_VALUE_ERROR   = 4
        self.ERROR_CODE_SMBUS_SMBUS_TIMEOUT     = 8
        self.ERROR_CODE_SMBUS_BUFFER_OVERFLOW   = 16
        self.ERROR_CODE_SMBUS_UNKNOWN_ERROR     = 32 # Catch all, includes timeout.
    def raise_twi_error(self, code, command_code):
        if code==self.ERROR_CODE_SMBUS_SUCCESS:             pass
        if code & self.ERROR_CODE_SMBUS_NACK_ON_ADDRESS:    raise i2cWriteAddressAcknowledgeError(f"Labcomm had a NACK on address error at command code: {command_code}.")
        if code & self.ERROR_CODE_SMBUS_NACK_ON_DATA:       raise i2cDataLowAcknowledgeError(f"Labcomm had a NACK on Data error at command code: {command_code}.")
        if code & self.ERROR_CODE_SMBUS_PEC_VALUE_ERROR:    raise i2cPECError(f"Labcomm had a PEC Value error at command code: {command_code}.")
        if code & self.ERROR_CODE_SMBUS_SMBUS_TIMEOUT:      raise i2cIOError(f"Labcomm had an a timeout error command code: {command_code}.")
        if code & self.ERROR_CODE_SMBUS_BUFFER_OVERFLOW:    raise i2cIOError(f"Labcomm had an firmware buffer overflow error at command code: {command_code}.")
        if code & self.ERROR_CODE_SMBUS_UNKNOWN_ERROR:      raise i2cIOError(f"Labcomm had an unknown error at command code: {command_code}.")
    def set_source_id(self, src_id):
        self.src_id = src_id
    def set_destination_id(self, dest_id):
        self.dest_id = dest_id
    def bytes_grouper(self, iterable, size):
        '''will return either:
                                [command_code, [status, Lo-byte]]
                                [command_code, [status, Lo-byte, Hi-byte]]
        '''
        args = [iter(iterable)] * size
        return list(itertools.zip_longest(fillvalue=None, *args))
    def read_register_list(self, addr7, command_codes, data_size, use_pec):
        payload  = int.to_bytes(self.SET_REG_LIST_AND_READ_LIST,length=1, byteorder="big")  # Transaction hint for client
        payload += int.to_bytes(addr7,                          length=1, byteorder="big")
        payload += int.to_bytes(0,                              length=1, byteorder="big")  # Placeholder COMMAND_CODE not used on list read
        payload += int.to_bytes(use_pec,                        length=1, byteorder="big")
        payload += int.to_bytes(data_size,                      length=1, byteorder="big")  # Will be 8 or 16
        for command_code in command_codes:                                                  # Use the extensible data field for the list
            payload += int.to_bytes(command_code,               length=1, byteorder="big")
        self.interface.write_raw(self.talker.assemble(source=self.src_id, destination=self.dest_id, payload=payload.decode(encoding=STR_ENCODING)))
        packet = self.parser.read_message()
        #┌────────┬──────────┬───────────┬┬────────┬──────────┬───────────┬┬─────┐
        #│ STATUS │ DATA LOW │[DATA HIGH]││ STATUS │ DATA LOW │[DATA HIGH]││ ... │
        #└────────┴──────────┴───────────┴┴────────┴──────────┴───────────┴┴─────┘
        values = []
        for group in zip(command_codes, self.bytes_grouper(packet["payload"], size=2 if data_size==8 else 3)):
            data = group[1][1]                  # Grab the Lo-byte
            if data_size==16:
                data += group[1][2] * 256       # Grab the Hi-byte for Words
            values.append(data)
            self.raise_twi_error(code=group[1][0], command_code=group[0])
        return dict(list(zip(command_codes, values)))
    def write_register(self, addr7, commandCode, data, data_size, use_pec):
        payload  = int.to_bytes(self.SMBUS_WRITE_REGISTER,  length=1, byteorder="big") # Transaction hint for client
        payload += int.to_bytes(addr7,                      length=1, byteorder="big")
        payload += int.to_bytes(commandCode,                length=1, byteorder="big")
        payload += int.to_bytes(use_pec,                    length=1, byteorder="big")
        payload += int.to_bytes(data_size,                  length=1, byteorder="big") # Will be 8 or 16
        payload += int.to_bytes(data&0xFF,                  length=1, byteorder="big") # Lo Byte
        if data_size==16:
            payload += int.to_bytes(data>>8,                length=1, byteorder="big") # Hi Byte assuming WORD mode
        self.interface.write_raw(self.talker.assemble(source=self.src_id, destination=self.dest_id, payload=payload.decode(encoding=STR_ENCODING)))
        packet = self.parser.read_message()
        self.raise_twi_error(code=packet["payload"][0], command_code=commandCode)
    def read_register(self, addr7, commandCode, data_size, use_pec):
        payload  = int.to_bytes(self.SMBUS_READ_REGISTER,   length=1, byteorder="big") # Transaction hint for client
        payload += int.to_bytes(addr7,                      length=1, byteorder="big")
        payload += int.to_bytes(commandCode,                length=1, byteorder="big")
        payload += int.to_bytes(use_pec,                    length=1, byteorder="big")
        payload += int.to_bytes(data_size,                  length=1, byteorder="big") # Will be 8 or 16
        self.interface.write_raw(self.talker.assemble(source=self.src_id, destination=self.dest_id, payload=payload.decode(encoding=STR_ENCODING)))
        packet = self.parser.read_message()
        self.raise_twi_error(code=packet["payload"][0], command_code=commandCode)
        return (packet["payload"][2] * 256 if data_size==16 else 0) + packet["payload"][1]
    def receive_byte(self, addr7, use_pec=False):  #TODO PyICe is broken here, needs to support receive_byte with Pec
        payload  = int.to_bytes(self.SMBUS_RECEIVE_BYTE,    length=1, byteorder="big") # Transaction hint for client
        payload += int.to_bytes(addr7,                      length=1, byteorder="big")
        payload += int.to_bytes(0,                          length=1, byteorder="big") # Field filler, no command code in Receive byte
        payload += int.to_bytes(use_pec,                    length=1, byteorder="big")
        payload += int.to_bytes(8,                          length=1, byteorder="big") # One byte is 8 bits
        self.interface.write_raw(self.talker.assemble(source=self.src_id, destination=self.dest_id, payload=payload.decode(encoding=STR_ENCODING)))
        packet = self.parser.read_message()
        self.raise_twi_error(code=packet["payload"][0], command_code=None)
        return packet["payload"][1]
    def read_word_pec(self, addr7, commandCode):
        print("read_word_pec in twi_interface unimplemented.")
        # return data16
    def write_word_pec(self, addr7, commandCode, data16):
        print("write_word_pec in twi_interface unimplemented.")
    def read_byte_pec(self, addr7, commandCode):
        print("read_byte_pec in twi_interface unimplemented.")
        # return data8
    def write_byte_pec(self, addr7, commandCode, data8):
        print("write_byte_pec in twi_interface unimplemented.")
    def start(self):
        '''UNIMPLEMENTED - I2C Start primitive - Falling SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    def stop(self):
        '''UNIMPLEMENTED - I2C Stop primitive - Rising SDA with SCL high.  Returns True or False to indicate successful arbitration'''
        raise i2cUnimplementedError()
    def write(self,data8):
        '''UNIMPLEMENTED - I2C primitive to transmit 8 bits plus 9th acknowledge clock.  Returns True or False to indicate slave acknowledge'''
        raise i2cUnimplementedError()
    def read_ack(self):
        '''UNIMPLEMENTED - I2C primitive to read 8 bits from slave transmitter  and assert SDA during 9th acknowledge clock.  Returns 8 bit data'''
        raise i2cUnimplementedError()
    def read_nack(self):
        '''UNIMPLEMENTED - I2C primitive to read 8 bits from slave transmitter  and release SDA during 9th acknowledge clock to request end of transmission.  Returns 8 bit data'''
        raise i2cUnimplementedError()
        # TODO ensure packet is intended for us and not unsynched ????!!!!!

class mem_dict(twi_interface):
    def __init__(self, data_source=None):
        self.set_data_source(data_source)
    def set_data_source(self, data):
        self._data_dict = data
    def read_register(self, addr7, commandCode, data_size, use_pec):
        # Most everything ignored
        # Interface unchanged to be able to use TWI Instrument bit field decoding.
        assert self._data_dict is not None, 'Must set input data source.'
        try:
            return self._data_dict[commandCode]
        except KeyError as e:
            print(f'Data missing for commandCode {e}')
            return None
    def read_ack(self):
        raise Exception('Unimplemented')
    def read_nack(self):
        raise Exception('Unimplemented')
    def start(self):
        raise Exception('Unimplemented')
    def stop(self):
        raise Exception('Unimplemented')
    def write(self):
        raise Exception('Unimplemented')
class i2cError(Exception):
    '''I2C Error Superclass - Don't raise this exception.  Use more specific subclass.'''
    def __init__(self, value=None):
        self.value = value
    def __str__(self):
        return repr(self.value)
class i2cUnimplementedError(i2cError, NotImplementedError):
    '''Feature currently unimplemented.  Write it if you want it!'''
    pass
class i2cMasterError(i2cError):
    '''Unexpected response from I2C interface device,
    possibly caused by dropped USB packets, serial error,
    unpowered master, or other 'computer' problems.
    Excludes communication problems with a device on the two-wire bus.'''
    pass
class i2cStartStopError(i2cError):
    '''Failed to assert Start of Stop signals - not supported by all hardware'''
    pass
class i2cAcknowledgeError(i2cError):
    '''Got expected responses from I2C master device, but slave devices not acknowledging address or subsequent data bytes.'''
    pass
class i2cAddressAcknowledgeError(i2cAcknowledgeError):
    '''Got expected responses from I2C master device, but slave device not acknowledging address.'''
    pass
class i2cWriteAddressAcknowledgeError(i2cAddressAcknowledgeError):
    '''Got expected responses from I2C master device, but slave device not acknowledging write address.'''
    pass
class i2cReadAddressAcknowledgeError(i2cAddressAcknowledgeError):
    '''Got expected responses from I2C master device, but slave device not acknowledging read address.'''
    pass
class i2cCommandCodeAcknowledgeError(i2cAcknowledgeError):
    '''Got expected responses from I2C master device, but slave device not acknowledging command code.'''
    pass
class i2cDataAcknowledgeError(i2cAcknowledgeError):
    '''Got expected responses from I2C master device and slave address, but slave devices not acknowledging subsequent data bytes.'''
    pass
class i2cDataLowAcknowledgeError(i2cDataAcknowledgeError):
    '''Got expected responses from I2C master device and slave address, but slave devices not acknowledging low data byte.'''
    pass
class i2cDataHighAcknowledgeError(i2cDataAcknowledgeError):
    '''Got expected responses from I2C master device and slave address, but slave devices not acknowledging high data byte.'''
    pass
class i2cDataPECAcknowledgeError(i2cDataAcknowledgeError):
    '''Got expected responses from I2C master device and slave address, but slave devices not acknowledging PEC data byte.'''
    pass
class i2cPECError(i2cError):
    '''Got expected responses from I2C master and slave acknowledging all bytes, but failed to reconcile SMBus packet error check.'''
    pass
class i2cIOError(i2cError):
    '''I2C Bus communication failure, not otherwise specified.'''
    pass
