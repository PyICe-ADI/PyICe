class TWI():
    '''
    This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    It's meant to feed into a pattern generator instrument such as the old HP8110a dual pattern generator or its modern equivalent.
    It has two channels, one for the the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    '''
    def __init__(self, time_step):
        self.time_step = time_step
        self.tbuf = 1300e-9
        self.thd_sta = 600e-9
        self.tlow = 1300e-9
        self.thd_dat = 0e-9     # Allowed to be 0ns to 900ns
        self.thigh = 600e-9
        self.tsu_dat = 100e-9
        self.tsu_sta = 600e-9   # Restart
        self.tsu_sto = 600e-9
        self.tsp = 50e-9
        self.tlead = 1.8e-9
        self.ttrail = 1.8e-9
        self.frequency = 1 / ( self.tlead + self.thigh + self.tlow + self.ttrail)
        self.SCL = []
        self.SDA = []
        self.STB = []

    def biterator(self, byte):
        '''Iterates over the bits of an integer from left to right.'''
        length = byte.bit_length()
        for index in range(length):
            yield 1 if byte << index & 1 << length-1 == 1 << length-1 else 0

    def add_lead_in(self, SDA, SCL, STROBE):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)
        self.STB.extend(STROBE)
        
    def add_lead_out(self, SDA, SCL, STROBE):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)
        self.STB.extend(STROBE)

    def add_start(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend([0])
        self.STB.extend([strobe])
        self.dwell(self.thd_sta)
        self.SCL.extend([0])
        self.SDA.extend([0])
        self.STB.extend([0])
        self.dwell(self.tlow - self.tsu_dat)

    def add_stop(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend([1])
        self.STB.extend([strobe])
        self.dwell(self.tbuf)

    def add_data_to_low(self, strobe):
        self.SCL.extend(self.SCL[-1:])
        self.SDA.extend([0])
        self.STB.extend([0])
        self.dwell(self.tlow)

    def add_clock_to_high(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend(self.SDA[-1:])
        self.STB.extend([0])
        self.dwell(self.tsu_sto)

    def add_data_bit(self, d, strobe):
        self.SCL.extend([0])
        self.SDA.extend([d])
        self.STB.extend(self.STB[-1:])
        self.dwell(self.tsu_dat)
        self.SCL.extend([1])
        self.SDA.extend([d])
        self.STB.extend([strobe])
        self.dwell(self.thigh)
        self.SCL.extend([0])
        self.SDA.extend([d])
        self.STB.extend([0])
        self.dwell(self.thd_dat)

    def add_ack_bit(self, strobe):
        self.dwell(self.tlow)
        self.add_data_bit(1, strobe=strobe)

    def add_byte(self, byte, strobes):
        '''
        For each bit in strobes, a strobe is added.
        Bits are [0..8] where 0 is the MSB of the data, 7 is the LSB of the data and 8 is the ACK.
        '''
        for bit in self.biterator(byte):
            self.dwell(self.tlow)
            self.add_data_bit(d = bit, strobe = 1 if strobes[bit] else 0)
        self.add_ack_bit(strobe = 1 if strobes[8] else 0)

    def add_addr7(self, addr7, R_Wb, strobes):
        self.add_byte(byte=addr7*2 + R_Wb, strobes=strobes)

    def dwell(self, tdwell):
        cycles = round(tdwell / self.time_step)
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)

    def get_SDA(self):
        return self.SDA
        
    def get_SCL(self):
        return self.SCL
        
    def get_STB(self):
        return self.STB
        
    def get_ALL(self, SCL_channel, SDA_channel, STB_channel):
        '''
        Build up the compound record of instrument Channels 1, 2 and 3 (Strobe).
        On the HP8110a, for example, the two output channels and the Strobe channel are binarily weighted so it takes values of 0-7 for 3 bits.
        '''
        assert len(self.SDA) == len(self.SCL), "TWI Generator: SDA and SCL records somehow not equal length!"
        assert len(self.SCL) == len(self.STB), "TWI Generator: SCL and STB records somehow not equal length!"
        values = []
        for position in range(len(self.SCL)):
            values.append(self.SCL[position] * 2**(SCL_channel-1) + self.SDA[position] * 2**(SDA_channel-1) + self.STB[position] * 2**(STB_channel-1))
        return values