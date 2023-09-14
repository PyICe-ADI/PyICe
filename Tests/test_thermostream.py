import visa
from lab import instrument
import time

# single channel temptronic_4310 thermostream
# add_channel doesnt take a name/number for the channel
#special methods: set_window(air_window), set_soak(soak_time), flow_off(), wait_settle()
# use wait_settle to wait for the soak to complete
#defaults to window = 3, soak=30
#extra data
#   _sense - the sensed temperature
#   _window - the temperature window
#   _time - the total settling time (including soak)
#   _soak - the programmed soak time
class temptronic_4310(instrument):
    def __init__(self,addr):
        instrument.__init__(self,addr)
        self.instrument = visa.instrument(addr)
        self.channels = []
        self.setpoint = 25
        self.soak = 30
        self.window = 3
        self.time = 0
        self.name = "temptronic_4310 @ " + str(addr)
        self.intrument.write("DUTM 1")
    def add_channel(self,name):
        self.channels.append(name)
    def write_channel(self,name,value):
        self.setpoint = value
        txt = "SETP " + str(self.setpoint) + ";WNDW " + str(self.window) + "; SOAK " + str(self.soak)
        self.instrument.write(txt)
        self.instrumnet.write("FLOW 1")
        self.instrumnet.write("COOL 1")
        self.time = 0
        pass
    def set_window(self,value):
        self.window = value
        txt = "WNDW " + str(self.window) 
        self.instrument.write(txt)
    def set_soak(self,value):
        self.soak = value
        txt = "SOAK " + str(self.soak) 
        self.instrument.write(txt)
    def off(self):
        self.instrument.write("FLOW 0")
        self.instrument.write("HEAD 0")
        self.instrument.write("COOL 0")
    def wait_settle(self):
        settled = False
        while not settled:
            time.sleep(.5)
            self.time += .5
            print(("Waiting To Settle: " + str(self.time)))
            tecr = self.instrument.ask("TECR?")
            if (tecr & 1):
                settled = True       
    def read_channel(self,name):
        return self.setpoint    
    def read_channels(self):
        results = {}
        for channel in self.channels:
            results[ channel  ] = self.read_channel(channel)
            results[ channel + "_sense_dut"] = self.instrument.ask("TMPD?")
            results[ channel + "_sense_air"] = self.instrument.ask("TMPA?")
            results[ channel + "_soak"] = self.soak
            results[ channel + "_window"] = self.window
            results[ channel + "_time"] = self.time
        return results
        
        
if __name__ =="__main__":
    t = temptronic_4310("GPIB0::24")
    t.add_channel("t")
    t.write_channel(0)
    t.wait_settle(self)
    print(settled)
    print((t.read_channel("t")))
    t.off()
