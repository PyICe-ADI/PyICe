class TWI_Pattern():
    '''
    This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    It's meant to feed into a pattern generator instrument such as the old HP8110A dual pattern generator or its modern equivalent.
    It has two channels, one for the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    '''
    
    class Leader():
        def __init__(self, pattern, SCL, SDA, tleader):
            self.pattern = pattern
            self.tleader = pattern.quantize(tleader)
            self.SCL = SCL
            self.SDA = SDA
        def extend(self, previous_item):
            self.pattern.dwell(SCL=self.SCL, SDA=self.SDA, tdwell=self.tleader)
    
    class Start():
        def __init__(self, pattern, thd_sta):
            self.pattern = pattern
            self.thd_sta = pattern.quantize(thd_sta)
        def extend(self, previous_item):
            self.pattern.dwell(SCL=1, SDA=0, tdwell=self.thd_sta)

    class Stop():
        def __init__(self, pattern, tsu_sto, tbuf):
            self.pattern = pattern
            self.tsu_sto = pattern.quantize(tsu_sto)
            self.tbuf = pattern.quantize(tbuf)
        def extend(self, previous_item):
            self.pattern.dwell(SCL=1, SDA=0, tdwell=self.tsu_sto)
            self.pattern.dwell(SCL=1, SDA=1, tdwell=self.tbuf)

    class Bitend():
        def __init__(self, pattern, tsu_sto):
            self.pattern = pattern
            self.tsu_sto = pattern.quantize(tsu_sto)
        def extend(self, previous_item):
            self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tsu_sto)

    class Bit():
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
        
        Spikes shall be inserted as follows:
        -----------------------------------
            1) High spikes on SCL from the low phase, if requested, shall be inserted centered in the TLOW (A) clock interval (without regard to data setup and hold times).
            2) Low spikes on SCL from the high phase, if requested, shall be inserted centered in the THIGH clock interval.
            3) All spikes on data, if requested, shall be inserted centered in the THIGH clock interval.
                a) If the data is low, a high spike shall be inserted.
                b) If the data is high, a low spike shall be inserted.
                                            _____________________________
                                           |
    SCL ___________________________________|

        _________                   _____________________________________
    SDA  D (PREV)|                 |             D (THIS ONE)
        _________|_________________|_____________________________________
                                                                         
        <- THD ->|                 |<-TSU->|                             
         (PREV)  |                 |       |                             
        <------------ TLOW --------------->|<--------- THIGH ----------->
                 |                 |       |                             
        █••••••••█•••••••••••••••••█•••••••█••••••••••••••••••••••••••••• <------ █ (Blocks) Denote where changes occur, • (Dots) denote time slices
        
        
        
        
                 __________       _________                     ___    
    SCL         ↑          \ Tsp /         |                   /   \   
        ________|           \___/          ↓__________________/ Tsp \__
                |                          |                           
        ________|__________  ___  _________|_________                  
    SDA         |          \/Tsp\/         |         |                 
        ________|__________/\___/\_________|_________↓_________________
        |       |                          |         |                 
        |<-TSU->|                          |<- THD ->|                 
        |       |                          |         |                 
        ------->|<-------- THIGH --------->|<------------ TLOW --------
        █•••••••█••••••••••••••••••••••••••█•••••••••█••••••••••••••••• <------ █ (Blocks) Denote where changes occur, • (Dots) denote time slices
        '''
        def __init__(self, pattern, value, tlow, thigh, tsu_dat, thd_dat):
            self.pattern = pattern
            self.value = value
            self.tlow = pattern.quantize(tlow)
            self.thigh = pattern.quantize(thigh)
            self.tsu_dat = pattern.quantize(tsu_dat)
            self.thd_dat = pattern.quantize(thd_dat)
            self.spikes = []
        def add_spike(self, value, tstart, twidth):
            self.spikes.append(self.pattern.Spike(value, tstart, twidth))
        def add_strobe(self):
            pass
        def extend(self, previous_item):
            ''' This item assumes SDA and SCL start out low and that we are starting at the change of data.'''
            # if isinstance(previous_item, self.pattern.Start): # TODO, account for negative hold on the from-START case
                # self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow-self.tsu_dat)
                # self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh)
                # self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.thd_dat)
                # self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - self.thd_dat - self.tsu_dat)
            # else:
                # if  previous_item.thd_dat >= 0: # Positive or Zero hold time
                    # self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
                    # self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh) #self.tlow - previous_item.thd_dat - self.tsu_dat)
                    # self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.thd_dat)
                    # self.pattern.dwell(SCL=0, SDA=0, tdwell=previous_item.tlow  elf.thigh)
                # else: # Negative hold time
                    # self.pattern.dwell(SCL=0, SDA=previous_item.value, tdwell=previous_item.thd_dat)
                    # self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - previous_item.thd_dat - self.tsu_dat)
                    # self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
                    # self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh + self.thd_dat)
                    # self.pattern.dwell(SCL=1, SDA=0, tdwell=-self.thd_dat)
            
            
            
            
            
            if isinstance(previous_item, self.pattern.Start):
                self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - self.tsu_dat)
                self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
                self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh)
            else:
                if  previous_item.thd_dat >= 0: # Positive or Zero hold time
                    self.pattern.dwell(SCL=0, SDA=previous_item.value, tdwell=previous_item.thd_dat)
                    self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - previous_item.thd_dat - self.tsu_dat)
                    self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
                    self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh)
                else: # Negative hold time
                    self.pattern.dwell(SCL=0, SDA=previous_item.value, tdwell=previous_item.thd_dat)
                    self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - previous_item.thd_dat - self.tsu_dat)
                    self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
                    self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh + self.thd_dat)
                    self.pattern.dwell(SCL=1, SDA=0, tdwell=-self.thd_dat)
            




    class Spike():
        def __init__(self, value, tstart, twidth):
            self.value = value
            self.tstart = tstart
            self.twidth = twidth
    '''
    Here's the start of the actual TWI pattern class.
    '''
    def __init__(self, tstep):
        self.tstep = tstep
        self.items = []
        self.SDA = []
        self.SCL = []
        self.STB = []

    def quantize(self, time):
        return round(time / self.tstep) * self.tstep

    def dwell(self, SCL, SDA, tdwell):
        cycles = self.quantize(tdwell)
        assert cycles >= 0, f"TWI Pattern Generator: tdwell of {tdwell} results in a negative time slice addition, not acheivable."
        self.SCL.extend([SCL] * cycles)
        self.SDA.extend([SDA] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)

    def add_item(self, item):
        self.items.append(item)

    def generate(self):
        previous = None
        for item in self.items:
            item.extend(previous)
            previous = item
            
    def get_SDA(self):
        return self.SDA
        
    def get_SCL(self):
        return self.SCL
        
    def get_STB(self):
        return self.STB

    def get_printable_pattern(self):
        SCL1=""
        SCL2=""
        SDA1=""
        SDA2=""
        STB1=""
        STB2=""
        for value in self.get_SCL():
            if value in [1,0]:
                SCL1 += "_" if value else " "
                SCL2 += " " if value else "_"
            else:
                SCL1 += value
                SCL2 += value
        for value in self.get_SDA():
            if value in [1,0]:
                SDA1 += "_" if value else " "
                SDA2 += " " if value else "_"
            else:
                SDA1 += value
                SDA2 += value
        for value in self.get_STB():
            STB1 += "_" if value else " "
            STB2 += " " if value else "_"
        return f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nSCL: {SCL1}\n     {SCL2}\n\n\nSDA: {SDA1}\n     {SDA2}\n\n\nSTB: {STB1}\n     {STB2}\n\n\n"

if __name__ == "__main__":
    pattern = TWI_Pattern(tstep=1)
    # bit1 = pattern.Bit(pattern, value=1, tlow=12, thigh=6, tsu_dat=1, thd_dat=1)
    # bit1.add_spike(value=1, start_time=3, wdith=3)
    pattern.add_item(pattern.Leader(pattern, SCL=1, SDA=0, tleader=2))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=3, tbuf=4))
    pattern.add_item(pattern.Start(pattern, thd_sta=5))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=3))
    # pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=3))
    # pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=3))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=-2))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=3))
    pattern.add_item(pattern.Bitend(pattern, tsu_sto=4))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=3, tbuf=3))
    pattern.generate()
    
    file = open("pattern.txt", "w")
    file.write(pattern.get_printable_pattern())
    file.close()
    
























# # class Bit():
    # # def __init__(self):
        # # self.SCL = []
        # # self.SDA = []
        # # self.STB = []

    # # def append_SCL(self, value):
        # # self.SCL.extend([value])

    # # def pad_SCL(self, cycles):
        # # self.SCL.extend(self.SCL[-1:] * cycles)
        

# class TWI():
    # '''
    # This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    # It's meant to feed into a pattern generator instrument such as the old HP8110a dual pattern generator or its modern equivalent.
    # It has two channels, one for the the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    # '''
    # def __init__(self, time_step, max_record_size=4096):
        # self.max_record_size = max_record_size
        # self.time_step = time_step

    # def biterator(self, byte):
        # '''Iterates over the bits of an integer from left to right.'''
        # length = byte.bit_length()
        # for index in range(length):
            # yield 1 if byte << index & 1 << length-1 == 1 << length-1 else 0
            
    # def init_pattern(self):
        # self.SCL                = []
        # self.SDA                = []
        # self.STB                = []
        # self.tbuf               = self.quantize(self.tbuf)
        # self.thd_sta            = self.quantize(self.thd_sta)
        # self.tlow               = self.quantize(self.tlow)
        # self.thd_dat            = self.quantize(self.thd_dat)
        # self.thigh              = self.quantize(self.thigh)
        # self.tsu_dat            = self.quantize(self.tsu_dat)
        # self.tsu_sta            = self.quantize(self.tsu_sta)
        # self.tsu_sto            = self.quantize(self.tsu_sto)
        # self.tspk_SCL_hi_clk    = self.quantize(self.tspk_SCL_hi_clk)
        # self.tdwl_SCL_hi_clk    = self.quantize(self.tdwl_SCL_hi_clk)
        # self.tspk_SCL_lo_clk    = self.quantize(self.tspk_SCL_lo_clk)
        # self.tdwl_SCL_lo_clk    = self.quantize(self.tdwl_SCL_lo_clk)
        # self.tspk_SDA_lo_clk    = self.quantize(self.tspk_SDA_lo_clk)
        # self.tdwl_SDA_lo_clk    = self.quantize(self.tdwl_SDA_lo_clk)
        # self.tspk_SDA_hi_clk    = self.quantize(self.tspk_SDA_hi_clk)
        # self.tdwl_SDA_hi_clk    = self.quantize(self.tdwl_SDA_hi_clk)

    # def update(self, SDA, SCL, STB, dwell):
        # self.SCL.extend([SCL])
        # self.SDA.extend([SDA])
        # if STB == "HOLD":
            # self.STB.extend(self.STB[-1:])
        # else:
            # self.STB.extend([STB])
        # self.dwell(dwell)
        # self.audit_pattern()

    # def add_lead_in(self, SDA, SCL, STROBE):
        # self.SCL.extend(SCL)
        # self.SDA.extend(SDA)
        # self.STB.extend(STROBE)
        # self.audit_pattern()
        
    # def add_lead_out(self, SDA, SCL, STROBE):
        # self.SCL.extend(SCL)
        # self.SDA.extend(SDA)
        # self.STB.extend(STROBE)
        # self.audit_pattern()

    # def add_start(self, strobe):
        # self.SCL.extend([1])
        # self.SDA.extend([0])
        # self.STB.extend([strobe])
        # self.dwell(self.thd_sta - self.time_step)
        # self.SCL.extend([0])
        # self.SDA.extend([0])
        # self.STB.extend([0])
        # self.dwell(self.tlow - self.tsu_dat - self.time_step)
        # self.audit_pattern()

    # def add_stop(self, strobe):
        # self.SCL.extend([1])
        # self.SDA.extend([1])
        # self.STB.extend([strobe])
        # self.dwell(self.tbuf - self.time_step)
        # self.audit_pattern()

    # def add_data_to_low(self, strobe):
        # self.SCL.extend(self.SCL[-1:])
        # self.SDA.extend([0])
        # self.STB.extend([0])
        # self.dwell(self.tlow - self.time_step)
        # self.audit_pattern()

    # def add_clock_to_high(self, strobe):
        # self.SCL.extend([1])
        # self.SDA.extend(self.SDA[-1:])
        # self.STB.extend([0])
        # self.dwell(self.tsu_sto - self.time_step)
        # self.audit_pattern()
        
    # def quantize(self, time):
        # return round(time / self.time_step) * self.time_step

    # def add_data_bit(self, d, strobe):
        # '''
        # The data bit cycle starts by dwelling low for TLOW.
        # Then it SCL low.
        # Data is simultaneously transitioned to its new value.
        # It then dwells with SCL low and data at 'd' for T_SU_DAT (minus one time slice to account for the first one used as a transition).
        # After T_SU_DAT, SCL goes high and data remains at 'd'.
        # What happens next depends on the requested hold time.
        # If the requested hold time is zero, it dwells for thigh and then sets SCL and SDA low together at next time slice.
        # If the requested hold time is positive, it dwells for the high time and then brings SCL low while leaving SDA as is, whereupon it then dwells for the hold time T_HD_DAT.
        # If the requested hold time is negative, it dwells for the high time minus the (negative) hold time, sets SCL high and SDA low and then dwells for the remainder of the high time whereupon is sets SDA and SCL low.

        # |                                                                  |
        # |      ___             _____________       _________               |
    # SCL |     /   \           |             \ Tsp /         |              |
        # |____/ Tsp \__________|              \___/          |______________|
        # |                     |                             |              |
        # |              _______|_____________  ___  _________|______________|
    # SDA |             |       |             \/Tsp\/         |              | RZ
        # |_____________|_______|_____________/\___/\_________|______________|_
        # |             |       |                             |              |
        # |             |<-TSU->|                             |<--- THD ---->|
        # |             |       |                             |              |
        # |<----- TLOW (A) ---->|<--------- THIGH ----------->|<- TLOW (B) ->|
        # |             |       |                             |              |
        # |•••••••••••••█•••••••█•••••••••••••••••••••••••••••█••••••••••••••█  <------ █ (Blocks) Denote where changes occur, • (Dots) denote time slices
        
        # Spikes shall be inserted as follows:
        # -----------------------------------
            # 1) High spikes on SCL from the low phase, if requested, shall be inserted centered in the TLOW (A) clock interval (without regard to data setup and hold times).
            # 2) Low spikes on SCL from the high phase, if requested, shall be inserted centered in the THIGH clock interval.
            # 3) All spikes on data, if requested, shall be inserted centered in the THIGH clock interval.
                # a) If the data is low, a high spike shall be inserted.
                # b) If the data is high, a low spike shall be inserted.
        # '''
