from ..lab_core import *
import time

class temptronic_4310(instrument):
        #DJS: TODO - Merge into temperature_chamber class when able to test that nothing gets broken.
    '''single channel temptronic_4310 thermostream
        special methods: set_window(air_window), set_soak(soak_time), off()
        use wait_settle to wait for the soak to complete
        defaults to window = 3, soak=30
        extra data
           _sense - the sensed temperature
           _window - the temperature window
           _time - the total settling time (including soak)
           _soak - the programmed soak time'''
    def __init__(self,interface_visa,en_compressor=True):
        '''Optionally disable compressor on startup'''
        #needs enable/compressor channel work
        self._base_name = 'temptronic_4310'
        instrument.__init__(self,f"temptronic_4310 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.setpoint = 25
        self.soak = 90
        self.window = 1
        self.air2dut = 50
        self.maxair = 170
        self.time = 0
        self.get_interface().write(("DUTM 1")) #use dut measurement
        if en_compressor:
            self.get_interface().write(("COOL 1"))
            print("Enabling Compressor... ")
            time.sleep(70)
            print("Compressor Enabled")
    def add_channel(self,channel_name,add_extended_channels=True):
        '''Helper method to add most commonly used channels.
        channel_name represents temperature setpoint.
        optionlayy also adds _sense_dut, _sense_air, _soak, _window, and _soak_settling_time channels.'''
        temp_channel = self.add_channel_temp(channel_name)
        if add_extended_channels:
            self.add_channel_sense_dut(channel_name + "_sense_dut")
            self.add_channel_sense_air(channel_name + "_sense_air")
            self.add_channel_soak(channel_name + "_soak")
            self.add_channel_window(channel_name + "_window")
            self.add_channel_soak_settling_time(channel_name + "_soak_settling_time")
        return temp_channel
    def add_channel_temp(self,channel_name):
        '''Channel_name represents PID loop forcing temperature setpoint.'''
        new_channel = channel(channel_name,write_function=self._write_temperature)
        new_channel.write(self.setpoint)
        return self._add_channel(new_channel)
    def add_channel_sense_dut(self,channel_name):
        '''channel_name represents primary PID control loop thermocouple readback.'''
        new_channel = channel(channel_name,read_function=lambda:  float(self.get_interface().ask("TMPD?")))
        return self._add_channel(new_channel)
    def add_channel_sense_air(self,channel_name):
        '''channel_name represents secondary air stream thermocouple readback.'''
        new_channel = channel(channel_name,read_function=lambda: float(self.get_interface().ask("TMPA?")))
        return self._add_channel(new_channel)
    def add_channel_soak(self,channel_name):
        '''channel_name represents soak time setpoint in seconds. Soak timer runs while temperature is continuously within 'window' and resets to zero otherwise.'''
        new_channel = channel(channel_name,write_function=self._set_soak)
        new_channel.write(self.soak)
        return self._add_channel(new_channel)
    def add_channel_window(self,channel_name):
        '''channel_name represents width setpoint of tolerance window to start soak timer. Setpoint is total window width in degrees (temp must be +/-window/2).'''
        new_channel = channel(channel_name,write_function=self._set_window)
        new_channel.write(self.window)
        return self._add_channel(new_channel)
    def add_channel_soak_settling_time(self,channel_name):
        '''channel_name represents soak timer elapsed time readback.'''
        new_channel = channel(channel_name,read_function=lambda: self.time)
        return self._add_channel(new_channel)
    def add_channel_max_air(self,channel_name):
        '''channel_name represents maximum airflow temperature setting.'''
        new_channel = channel(channel_name,write_function=self._set_max_air)
        new_channel.write(self.maxair)
        return self._add_channel(new_channel)
    def add_channel_max_air2dut(self,channel_name):
        '''channel_name represents maximum allowed temperature difference between airflow and dut setting.'''
        new_channel = channel(channel_name,write_function=self._set_max_air2dut)
        new_channel.write(self.air2dut)
        return self._add_channel(new_channel)
    def _set_max_air(self,value):
        self.air2dut = value
    def _set_max_air2dut(self,value):
        self.maxair = value
    def _set_window(self,value):
        '''Set allowed window to start soak timer.'''
        self.window = value
        txt = "WNDW " + str(self.window)
        self.get_interface().write((txt))
    def _set_soak(self,value):
        '''Set soak time in seconds'''
        self.soak = value
        txt = "SOAK " + str(self.soak)
        self.get_interface().write((txt))
    def off(self):
        '''Turn off airflow and compressor, lift head, reset limits'''
        self.get_interface().write(("FLOW 0;"))
        self.get_interface().write(("HEAD 0;"))
        self.get_interface().write(("COOL 0;"))
        self.get_interface().write((f"ULIM {155};"))
    def _write_temperature(self,value):
        '''Set temperature'''
        self.setpoint = value
        if value < 20:
            self.range = 2
        elif value < 30:
            self.range = 1
        else:
            self.range = 0
        self.get_interface().write(("SETN " + str(self.range)))
        txt = "SETP " + str(self.setpoint) + ";WNDW " + str(self.window) + ";ADMD " + str(self.air2dut)
        txt += ";ULIM " + str(self.maxair) + "; SOAK " + str(self.soak) +";"
        self.get_interface().write((txt))
        self.get_interface().write(("FLOW 1"))
        self.time = 0
        self._wait_settle()
    def _wait_settle(self):
        '''Block until temperature has been within window for soak time.'''
        settled = False
        while(settled == False):
            time.sleep(5)
            self.time += 5
            print("Waiting To Settle to " + str(self.setpoint) + " : "+ str(self.time) + "s", end=' ')
            tecr = self.get_interface().ask(("TECR?"))
            if ((int(tecr) & 1) == 1):
                settled = True
