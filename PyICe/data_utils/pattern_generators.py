class TWI():
    '''
    This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    It's meant to feed into a pattern generator instrument such as the old HP8110a dual pattern generator or its modern equivalent.
    It has two channels, one for the the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    '''
    def __init__(self, time_step, max_record_size=4096):
        self.max_record_size = max_record_size
        self.time_step = time_step

    def biterator(self, byte):
        '''Iterates over the bits of an integer from left to right.'''
        length = byte.bit_length()
        for index in range(length):
            yield 1 if byte << index & 1 << length-1 == 1 << length-1 else 0
            
    def init_pattern(self):
        self.SCL = []
        self.SDA = []
        self.STB = []
        self.tbuf    = self.quantize(self.tbuf)
        self.thd_sta = self.quantize(self.thd_sta)
        self.tlow    = self.quantize(self.tlow)
        self.thd_dat = self.quantize(self.thd_dat)
        self.thigh   = self.quantize(self.thigh)
        self.tsu_dat = self.quantize(self.tsu_dat)
        self.tsu_sta = self.quantize(self.tsu_sta)
        self.tsu_sto = self.quantize(self.tsu_sto)
        self.tsp_SCL_hi = self.quantize(self.tsp_SCL_hi)
        self.tsp_SCL_lo = self.quantize(self.tsp_SCL_lo)
        self.tsp_SDA_hi = self.quantize(self.tsp_SDA_hi)
        self.tsp_SDA_lo = self.quantize(self.tsp_SDA_lo)

    def update(self, SDA, SCL, STB, dwell):
        self.SCL.extend([SCL])
        self.SDA.extend([SDA])
        if STB == "HOLD":
            self.STB.extend(self.STB[-1:])
        else:
            self.STB.extend([STB])
        self.dwell(dwell)
        self.audit_pattern()

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
        
    def quantize(self, time):
        return round(time / self.time_step) * self.time_step

    def add_data_bit(self, d, strobe):
        '''
        The data bit cycle starts by dwelling low for TLOW.
        Then it SCL low.
        Data is simultaneously transitioned to its new value.
        It then dwells with SCL low and data at 'd' for T_SU_DAT (minus one time slice to account for the first one used as a transition).
        After T_SU_DAT, SCL goes high and data remains at 'd'.
        What happens next depends on the requested hold time.
        If the requested hold time is zero, it dwells for thigh and then sets SCL and SDA low together at next time slice.
        If the requested hold time is positive, it dwells for the high time and then brings SCL low while leaving SDA as is, whereupon it then dwells for the hold time T_HD_DAT.
        If the requested hold time is negative, it dwells for the high time minus the (negative) hold time, sets SCL high and SDA low and then dwells for the remainder of the high time whereupon is sets SDA and SCL low.

        |                                                                  |
        |     __               _____________________________               |
    SCL |    |  |             |                             |              |
        |____|  |_____________|                             |______________|
        |                     |                             |              |
        |              ____________________________________________________|
    SDA |             |       |             D2              |              | RZ
        |_____________|____________________________________________________|_
        |             |                                     |              |
        |             |<-TSU->|                             |<--- THD ---->|
        |             |       |                             |              |
        |<----- TLOW (A) ---->|<--------- THIGH ----------->|<- TLOW (B) ->|
        |             |       |                             |              |
        |•••••••••••••█•••••••█•••••••••••••••••••••••••••••█••••••••••••••█  <------ █ (Blocks) Denote where changes occur, • (Dots) denote time slices
        '''
        thd_dat_steps = round(self.thd_dat / self.time_step)
        
        if  thd_dat_steps > 0:                                                                  # Positive hold time
            lead_in = self.quantize((self.tlow - self.tsu_dat - self.tsp_SCL_hi) / 2) - self.time_step
            self.dwell(lead_in - self.time_step)
            if self.tsp_SCL_hi > 0:
                self.update(SCL=1, SDA=0, STB="HOLD", dwell=self.tsp_SCL_hi-self.time_step)
            self.update(SCL=0, SDA=0, STB="HOLD", dwell=self.quantize((self.tlow-self.tsu_dat-self.thd_dat-self.tsp_SCL_hi)) - lead_in - self.time_step)
            self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)            # Change SDA to d, SCL stays low, dwell until time to raise SCL
            self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh-self.time_step)              # Bring SCL high, data holds at d, maybe assert STROBE
            self.update(SCL=0, SDA=d, STB=0, dwell=self.thd_dat-self.time_step)                 # Clock low, data stays put
            self.update(SCL=0, SDA=0, STB=0, dwell=0)                                           # Clock low, make this port RZ (Return to Zero), One's will get hammered, STROBE back low
        elif thd_dat_steps == 0:                                                                # Request is zero hold time
            self.dwell(self.tlow - self.tsu_dat - self.time_step)                               # Dwell until time one tic short of time to change the data
            self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)            # Change SDA to data, SCL stays low, wait one tic short of data setup time
            self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh-self.time_step)              # Bring SCL high, data holds at d, maybe assert STROBE
            self.update(SCL=0, SDA=0, STB=0, dwell=0)                                           # Clock low, make this port RZ (Return to Zero), One's will get hammered, STROBE back low
        else: # thd_dat_steps < 0                                                               # Negative hold time
            self.dwell(self.tlow - self.tsu_dat - self.time_step)                               # Dwell until time to change the data
            self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)            # Bring data high, hold STROBE
            self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh+self.thd_dat-self.time_step) # Bring SCL high, maybe assert STROBE
            self.update(SCL=1, SDA=0, STB=strobe, dwell=-self.thd_dat-self.time_step)           # Brind SDA low, maybe keep STROBE high
            self.update(SCL=0, SDA=0, STB=0, dwell=0)                                           # Clock low, Make this port RZ (Return to Zero), One's will get hammered, STROBE low
        self.audit_pattern()

    def add_ack_bit(self, strobe):
        self.add_data_bit(1, strobe)

    def add_byte(self, byte, strobes):
        '''
        For each bit in strobes, a strobe is added.
        Bits are [0..8] where 0 is the MSB of the data, 7 is the LSB of the data and 8 is the ACK.
        '''
        for bit in self.biterator(byte):
            self.add_data_bit(bit, 1 if strobes[bit] else 0)
        self.add_ack_bit(1 if strobes[8] else 0)

    def add_addr7(self, addr7, R_Wb, strobes):
        self.add_byte(addr7*2 + R_Wb, strobes)

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
        
    def get_printable_pattern(self):
        SCL1=""
        SCL2=""
        SDA1=""
        SDA2=""
        STB1=""
        STB2=""
        for value in self.get_SCL():
            SCL1 += "_" if value else " "
            SCL2 += " " if value else "_"
        for value in self.get_SDA():
            SDA1 += "_" if value else " "
            SDA2 += " " if value else "_"
        for value in self.get_STB():
            STB1 += "_" if value else " "
            STB2 += " " if value else "_"
        return f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nSCL: {SCL1}\n     {SCL2}\n\n\nSDA: {SDA1}\n     {SDA2}\n\n\nSTB: {STB1}\n     {STB2}\n\n\n"

if __name__ == "__main__":
    time_step = 1
    pattern = TWI(time_step=time_step, max_record_size=4096)
    pattern.tbuf    = 3
    pattern.thd_sta = 3
    pattern.tlow    = 12
    pattern.thd_dat = 1
    pattern.thigh   = 6
    pattern.tsu_dat = 1
    pattern.tsu_sta = 3
    pattern.tsu_sto = 3
    pattern.tsp_SCL_lo = 0
    pattern.tsp_SCL_hi = 1
    pattern.tsp_SDA_lo = 0
    pattern.tsp_SDA_hi = 0
    pattern.init_pattern()
    pattern.add_lead_in(SCL=[1], SDA=[0], STROBE=[0])
    pattern.dwell(3)
    pattern.add_stop(strobe=False)
    pattern.add_start(strobe=False)
    pattern.add_addr7(addr7=0x69, R_Wb=0, strobes=[0,0,0,0,0,0,0,0,1])
    file = open("pattern.txt", "w")
    file.write(pattern.get_printable_pattern())
    file.close()