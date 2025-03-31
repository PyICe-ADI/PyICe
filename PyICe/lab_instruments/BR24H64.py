from ..lab_core import *
from PyICe.lab_utils.banners import print_banner

class BR24H64(instrument):
    '''Rhom 64kb (8kbyte) EEPROM
    https://fscdn.rohm.com/en/products/databook/datasheet/ic/memory/eeprom/br24h64xxx-5ac-e.pdf'''

    # Proposed Dictionary Like Structure
    # https://en.wikipedia.org/wiki/C0_and_C1_control_codes
    # [STX] (0x02) ..........	Start of an Entry
    # KEY	.................   Key Text (ASCII Only)
    # .......................
    # [US] (0x1F) ...........   Key/Value Delimiter
    # VALUE .................   Value Text (ASCII Only)
    # .......................
    # [ETX] (0x03) ..........   End of an Entry
    # [SUB] (0x19) ..........   End of All Entries (End of Medium)
    
    STX = b'\x02'     # Start of Text       (Start of a record or entry)
    ETX = b'\x03'     # End of Text         (End of a record or entry)
    US =  b'\x1F'     # Key:Value Delimiter
    EOM = b'\x19'     # End of All Entries  (End of Media)

    def __init__(self, interface_twi, addr7):
        '''interface_twi is a interface_twi
        addr7 is the 7-bit I2C address of the BR24H64 set by pinstrapping.
        Choose addr7 from 0x50 - 0x57 only.
        Device uses 16bit internal addressing for 8 bit memory so had to play some protocol games.
        '''
        instrument.__init__(self, f'64KBit, I²C BUS, High Speed Write Cycle, High Endurance, Serial EEPROM at {hex(addr7)}')
        self._base_name = 'BR24H64'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        if addr7 not in range(0x50, 0x58):
            raise ValueError(f"\n\n\nBR24H64 only supports addresses 0x50 - 0x57, What makes you think it would respond to address: 0x{hex(addr7)}?")
        self.addr7 = addr7
        self.tries = 3

    def _write_location(self, location, data):
        tries = self.tries
        if location < 0 or location >= 8191:
            raise Exception(f"\n*** BR24H64 EEPROM write transaction to device at ADDR7:{hex(self.addr7)} skipped. \n*** Attempt to write address {location} which is outside physical media [0..8191].\n")
            return
        if data < 0 or data > 255:
            raise Exception(f"\n*** BR24H64 EEPROM write transaction to device at ADDR7:{hex(self.addr7)} skipped. \n*** Attempt to write the value {data} which is outside the range [0..255].\n")
            return
        while tries:
            try:
                tries -= 1
                # time.sleep(0.0035) # Max write delay value from the datasheet - Doesn't appear to be needed ???
                self.twi.write_register(addr7=self.addr7, commandCode=location >> 8, data=(location & 0xff) + (data << 8), data_size=16, use_pec=False)
                return
            except Exception as e:
                print(e)
                self.twi.resync_communication()
                if not tries:
                    raise e
                    
    def _read_location(self, location):
        tries = self.tries
        while tries:
            try:
                tries -= 1
                self.twi.write_register(addr7=self.addr7, commandCode=location >> 8, data=(location & 0x00ff), data_size=8, use_pec=False)
                return self.twi.receive_byte(addr7=self.addr7)
            except Exception as e:
                print(e)
                self.twi.resync_communication()
                if not tries:
                    raise e
                    
    def write_location(self, location, value):
        self._write_location(location, value)
        
    def read_location(self, location):
        return self._read_location(location)

    def read_dictionary(self, verbose=False):
        file = b''
        if verbose:
            print_banner(f"Reading BR24H64 EEPROM media from device at ADDR7:{hex(self.addr7)}.", "Please Wait..")
        for location in range(8193):
            if location > 8191:
                raise Exception(f"\n*** Warning: BR24H64 EEPROM at ADDR7:{hex(self.addr7)} reached end of available media with no end of record found.\nReturning empty dictionary.")
                return {}
            byte = self.read_location(location)
            if bytes([byte]) == self.EOM:
                break                       # Done! Outa here.
            file += bytes([byte])
        data = {}
        key = ""
        value = ""
        state = None
        for character in file:
            character = bytes([character]) # for-loop returns integers instead of bytestrings for some reason
            if character == self.STX:
                state = "KEY"
            elif character == self.US:
                state = "VALUE"
            elif character == self.ETX:
                data[key]=value
                key = ""
                value = ""
                state = None
            else:                               # It presumably must be an ASCII character
                if state == "KEY":
                    key += character.decode("ASCII")
                if state == "VALUE":
                    value += character.decode("ASCII")
        if verbose:
            print_banner(f"BR24H64 EEPROM at ADDR7:{hex(self.addr7)} reading complete.")
        return data
        
    def write_dictionary(self, data_dict, verbose=False):
        file = b''
        for key in data_dict:
            file += self.STX + key.encode("ASCII") + self.US + data_dict[key].encode("ASCII") + self.ETX
        file += self.EOM # End of Medium
        if len(file) >= 8191:
            raise Exception(f"\n*** BR24H64 EEPROM at ADDR7:{hex(self.addr7)} write transaction aborted before starting.\n*** Record too long, would overrun available space.\n")
            return
        for byte in file:
            if byte < 0 or byte > 255:
                raise Exception(f"\n*** BR24H64 EEPROM at ADDR7:{hex(self.addr7)} write transaction aborted before starting.\n*** Record contains at least one value outside the range [0..255].\n")
                return
        if verbose:
            print_banner(f"Writing BR24H64 EEPROM media at ADDR7:{hex(self.addr7)}.","Please Wait...")
        location = 0
        for byte in file:
            self.write_location(location, byte)
            location += 1
