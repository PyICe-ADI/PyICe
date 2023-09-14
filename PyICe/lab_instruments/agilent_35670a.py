from ..lab_core import scpi_instrument
class agilent_35670a(scpi_instrument):

    '''Agilent 35670a 100kHz Signal Analyzer
        This driver is not complete and only supports noise measurements at this time.'''
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'agilent_35670a'
        scpi_instrument.__init__(self,"a35670 @ " + str(interface_visa))
        self.add_interface_visa(interface_visa)
    def add_channel_noise(self,channel_name,channel_num=1,freqs=[0,12.5,100,1000,10000,100000], res=[800,800,800,800,800], count=[150,600,600,600,600]):
        self.freqs = freqs
        self.res = res
        self.count = count
        self.progress_chars = ['-', '\\', '|', '/']
        self.mask = 0b000100010000
        self.timer=0
        self.get_interface().write(("SYSTem:PRESet"))
        self.get_interface().write(("INSTrument:SELect FFT"))
        self.get_interface().write(("INP2 OFF"))
        self.get_interface().write(("SENSe:REJect:STATe ON"))
        self.get_interface().write(("INPut1:LOW FLOat"))
        self.get_interface().write(("INPut1:COUPling DC"))
#        self.interface.write("VOLTage1:RANGe:AUTO 1")
        self.get_interface().write(("VOLTage1:RANGe 1.0 VPK"))
        self.get_interface().write(("SENSe:AVERage ON"))
        self.get_interface().write(("SENSe:AVERage:TYPE RMS"))
        self.get_interface().write(("SENSe:SWEep:OVERlap 0"))
        self.get_interface().write(("CALC1:UNIT:VOLTage \"V/RTHZ\""))
        self.get_interface().write(("CALibration:AUTO ONCE"))
        self.get_interface().write(("ABORt;:INIT"))
        self.get_interface().write(("FORMat:DATA ASCii"))
        self.add_channel(channel_name, channel_num)
    def add_channel(self,channel_name,channel_num):
        '''Add named channel to instrument.'''
        meter_channel = channel(channel_name,read_function=lambda: self.read_channel(channel_num) )
        return self._add_channel(meter_channel)
    def read_channel(self,channel_num):
        '''Return float representing meter measurement.  Units are {} etc depending on meter configuration.'''
        for ii in range(0,len(self.count)):
            print((f'Start : {self.freqs[ii]}, Stop : {self.freqs[ii+1]}'))
            self.get_interface().write(("SENSe:FREQuency:STARt "  + str(self.freqs[ii])))
            self.get_interface().write(("SENSe:FREQuency:STOP "  + str(self.freqs[ii+1])))
            self.get_interface().write(("SENSe:FREQuency:RESolution "  + str(self.res[ii])))
            self.get_interface().write(("SENSe:AVERage:COUNt " + str(self.count[ii])))
            self.get_interface().write(("ABORt;:INIT:IMM"))
            status = int(self.get_interface().ask("STATus:OPERation:CONDition?"))
            #condition? returns the sum of the decimal weights of all bits currently set to 1 i the operation status condition register
            #BIT(WEIGHT)Description
            #0(1)Calibrating
            #1(2)Settling
            #2(4)Ranging
            #3(8)
            #4(16)Measuring
            #5(32)Waiting for Trig
            #6(64)Waiting for Arm
            #7(128)
            #8(256)Averaging
            #9(512)Hardcopy in Progress
            #10(1024)Waiting for Accept/Reject
            #11(2048)Loading Waterfall
            #12(4096)
            #13(8192)
            #14(16384)Program Running
            time.sleep(1)
            test = int(status) & int(self.mask)
            #loop waiting for averaging to complete
            while test != 0:
                status = int(self.get_interface().ask("STATus:OPERation:CONDition?"))
                time.sleep(1)
                print(f"\r MEASURING {self.progress_chars[self.timer%len(self.progress_chars)]}", end=' ')
                sys.stdout.flush()
                test = int(status) & int(self.mask) #will only equal zero if averaging is complete
                self.timer += 1
            xdata = (self.get_interface().ask(("CALC" + str(channel_num) + ":X:DATA?")))
            ydata = (self.get_interface().ask(("CALC" + str(channel_num) + ":DATA?")))
            xdata = xdata.replace('+','')
            xlist = xdata.split(',')
            ylist = ydata.split(',')
            #An undocumented "feature" of the 35670A is that it returns more X data points than you have set up for
            #lines of resolution, while all you see on the display is one point per line of resolution continuously
            #connected. The extra data is aliased data that is not used in the display. Unfortunately, the programmer
            #has to take care of this data when the trace data is transferred across GPIB.
            #RES | Array Size
            #400 | 513
            #800 | 1025
            #1600 | 2049
            #the if statements below take care of this
            test = len(ylist)
            if test == 101:
                xlist = xlist[:101]
            elif test == 201:
                xlist = xlist[:201]
            elif test == 401:
                xlist = xlist[:401]
            elif test == 801:
                xlist = xlist[:801]
            elif test == 1601:
                xlist = xlist[:1601]
            if ii == 0:
                xlist_final = xlist
                ylist_final = ylist
            elif ii > 0:
                xlist_final = xlist_final + xlist
                ylist_final = ylist_final + ylist
        dictionary = {"freq":xlist_final,"noise":ylist_final}
        return (dictionary)