# # self.tspk_SCL_lo_clk
# # self.tdwl_SCL_lo_clk
# # self.tspk_SCL_hi_clk
# # self.tdwl_SCL_hi_clk
# # self.tspk_SDA_lo_clk
# # self.tdwl_SDA_lo_clk
# # self.tspk_SDA_hi_clk
# # self.tdwl_SDA_hi_clk

        # if  self.thd_dat > 0:                                                                   # Positive hold time
            # if self.tspk_SCL_lo_clk > 0 or self.tspk_SDA_lo_clk > 0:
                # self.dwell(self.tdwl_SCL_lo_clk)
                # self.update(SCL=1, SDA=0, STB="HOLD", dwell=self.tspk_SCL_lo_clk-self.time_step)
                # self.update(SCL=0, SDA=0, STB="HOLD", dwell=self.tlow-self.tsu_dat-self.thd_dat-self.tspk_SCL_lo_clk-self.time_step)
                
                
                
                
                
                
                
                
                
            # else:
                
            # self.update(SCL=0, SDA=0, STB="HOLD", dwell=self.tlow-self.tsu_dat-self.thd_dat-self.time_step)
            # self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)
            # self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh-self.time_step)
            # self.update(SCL=0, SDA=d, STB=0, dwell=self.thd_dat-self.time_step)
            # self.update(SCL=0, SDA=0, STB=0, dwell=0)
        # elif self.thd_dat == 0:                                                                 # Request is zero hold time
            # self.dwell(self.tlow - self.tsu_dat - self.time_step)
            # self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)
            # self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh-self.time_step)
            # self.update(SCL=0, SDA=0, STB=0, dwell=0)
        # else: # self.thd_dat < 0                                                                # Negative hold time
            # self.dwell(self.tlow - self.tsu_dat - self.time_step)
            # self.update(SCL=0, SDA=d, STB="HOLD", dwell=self.tsu_dat-self.time_step)
            # self.update(SCL=1, SDA=d, STB=strobe, dwell=self.thigh+self.thd_dat-self.time_step)
            # self.update(SCL=1, SDA=0, STB=strobe, dwell=-self.thd_dat-self.time_step)
            # self.update(SCL=0, SDA=0, STB=0, dwell=0)
        # self.audit_pattern()

    # def add_ack_bit(self, strobe):
        # self.add_data_bit(1, strobe)

    # def add_byte(self, byte, strobes):
        # '''
        # For each bit in strobes, a strobe is added.
        # Bits are [0..8] where 0 is the MSB of the data, 7 is the LSB of the data and 8 is the ACK.
        # '''
        # for bit in self.biterator(byte):
            # self.add_data_bit(bit, 1 if strobes[bit] else 0)
        # self.add_ack_bit(1 if strobes[8] else 0)

    # def add_addr7(self, addr7, R_Wb, strobes):
        # self.add_byte(addr7*2 + R_Wb, strobes)

    # def dwell(self, tdwell):
        # cycles = self.quantize(tdwell)
        # assert cycles >= 0, f"TWI Pattern Generator: tdwell of {tdwell} results in a negative time slice addition, not acheivable."
        # self.SCL.extend(self.SCL[-1:] * cycles)
        # self.SDA.extend(self.SDA[-1:] * cycles)
        # self.STB.extend(self.STB[-1:] * cycles)
        # self.audit_pattern()
        
    # def pad_out(self):
        # cycles = 4096 - len(self.SCL)
        # self.SCL.extend(self.SCL[-1:] * cycles)
        # self.SDA.extend(self.SDA[-1:] * cycles)
        # self.STB.extend(self.STB[-1:] * cycles)
        # self.audit_pattern()

    # def get_SDA(self):
        # return self.SDA
        
    # def get_SCL(self):
        # return self.SCL
        
    # def get_STB(self):
        # return self.STB
        
    # def get_ALL(self, SCL_channel, SDA_channel, STB_channel):
        # '''
        # Build up the compound record of instrument Channels 1, 2 and 3 (Strobe).
        # On the HP8110a, for example, the two output channels and the Strobe channel are binarily weighted so it takes values of 0-7 for 3 bits.
        # '''
        # self.audit_pattern()
        # values = []
        # for position in range(len(self.SCL)):
            # values.append(self.SCL[position] * 2**(SCL_channel-1) + self.SDA[position] * 2**(SDA_channel-1) + self.STB[position] * 2**(STB_channel-1))
        # return values
        
    # def audit_pattern(self):
        # assert len(self.SDA) == len(self.SCL), "TWI Pattern Generator: SDA and SCL records unequal length!"
        # assert len(self.SCL) == len(self.STB), "TWI Pattern Generator: SCL and STB records unequal length!"
        # assert len(self.SCL) <= self.max_record_size, f"TWI Pattern Generator: Record size of {len(self.SCL)} exceeds max record size of {self.max_record_size}!"
        
    # def get_printable_pattern(self):
        # SCL1=""
        # SCL2=""
        # SDA1=""
        # SDA2=""
        # STB1=""
        # STB2=""
        # for value in self.get_SCL():
            # SCL1 += "_" if value else " "
            # SCL2 += " " if value else "_"
        # for value in self.get_SDA():
            # SDA1 += "_" if value else " "
            # SDA2 += " " if value else "_"
        # for value in self.get_STB():
            # STB1 += "_" if value else " "
            # STB2 += " " if value else "_"
        # return f"\n\n\n\n\n\n\n\n\n\n\n\n\n\n\nSCL: {SCL1}\n     {SCL2}\n\n\nSDA: {SDA1}\n     {SDA2}\n\n\nSTB: {STB1}\n     {STB2}\n\n\n"

