from ..lab_core import *

class hameg_4040(scpi_instrument):
    '''Hameg Lab Supply, model HMP 4040
        Four channel lab supply with GPIB interface.

        This instrument works by selecting the desired output with one command
        then sending "source" or "measure" commands to that output to set
        or measure voltage and current.
    '''
    def __init__(self,interface_visa):
        self._base_name = 'hameg_4040'
        # instrument.__init__(self,f'HMP4040 @  {interface_visa}')
        super(hameg_4040, self).__init__(f'HMP4040 @  {interface_visa}')
        self.add_interface_visa(interface_visa)
        #Reset the instrument to all outputs on, all voltages zero.
        #turn on all channels with zero output voltage
        #and one amp current limits (why?)
        self.get_interface().write("*RST")
        time.sleep(1)
        #print self.get_interface().resync()
        self.retries = 0
        self.hameg_suck_time = 0.03
    def __del__(self):
        '''turn OFF all channels'''
        for i in [1,2,3,4]:
            self.get_interface().write(f"INSTRUMENT:SELECT OUTPUT{i}")
            time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
            self.get_interface().write("OUTPUT:STATE OFF")
            time.sleep(0.25) # do no remove
        self.get_interface().close()
    def set_retries(self, retries):
        '''attempt to be robust to communication interface problems'''
        self.retries = retries
    def add_channel(self, channel_name, num, ilim = 1, delay = 0.5, add_extended_channels=True):
        '''add voltage forcing channel
            optionally add voltage force channel, current force channel "_ilim", enable "_enable", voltage sense "_vsense" and current sense "_isense"
            channel_name is channel name, ex: input_voltage
            num is channel number, allowed values are 1, 2, 3, 4
            ilim is optional current limit for this output, defaults to 1 amp.'''
        voltage_channel = self.add_channel_voltage(channel_name, num)
        self.write_channel(channel_name,0)
        voltage_channel.set_write_delay(delay)
        if add_extended_channels:
            current_channel = self.add_channel_current(channel_name + "_ilim", num)
            enable_channel = self.add_channel_enable(channel_name + "_enable", num)
            self.write_channel(channel_name + "_ilim",ilim)
            self.write_channel(channel_name + "_enable",True)
            self.add_channel_vsense(channel_name + "_vsense", num)
            self.add_channel_isense(channel_name + "_isense", num)
            current_channel.set_write_delay(delay)
            enable_channel.set_write_delay(delay)
        else:
            self._write_current(num,ilim)
            self._write_enable(num,True)
        return voltage_channel
    def add_channel_voltage(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda voltage: self._write_voltage(num,voltage))
        new_channel.set_attribute('hameg_number',num)
        new_channel.set_max_write_limit(32.05)
        new_channel.set_min_write_limit(0)
        new_channel.set_write_resolution(decimal_digits=3)
        return self._add_channel(new_channel)
    def add_channel_current(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda current: self._write_current(num,current))
        new_channel.set_attribute('hameg_number',num)
        new_channel.set_max_write_limit(10)
        new_channel.set_min_write_limit(0)
        new_channel.set_write_resolution(decimal_digits=4)
        return self._add_channel(new_channel)
    def add_channel_vsense(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_vsense(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_isense(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_isense(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_voltage_readback(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_voltage_readback(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_current_readback(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_current_readback(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_measured_voltage(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_measured_voltage(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_measured_current(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_measured_current(num))
        new_channel.set_attribute('hameg_number',num)
        return self._add_channel(new_channel)
    def add_channel_ovp(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda voltage: self._write_ovp(num, voltage))
        new_channel.set_attribute('hameg_number', num)
        return self._add_channel(new_channel)
    def add_channel_ovp_status(self, channel_name, num):
        new_channel = integer_channel(channel_name, size=1, read_function=lambda: self._read_ovp_status(num))
        new_channel.set_attribute('hameg_number', num)
        return self._add_channel(new_channel)
    def add_channel_fuse_status(self, channel_name, num):
        new_channel = integer_channel(channel_name, size=1, read_function= lambda: self._read_fuse_status(num))
        new_channel.set_attribute('hameg_number', num)
        return self._add_channel(new_channel)
    def add_channel_enable(self, channel_name, num):
        new_channel = integer_channel(channel_name, size=1, write_function= lambda state: self._write_enable(num,state))
        new_channel.set_attribute('hameg_number', num)
        return self._add_channel(new_channel)
    def add_channel_fuse_enable(self, channel_name, num, fuse_delay = 0):
        new_channel = integer_channel(channel_name, size=1, write_function= lambda state: self._write_fuse_enable(num, state, fuse_delay))
        new_channel.set_attribute('hameg_number', num)
        new_channel.set_write_delay(0.5)
        return self._add_channel(new_channel)
    def add_channel_fuse_link(self, channel_name, num):
        new_channel = channel(channel_name, write_function= lambda link_list: self._write_fuse_links(num, link_list))
        new_channel.set_attribute('hameg_number', num)
        new_channel.set_write_delay(0.5)
        return self._add_channel(new_channel)
    def add_channel_master_enable(self, channel_name):
        new_channel = integer_channel(channel_name, size=1, write_function=self._write_master_enable)
        new_channel.set_write_delay(0.5)
        return self._add_channel(new_channel)
    def add_channel_AWG(self, channel_name, num):
        trigger_channel = channel(channel_name + "_trigger", write_function=lambda value: self._run_arb(value, num))
        trigger_channel.set_attribute('hameg_number', num)
        pattern_channel = channel(channel_name + "_pattern", write_function=lambda pattern: self._set_arb_pattern(pattern, num))
        pattern_channel.set_attribute('hameg_number', num)
        reps_channel = channel(channel_name + "_reps", write_function=lambda arb_cycles: self._set_arb_reps(arb_cycles))
        reps_channel.set_attribute('hameg_number', num)
        self._add_channel(pattern_channel)
        self._add_channel(reps_channel)
        return trigger_channel
    def _set_arb_pattern(self, pattern, num):
        self._clear_arb_pattern()
        if not isinstance(pattern, list):
            raise ValueError("\n\nHameg ARB pattern must be a list.\n")
        if len(pattern) > 128*3: # 128 points times [voltage,current,time] sets
            raise ValueError("\n\nHameg ARB pattern must contain 128 points or fewer.\n")
        voltages = pattern[0::3]
        currents = pattern[1::3]
        times = pattern[2::3]
        bad_pattern = False
        for voltage in voltages:
            bad_pattern = bad_pattern or voltage < 0 or voltage > 32.05
        for current in currents:
            bad_pattern = bad_pattern or current < 0 or current > 10
        for timeval in times:
            bad_pattern = bad_pattern or timeval < 0.01 or timeval > 60
        if bad_pattern:
            raise ValueError("\n\nHameg ARB pattern error. Pattern: V,I,T,V,I,T... Volatge must be in [0,32.05], Currents must be in [0,10], Times must be in [0.01,60].\n")
        self.get_interface().write(f"ARBitrary:DATA {','.join(str(val) for val in pattern)}")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self._transfer_arb_pattern(num)
    def _clear_arb_pattern(self):
        self.get_interface().write("ARBitrary:CLEar")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
    def _transfer_arb_pattern(self, channel):
        self.get_interface().write(f"ARBitrary:TRANsfer {channel}")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
    def _run_arb(self, value, num):
        if value == "RUN":
            self.get_interface().write(f"ARBitrary:STARt {num}")
            time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
            self.get_interface().ask("*OPC?")
            time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
            
           # much more to do here like determining if OPC and changing state of channel to STANDBY..... or writing stop or whatever.
            
            
    def _start_arb(self, channel):
        self.get_interface().write(f"ARBitrary:STARt {channel}")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().write(f"OUTPut:STATe ON")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
    def _stop_arb(self, channel):
        self.get_interface().write(f"ARBitrary:STOP {channel}")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) # needed for hw serial on fast linux
    def _set_arb_reps(self, arb_cycles):
        '''Defines the repetition rate of the defined arbitrary waveform for the previous selected channel.
        Up to 255 repetitions are possible. If the repetition rate "0" is selected the arbitrary waveform of
        the previous selected channel will be repeated infinitely.'''
        '''SLM: What constitutes a Previous Selected Channel'''
        arb_cycles = 0 if "INF" in ncycle.upper() else int(arb_cycles)
        if arb_cycles not in range(256):
            raise ValueError("\n\nNumber of ARB cycles for Hameg 4040 must be [0..255] or something containing case agnostic substring 'inf'.\n")
        self.arb_cycles = arb_cycles
        self.get_interface().write(f"ARBitrary:REPetitions {arb_cycles}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
    def _write_fuse_enable(self, num, state, fuse_delay):
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        if state:
            self.get_interface().write("FUSE:STATe ON")
            time.sleep(self.hameg_suck_time)
        else:
            self.get_interface().write("FUSE:STATe OFF")
            time.sleep(self.hameg_suck_time)
        self.get_interface().write(f"FUSE:DELay {fuse_delay}")
        time.sleep(self.hameg_suck_time)
    def _write_fuse_links(self, num, link_list):
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        link_string = ""
        for supply in link_list:
            self.get_interface().write(f"FUSE:LINK {supply}")
            time.sleep(self.hameg_suck_time)
    def _write_voltage(self,num,voltage):
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().write(f"SOURce:VOLTage {voltage}")
        time.sleep(self.hameg_suck_time)
    def _write_current(self,num,current):
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().write(f"SOURce:CURRent {current}")
        time.sleep(self.hameg_suck_time)
    def _read_voltage_readback(self,num):
        '''returns the voltage setting as known by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data = float(self.get_interface().ask("SOURce:VOLTage?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_current_readback(self,num):
        '''returns the voltage setting as known by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data = float(self.get_interface().ask("SOURce:CURRent?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_measured_voltage(self,num):
        '''returns the voltage setting as known by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data = float(self.get_interface().ask("MEASure:VOLTage?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_measured_current(self,num):
        '''returns the voltage setting as known by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data = float(self.get_interface().ask("MEASure:CURRent?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_vsense(self,num):
        '''returns the voltage measured by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data =  float(self.get_interface().ask("MEASure:SCALar:VOLT:DC?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_isense(self,num):
        '''returns the current measured by the instrument'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                data = float( self.get_interface().ask("MEASure:SCALar:CURRent:DC?"))
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _write_ovp(self, num, voltage):
        '''Set a channel OVP level'''
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().write(f"VOLTage:PROTection:LEVel {voltage}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
    def _read_ovp(self, num):
        '''Read channel OVP level'''
        retry = 0
        while(retry <= self.retries):
            try:
                self.get_interface().write(f"INST:NSEL {num}")
                time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
                self.get_interface().ask("*OPC?")
                time.sleep(self.hameg_suck_time)
                data = float(self.get_interface().ask("VOLTage:PROTection:LEVel?"))
                time.sleep(self.hameg_suck_time)
                return data
            except Exception as e:
                print(e)
                print(f"Resync {self.get_name()}: {self.get_interface().resync()}")
                retry += 1
        raise e
    def _read_ovp_status(self, num):
        '''Read channel OVP level'''
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time)
        data = self.get_interface().ask("VOLTage:PROTection:TRIPped?")
        time.sleep(self.hameg_suck_time)
        return data
    def _read_fuse_status(self, num):
        '''read if fuse is tripped'''
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time)
        data = int(self.get_interface().ask("FUSE:TRIPed?"))
        time.sleep(self.hameg_suck_time)
        return data
    def _write_enable(self, num, state):
        #state is true/false
        self.get_interface().write(f"INST:NSEL {num}")
        time.sleep(self.hameg_suck_time) #needed for hw serial on fast linux
        self.get_interface().ask("*OPC?")
        time.sleep(self.hameg_suck_time)
        if state:
            self.get_interface().write("OUTPUT:STATE ON")
            time.sleep(self.hameg_suck_time)
        else:
            self.get_interface().write("OUTPUT:STATE OFF")
            time.sleep(self.hameg_suck_time)
    def _write_master_enable(self, state):
        "True -> turn on all enabled channels / False -> turn off all channels"
        if state:
            self.get_interface().write("OUTPut:GENeral ON")
            time.sleep(self.hameg_suck_time)
        else:
            self.get_interface().write("OUTPut:GENeral OFF")
            time.sleep(self.hameg_suck_time)