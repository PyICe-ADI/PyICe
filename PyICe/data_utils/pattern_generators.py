from PyICe.lab_utils.eng_string import eng_string
from PyICe import LTC_plot

class TWI_Pattern():
    '''
    This class can be used to construct a Two Wire Interface Pattern (I²C or SMBus or whatever) time-slice by time-slice.
    It's meant to feed into a pattern generator instrument such as the old HP8110A dual pattern generator or its modern equivalent.
    It has two channels, one for the I²C pins SDA and SCL as well as a strobe channel (which the HP811xx family supports) to trigger a scope.
    '''
    class Leader():
        def __init__(self, pattern, SCL, SDA, tleader, strobe=False):
            self.pattern = pattern
            self.tleader = pattern.quantize(tleader)
            self.SCL = SCL
            self.SDA = SDA
            self.STB = strobe
        def extend(self, previous_item):
            self.pattern.dwell(SCL=self.SCL, SDA=self.SDA, STB=self.STB, tdwell=self.tleader)
    
    class Start():
        def __init__(self, pattern, thd_sta, strobe=False):
            self.pattern = pattern
            self.thd_sta = pattern.quantize(thd_sta)
            self.STB = strobe
        def extend(self, previous_item):
            self.pattern.dwell(SCL=1, SDA=0, STB=self.STB, tdwell=self.thd_sta)

    class Stop():
        def __init__(self, pattern, tsu_sto, tbuf, strobe=False):
            self.pattern = pattern
            self.tsu_sto = pattern.quantize(tsu_sto)
            self.tbuf = pattern.quantize(tbuf)
            self.STB = strobe
        def extend(self, previous_item):
            self.pattern.dwell(SCL=1, SDA=0, STB=self.STB, tdwell=self.tsu_sto)
            self.pattern.dwell(SCL=1, SDA=1, STB=self.STB, tdwell=self.tbuf)

    class Bitend():
        def __init__(self, pattern, strobe=False):
            self.pattern = pattern
            self.STB = strobe
        def extend(self, previous_item):
            self.pattern.dwell(SCL=0, SDA=previous_item.value, STB=self.STB, tdwell=previous_item.thd_dat)

    class SDA_Spike():
        def __init__(self, pattern, value, tstart, twidth, strobe=False):
            self.pattern = pattern
            self.value = value
            self.tstart = pattern.quantize(tstart)
            self.twidth = pattern.quantize(twidth)
            self.STB = strobe
            assert self.twidth > 0, f"TWI Pattern Generator: Requested SDA spike starting at {tstart} rounded to 0 width in pattern, not acheivable."
        def extend(self, previous_item):
            self.pattern.sda_spikes.append(self)
            
    class SCL_Spike():
        def __init__(self, pattern, value, tstart, twidth, strobe=False):
            self.pattern = pattern
            self.value = value
            self.tstart = pattern.quantize(tstart)
            self.twidth = pattern.quantize(twidth)
            self.STB = strobe
            assert self.twidth > 0, f"TWI Pattern Generator: Requested SCL spike starting at {tstart} rounded to 0 width in pattern, not acheivable."
        def extend(self, previous_item):
            self.pattern.scl_spikes.append(self)

    class Bit():
        '''
        The data bit cycle starts by bringing SCL low.
        The previous data bit is held until its hold time (THD_DAT Prev) expires or is brought low immediately if the pervious bit's hold time is 0.
        It then dwells with SCL low until the setup time of this bit whereupon SDA goes to the value for this bit.
        It then dwells for the setup time for this bit and then SCL goes high.
        SCL stays high for the duration of THIGH.
        If the hold time of this bit is negative, SDA is brought low before this bit's cycle ends.
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
        def __init__(self, pattern, value, tlow, thigh, tsu_dat, thd_dat, strobe=False):
            self.pattern = pattern
            self.value = value
            self.tlow = pattern.quantize(tlow)
            self.thigh = pattern.quantize(thigh)
            self.tsu_dat = pattern.quantize(tsu_dat)
            self.thd_dat = pattern.quantize(thd_dat)
            self.STB = strobe
        def extend(self, previous_item):              
            if isinstance(previous_item, self.pattern.Start):
                previous_thd_dat = 0
                previous_value = 0
            else:
                previous_thd_dat = previous_item.thd_dat
                previous_value = previous_item.value
            if  previous_thd_dat >= 0:    # Previous bit had Positive or Zero hold time
                self.pattern.dwell(SCL=0, SDA=previous_value, STB=0,    tdwell=previous_thd_dat)
                self.pattern.dwell(SCL=0, SDA=0, STB=0,                 tdwell=self.tlow - previous_thd_dat - self.tsu_dat)
                self.pattern.dwell(SCL=0, SDA=self.value, STB=0,        tdwell=self.tsu_dat)
            else:                         # Previous bit had Negative hold time
                self.pattern.dwell(SCL=0, SDA=0, STB=0,                 tdwell=self.tlow - self.tsu_dat)
                self.pattern.dwell(SCL=0, SDA=self.value, STB=0,        tdwell=self.tsu_dat)
            if self.thd_dat >= 0:         # Current bit has Positive or Zero hold time
                self.pattern.dwell(SCL=1, SDA=self.value, STB=self.STB, tdwell=self.thigh)
            else:                         # Current bit has Negative hold time
                self.pattern.dwell(SCL=1, SDA=self.value, STB=self.STB, tdwell=self.thigh + self.thd_dat)
                self.pattern.dwell(SCL=1, SDA=0, STB=self.STB,          tdwell=-self.thd_dat)
    '''
    Here's the start of the actual TWI pattern class.
    '''
    def __init__(self, tstep, max_record_size):
        self.tstep = tstep
        self.max_record_size = max_record_size
        
    def initialize(self):
        '''Call this whenever you want to start a new pattern or flush an existing pattern to change settings.
           Otherwise the pattern will keep on growing if you keep adding items.'''
        self.items = []
        self.SDA = []
        self.SCL = []
        self.STB = []
        self.sda_spikes = []
        self.scl_spikes = []

    def add_item(self, item):
        self.items.append(item)

    def quantize(self, time):
        return round(time / self.tstep) * self.tstep

    def dwell(self, SCL, SDA, STB, tdwell):
        cycles = round(tdwell/self.tstep)
        assert cycles >= 0, f"TWI Pattern Generator: tdwell of {tdwell} results in the addition of a negative time slice, not acheivable."
        self.SCL.extend([SCL] * cycles)
        self.SDA.extend([SDA] * cycles)
        self.STB.extend([STB] * cycles)

    def pad_out(self):
        cycles = self.max_record_size - len(self.SCL)
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)
        self.STB.extend(self.STB[-1:] * cycles)

    def finalize(self):
        previous = None
        for item in self.items:
            item.extend(previous)
            previous = item
        for sda_spike in self.sda_spikes:
            for index in range(len(self.SDA)):
                if index > sda_spike.tstart / self.tstep and index <= (sda_spike.tstart + sda_spike.twidth) / self.tstep:
                    if sda_spike.value:
                        self.SDA[index] ^= 1
                    else:
                        self.SDA[index] &= 0
        for scl_spike in self.scl_spikes:
            for index in range(len(self.SCL)):
                if index > scl_spike.tstart / self.tstep and index <= (scl_spike.tstart + scl_spike.twidth) / self.tstep:
                    if scl_spike.value:
                        self.SCL[index] ^= 1
                    else:
                        self.SCL[index] &= 0
        self.audit()

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
        values = []
        for position in range(len(self.SCL)):
            values.append(self.SCL[position] * 2**(SCL_channel-1) + self.SDA[position] * 2**(SDA_channel-1) + self.STB[position] * 2**(STB_channel-1))
        return values
        
    def audit(self):
        assert len(self.SDA) == len(self.SCL), "TWI Pattern Generator: SDA and SCL records unequal length!"
        assert len(self.SCL) == len(self.STB), "TWI Pattern Generator: SCL and STB records unequal length!"
        assert len(self.SCL) <= self.max_record_size, f"TWI Pattern Generator: Record size of {len(self.SCL)} exceeds max record size of {self.max_record_size}!"

    def visualize(self, title=None, file_basename=None, plot_sizex=5, plot_sizey=4):
        times = [index*self.tstep for index in range(len(self.SCL))]
        G0 = LTC_plot.scope_plot(   plot_title  = "TWI Pattern" if title==None else title,
                                    plot_name   = None,
                                    xaxis_label = f"{eng_string(x=times[-1]/10, fmt=':.3g', si=True, units='s')} / DIV",
                                    xlims       = (times[0], times[-1]),
                                    ylims       = (0, 8))
        SCL = [value+5 for value in self.SCL]
        SDA = [value+3 for value in self.SDA]
        STB = [value+1 for value in self.STB]
        G0.add_trace(   data        = zip(times, SCL),
                        color       = LTC_plot.LT_RED_1,
                        marker      = None,
                        markersize  = 0,
                        legend      = "SCL")
        G0.add_trace(   data        = zip(times, SDA),
                        color       = LTC_plot.LT_BLUE_1,
                        marker      = None,
                        markersize  = 0,
                        legend      = "SDA")
        G0.add_trace(   data        = zip(times, STB),
                        color       = LTC_plot.LT_GREEN_1,
                        marker      = None,
                        markersize  = 0,
                        legend      = "STB")
        G0.add_legend(axis=1, location=(0.98, 0.98), justification='upper right', use_axes_scale=False, fontsize=10)
        G0.add_note(note=f"Pattern Length = {len(self.SCL)}", location=[0.01, 0.99], use_axes_scale=False, fontsize=10, axis=1, horizontalalignment="left", verticalalignment="top")
        Page = LTC_plot.Page(plot_count=1)
        Page.add_plot(G0, plot_sizex=plot_sizex, plot_sizey=plot_sizey)
        Page.create_svg(file_basename="TWI Pattern" if file_basename==None else file_basename)
        Page.create_pdf(file_basename="TWI Pattern" if file_basename==None else file_basename)

if __name__ == "__main__":
    pattern = TWI_Pattern(tstep=1, max_record_size=4096)
    pattern.initialize()
    pattern.add_item(pattern.Leader(pattern, SCL=1, SDA=0, tleader=2))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=3, tbuf=4))
    pattern.add_item(pattern.Start(pattern, thd_sta=5))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=0, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=0, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=0, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=0, tlow=6, thigh=4, tsu_dat=1, thd_dat=1))
    pattern.add_item(pattern.Bit(pattern, value=1, tlow=6, thigh=4, tsu_dat=1, thd_dat=1, strobe=True))
    pattern.add_item(pattern.Bitend(pattern))
    pattern.add_item(pattern.Stop(pattern, tsu_sto=4, tbuf=3))
    pattern.add_item(pattern.SDA_Spike(pattern, value=1, tstart=55.5, twidth=2))
    pattern.finalize()
    pattern.visualize()