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
        def __init__(self, pattern):
            self.pattern = pattern
        def extend(self, previous_item):
            self.pattern.dwell(SCL=0, SDA=previous_item.value, tdwell=previous_item.thd_dat)

    class Spike():
        def __init__(self, value, tstart, twidth):
            self.value = value
            self.tstart = tstart
            self.twidth = twidth

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
        '''
        def __init__(self, pattern, value, tlow, thigh, tsu_dat, thd_dat):
            self.pattern = pattern
            self.value = value
            self.tlow = pattern.quantize(tlow)
            self.thigh = pattern.quantize(thigh)
            self.tsu_dat = pattern.quantize(tsu_dat)
            self.thd_dat = pattern.quantize(thd_dat)
        def extend(self, previous_item):
            ''' This item assumes SDA and SCL start out low and that we are starting at the change of data.
                Be aware, hold time of the last added bit is ignored
                Presumably OK since it's the ACK bit and has been acptured already?'''                
            if isinstance(previous_item, self.pattern.Start):
                previous_thd_dat = 0
                previous_value = 0
            else:
                previous_thd_dat = previous_item.thd_dat
                previous_value = previous_item.value
            if  previous_thd_dat >= 0:    # Previous bit had Positive or Zero hold time
                self.pattern.dwell(SCL=0, SDA=previous_value,  tdwell=previous_thd_dat)
                self.pattern.dwell(SCL=0, SDA=0,                    tdwell=self.tlow - previous_thd_dat - self.tsu_dat)
                self.pattern.dwell(SCL=0, SDA=self.value,           tdwell=self.tsu_dat)
            else:                         # Previous bit had Negative hold time
                self.pattern.dwell(SCL=0, SDA=0, tdwell=self.tlow - self.tsu_dat)
                self.pattern.dwell(SCL=0, SDA=self.value, tdwell=self.tsu_dat)
            if self.thd_dat >= 0:         # Current bit has Positive or Zero hold time
                self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh)
            else:                         # Current bit has Negative hold time
                self.pattern.dwell(SCL=1, SDA=self.value, tdwell=self.thigh + self.thd_dat)
                self.pattern.dwell(SCL=1, SDA=0, tdwell=-self.thd_dat)

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
    pattern.add_item(pattern.Leader(pattern, SCL=1, SDA=0, tleader=2))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=3, tbuf=4))
    pattern.add_item(pattern.Start(pattern, thd_sta=5))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=-3))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=-2))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=-1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=0))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=2))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=3))
    pattern.add_item(pattern.Bitend(pattern))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=4, tbuf=3))
    pattern.generate()
    
    file = open("pattern.txt", "w")
    file.write(pattern.get_printable_pattern())
    file.close()
    


    # pattern.init_pattern()
    # pattern.add_lead_in(SCL=[1], SDA=[0], STROBE=[0])
    # pattern.dwell(3)
    # pattern.add_stop(strobe=False)
    # pattern.add_start(strobe=False)
    # pattern.add_addr7(addr7=0x69, R_Wb=0, strobes=[0,0,0,0,0,0,0,0,1])
    # file = open("pattern.txt", "w")
    # file.write(pattern.get_printable_pattern())
    # file.close()