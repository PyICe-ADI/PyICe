class TWI():
    '''
    This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    It's meant to feed into a pattern generator instrument such as the old HP8110a dual pattern generator or its modern equivalent.
    It has two channels, one for the the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    '''
    def __init__(self, time_step, max_record_size=4096):
        self.max_record_size = max_record_size
        self.time_step = time_step
        self.init_pattern()

    def biterator(self, byte):
        '''Iterates over the bits of an integer from left to right.'''
        length = byte.bit_length()
        for index in range(length):
            yield 1 if byte << index & 1 << length-1 == 1 << length-1 else 0
            
    def init_pattern(self):
        self.SCL = []
        self.SDA = []
        self.STB = []

    def add_lead_in(self, SDA, SCL, STROBE):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)
        self.STB.extend(STROBE)
        self.audit_pattern()
        
    def add_lead_out(self, SDA, SCL, STROBE):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)
        self.STB.extend(STROBE)
        self.audit_pattern()

    def add_start(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend([0])
        self.STB.extend([strobe])
        self.dwell(self.thd_sta - self.time_step)
        self.SCL.extend([0])
        self.SDA.extend([0])
        self.STB.extend([0])
        self.dwell(self.tlow - self.tsu_dat - self.time_step)
        self.audit_pattern()

    def add_stop(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend([1])
        self.STB.extend([strobe])
        self.dwell(self.tbuf - self.time_step)
        self.audit_pattern()

    def add_data_to_low(self, strobe):
        self.SCL.extend(self.SCL[-1:])
        self.SDA.extend([0])
        self.STB.extend([0])
        self.dwell(self.tlow - self.time_step)
        self.audit_pattern()

    def add_clock_to_high(self, strobe):
        self.SCL.extend([1])
        self.SDA.extend(self.SDA[-1:])
        self.STB.extend([0])
        self.dwell(self.tsu_sto - self.time_step)
        self.audit_pattern()

    def add_data_bit(self, d, strobe):
        self.dwell(self.tlow)
        self.SCL.extend([0])                                        # Clock low
        self.SDA.extend([d])                                        # Data to d
        self.STB.extend(self.STB[-1:])                              # Hold Strobe
        self.dwell(self.tsu_dat - self.time_step)                   # Wait data setup time
        self.SCL.extend([1])                                        # Clock high
        self.SDA.extend([d])                                        # Hold data at d
        self.STB.extend([strobe])                                   # Assert strobe
        thd_dat_steps = round(self.thd_dat / self.time_step)
        if thd_dat_steps == 0:                                      # Request is zero hold time
            self.dwell(self.thigh - self.time_step)                 # Wait clock high time
            self.SCL.extend([0])                                    # Clock low
            self.SDA.extend([0])                                    # Make this port RZ (Return to Zero), One's will get hammered.
            self.STB.extend([0])                                    # Strobe low
        elif thd_dat_steps > 0:                                     # Positive hold time
            self.dwell(self.thigh - self.time_step)                 # Wait clock high time
            self.SCL.extend([0])                                    # Clock low
            self.SDA.extend([d])                                    # Hold data at d
            self.STB.extend([0])                                    # Strobe low
            self.dwell(self.thd_dat - self.time_step)               # Wait data hold time
        else: # Must be negative hold time                          # Negative hold time
            self.dwell(self.thigh + self.thd_dat - self.time_step)  # Wait clock high time minus negative hold time
            self.SCL.extend([1])                                    # Hold clock high
            self.SDA.extend([0])                                    # Make this port RZ (Return to Zero), One's will get hammered.
            self.STB.extend([strobe])                               # Hold Strobe as is
            self.dwell(-self.thd_dat - self.time_step)              # Wait out what would have been the thigh time
            self.SCL.extend([0])                                    # Clock low
            self.SDA.extend([0])                                    # Make this port RZ (Return to Zero), One's will get hammered.
            self.STB.extend([0])                                    # Strobe low
        self.audit_pattern()

    def add_ack_bit(self, strobe):
        self.add_data_bit(1, strobe=strobe)

    def add_byte(self, byte, strobes):
        '''
        For each bit in strobes, a strobe is added.
        Bits are [0..8] where 0 is the MSB of the data, 7 is the LSB of the data and 8 is the ACK.
        '''
        for bit in self.biterator(byte):
            self.add_data_bit(d = bit, strobe = 1 if strobes[bit] else 0)
        self.add_ack_bit(strobe = 1 if strobes[8] else 0)

    def add_addr7(self, addr7, R_Wb, strobes):
        self.add_byte(byte=addr7*2 + R_Wb, strobes=strobes)

    def dwell(self, tdwell):
        cycles = round(tdwell / self.time_step)
        assert cycles >= 0, f"TWI Pattern Generator: tdwell of {tdwell} results in a negative time slice addition, not acheivable."
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)
        self.audit_pattern()
        
    def pad_out(self):
        cycles = 4096 - len(self.SCL)
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)
        self.audit_pattern()

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
        self.audit_pattern()
        values = []
        for position in range(len(self.SCL)):
            values.append(self.SCL[position] * 2**(SCL_channel-1) + self.SDA[position] * 2**(SDA_channel-1) + self.STB[position] * 2**(STB_channel-1))
        return values
        
    def audit_pattern(self):
        assert len(self.SDA) == len(self.SCL), "TWI Pattern Generator: SDA and SCL records unequal length!"
        assert len(self.SCL) == len(self.STB), "TWI Pattern Generator: SCL and STB records unequal length!"
        assert len(self.SCL) <= self.max_record_size, f"TWI Pattern Generator: Record size of {len(self.SCL)} exceeds max record size of {self.max_record_size}!"