# if __name__ == "__main__":
    # time_step = 1
    # pattern = TWI(time_step=time_step, max_record_size=4096)
    # pattern.tbuf    = 3
    # pattern.thd_sta = 3
    # pattern.tlow    = 12
    # pattern.thd_dat = 1
    # pattern.thigh   = 6
    # pattern.tsu_dat = 1
    # pattern.tsu_sta = 3
    # pattern.tsu_sto = 3
    
    
    # pattern.tspk_SCL_lo_clk = 0
    # pattern.tdwl_SCL_lo_clk = 10
    # pattern.tspk_SCL_hi_clk = 0
    # pattern.tdwl_SCL_hi_clk = 0
    # pattern.tspk_SDA_lo_clk = 0
    # pattern.tdwl_SDA_lo_clk = 0
    # pattern.tspk_SDA_hi_clk = 0
    # pattern.tdwl_SDA_hi_clk = 0
    

    # pattern.init_pattern()
    # pattern.add_lead_in(SCL=[1], SDA=[0], STROBE=[0])
    # pattern.dwell(3)
    # pattern.add_stop(strobe=False)
    # pattern.add_start(strobe=False)
    # pattern.add_addr7(addr7=0x69, R_Wb=0, strobes=[0,0,0,0,0,0,0,0,1])
    # file = open("pattern.txt", "w")
    # file.write(pattern.get_printable_pattern())
    # file.close()