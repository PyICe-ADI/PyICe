from .oscilloscope import oscilloscope
from ..lab_core import *
import time, math
from deprecated import deprecated
try:
    from numpy import fromiter, dtype
    numpy_missing = False
except ImportError as e:
    numpy_missing = True

class agilent_3034a(oscilloscope):
    '''Agilent 4-channel mixed signal DSO'''
    def __init__(self, interface_visa, force_trigger=False, reset=False, timeout=10): # 10 seconds recommended in programmer"s manual page 63
        '''interface_visa'''
        self._base_name = "agilent_3034a"
        scpi_instrument.__init__(self,f"agilent_3034a @ {interface_visa}")
        delegator.__init__(self)  # Clears self._interfaces list, so must happen before add_interface_visa(). --FL 12/21/2016
        self.add_interface_visa(interface_visa, timeout = timeout)
        if reset:
            self.get_interface().clear()
            self.reset() # Get to a known state for full automation if so desired.
            time.sleep(1)  #Sleep after a reset. Scope might crash without this.
            # self.get_interface().write(":CHANnel1:DISPlay OFF") # Factpry Default enables Channel 1 - thanks factory man!
            # self.trigger_force() #xincrement and possibly other SCPI queries time out with no waveform data captured, but it's hard to reliably determine if
        # self.get_interface().write(":WAVeform:FORMat ASCII")
        # self.get_interface().write(":WAVeform:FORMat WORD")
        self.get_interface().write(":WAVeform:FORMat BYTE")
        self.get_interface().write(":WAVeform:POINts:MODE RAW") #maximum number of points by default (scope must be stopped)
        self.force_trigger = force_trigger
        self.Xchannels = {}##############################################DELETE ME after rollout
        self.Ychannels = {}##############################################DELETE ME after rollout
        
        # Make sure time channel reads don't crash before acquisition
        self.time_info                  = {}
        self.time_info["points"]        = None
        self.time_info["increment"]     = None
        self.time_info["origin"]        = None
        self.time_info["reference"]     = None
        self.time_info["scale"]         = None
        self.time_info["enable_status"] = None

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def add_Ychannel(self, name, number):
        '''Add named channel to instrument. num is 1-4.'''
        assert number in range(1,5)
        self.Ychannels[number]                          = {}
        self.Ychannels[number]["main_channel"]          = channel(name, read_function=lambda: self._read_scope_channel(number))
        self.Ychannels[number]["probe_gain_channel"]    = self.add_channel_probe_gain(name=f"{name}_probe_gain", number=number)
        self.Ychannels[number]["BWLimit_channel"]       = self.add_channel_BWLimit(name=f"{name}_BWlimit", number=number)
        self.Ychannels[number]["invert_channel"]        = self.add_channel_invert(name=f"{name}_invert", number=number)
        self.Ychannels[number]["Yrange_channel"]        = self.add_channel_Yrange(name=f"{name}_Yrange", number=number)
        self.Ychannels[number]["Yoffset_channel"]       = self.add_channel_Yoffset(name=f"{name}_Yoffset", number=number)
        self.Ychannels[number]["Yrange_readback"]       = self.add_channel_Yrange_readback(name=f"{name}_Yrange_readback", number=number)
        self.Ychannels[number]["Yoffset_readback"]      = self.add_channel_Yoffset_readback(name=f"{name}_Yoffset_readback", number=number)
        self.Ychannels[number]["impedance_channel"]     = self.add_channel_impedance(name=f"{name}_Impedance", number=number)
        self.Ychannels[number]["units_channel"]         = self.add_channel_units(name=f"{name}_units", number=number)
        self.Ychannels[number]["coupling_channel"]      = self.add_channel_coupling(name=f"{name}_coupling", number=number)
        self.Ychannels[number]["display_channel"]       = self.add_channel_display(name=f"{name}_display", number=number)
        self.Ychannels[number]["main_channel"].set_delegator(self)
        main_channel = self._add_channel(self.Ychannels[number]["main_channel"])
        main_channel.set_attribute('dependent_physical_channels',(number,))
        self.Ychannels[number]["display_channel"].write(True) # legacy script support
        return self.Ychannels

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def purge_all_Xchannels(self):
        for channel in self.Xchannels:
            self.remove_channel(self.Xchannels[channel])

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def purge_all_Ychannels(self):
        remove_channels = []
        for channel_number in self.Ychannels:
            for channel_name in self.Ychannels[channel_number]:
                self.remove_channel(self.Ychannels[channel_number][channel_name])
                remove_channels.append({"channel_number":channel_number, "channel_name":channel_name})
        for remove_channel in remove_channels:                                                      # This can't be done in the loop
            del self.Ychannels[remove_channel["channel_number"]][remove_channel["channel_name"]]    # Iterator size not allowed to change dynamically.

    def disable_all_Ychannels(self):
        for number in [1,2,3,4]:
            self.channel_display(number=number, value=False)

    def enable_channels(self, channels):
        if len(channels) > 4:
            raise Exception(f"\n\nAgilent 3034a too many channels specified for displaying: {channels}")
        for channel_number in channels:
            if channel_number in [1,2,3,4]:
                self.channel_display(number=channel_number, value=True)
            else:
                raise Exception(f"\n\nAgilent 3034a Can't enable channel {channel_number}, physically doesn't exist.")
        for channel_number in list(set([1,2,3,4]) - set(channels)):
            self.channel_display(number=channel_number, value=False)

    def resync_scope(self):
        '''call at the top of collect to reconfigure physical instrument to the test's used channels.  Resets the scope.
        Requires every single oscilloscope channel be loaded with the channel attribute 'dependent_physical_channels', in turn
        containing a tuple of all channels required to be turned on. (None,) is acceptable for timebase channels, etc.'''
        self.get_interface().clear()  #Clear command in \deps\usbtmc\usmtmc.py.  Helps if the scope is not responding because it was asked about data that isn't there because it didn't trigger.
        self.reset()
        time.sleep(1)
        self.get_interface().write(':SYSTem:MENU OFF')          #Turn off the softkey menu so that channel info displays on the bottom.  This maybe could have worked in just the _init_ as once it's done once it appears to stick through reseting and clearing the scope.
        self.get_interface().write(":WAVeform:FORMat BYTE")
        self.get_interface().write(":WAVeform:POINts:MODE RAW") #maximum number of points by default (scope must be stopped)
        enabled_channels = []
        for ch in self.get_all_channels_list():
            try:
                for phych in ch.get_attribute('dependent_physical_channels'):
                    if phych is None: continue
                    enabled_channels.append(phych)
            except ChannelAttributeException as e:
                raise Exception(f'stowe_oscilloscopes requires "dependent_physical_channels" attribute of all scope channnels. Scope driver not in compliance w.r.t {ch.get_name()}. Contact PyICe-developers@analog.com for more information.')
        enabled_unique = set(enabled_channels)
        self.disable_all_Ychannels()
        self.enable_channels(enabled_unique)

    def setup_channels(self, scope_channels, prefix="scope"):
        '''Shortcut to quickly setup scope channels for most common use cases.  If vector data is not desired when using a measurement channels, manual setup of channels is required.'''
        for channel in scope_channels:
            self.add_Ychannel_waveform(name=channel, number=scope_channels[channel])
        self.add_all_timebase_trigger_aquisition_channels(prefix=prefix)

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def add_Xchannels(self, prefix):
        self.Xchannels["Xrange"]                        = self.add_channel_Xrange(name=f"{prefix}_Xrange")
        self.Xchannels["Xposition"]                     = self.add_channel_Xposition(name=f"{prefix}_Xposition")
        self.Xchannels["Xreference"]                    = self.add_channel_Xreference(name=f"{prefix}_Xreference")
        self.Xchannels["Xrange_readback"]               = self.add_channel_Xrange_readback(name=f"{prefix}_Xrange_readback")
        self.Xchannels["Xposition_readback"]            = self.add_channel_Xposition_readback(name=f"{prefix}_Xposition_readback")
        self.Xchannels["Xreference_readback"]           = self.add_channel_Xreference_readback(name=f"{prefix}_Xreference_readback")
        self.Xchannels["triggerlevel"]                  = self.add_channel_triggerlevel(name=f"{prefix}_trigger_level")
        self.Xchannels["triggermode"]                   = self.add_channel_triggermode(name=f"{prefix}_trigger_mode")
        self.Xchannels["triggerslope"]                  = self.add_channel_triggerslope(name=f"{prefix}_trigger_slope")
        self.Xchannels["triggersource"]                 = self.add_channel_triggersource(name=f"{prefix}_trigger_source")
        self.Xchannels["triggertype"]                   = self.add_channel_triggertype(name=f"{prefix}_trigger_type")
        self.Xchannels["acquire_type"]                  = self.add_channel_acquire_type(name=f"{prefix}_acquire_type")
        self.Xchannels["acquire_count"]                 = self.add_channel_acquire_count(name=f"{prefix}_acquire_count")
        self.Xchannels["pointcount"]                    = self.add_channel_pointcount(name=f"{prefix}_points_count")
        self.Xchannels["pointcount_readback"]           = self.add_channel_pointcount_readback(name=f"{prefix}_points_count_readback")
        self.Xchannels["runmode"]                       = self.add_channel_runmode(name=f"{prefix}_run_mode")
        self.Xchannels["time"]                          = self.add_channel_time(name=f"{prefix}_timedata")
        self.Xchannels["trigger_glitch_range"]          = self.add_channel_trigger_glitch_range(name=f"{prefix}_glitch_range")
        self.Xchannels["trigger_glitch_level"]          = self.add_channel_trigger_glitch_level(name=f"{prefix}_glitch_level")
        self.Xchannels["trigger_glitch_source"]         = self.add_channel_trigger_glitch_source(name=f"{prefix}_glitch_source")
        self.Xchannels["trigger_glitch_lessthan"]       = self.add_channel_trigger_glitch_lessthan(name=f"{prefix}_glitch_lessthan")
        self.Xchannels["trigger_glitch_polarity"]       = self.add_channel_trigger_glitch_polarity(name=f"{prefix}_glitch_polarity")
        self.Xchannels["trigger_glitch_qualifier"]      = self.add_channel_trigger_glitch_qualifier(name=f"{prefix}_glitch_qualifier")
        self.Xchannels["trigger_glitch_greaterthan"]    = self.add_channel_trigger_glitch_greaterthan(name=f"{prefix}_glitch_greaterthan")
        self.Xchannels["trigger_runt_polarity"]         = self.add_channel_trigger_runt_polarity(name=f"{prefix}_runt_polarity")
        self.Xchannels["trigger_runt_qualifier"]        = self.add_channel_trigger_runt_qualifier(name=f"{prefix}_runt_qualifier")
        self.Xchannels["trigger_runt_source"]           = self.add_channel_trigger_runt_source(name=f"{prefix}_runt_source")
        self.Xchannels["trigger_runt_time"]             = self.add_channel_trigger_runt_time(name=f"{prefix}_runt_time")
        self.Xchannels["trigger_runt_level_high"]       = self.add_channel_trigger_runt_level_high(name=f"{prefix}_trigger_runt_level_high")
        self.Xchannels["trigger_runt_level_low"]        = self.add_channel_trigger_runt_level_low(name=f"{prefix}_trigger_runt_level_low")
        self.Xchannels["trigger_HFReject"]              = self.add_channel_trigger_HFReject(name=f"{prefix}_trigger_HFReject")
        return self.Xchannels

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def get_Xchannels(self):
        return self.Xchannels

    @deprecated(version='47', reason="You are using old scope driver methods.  Consider updating to new scope binding.  See https://confluence.analog.com/display/stowe/Preferred+Practices")
    def add_channel_time(self,name):
        def compute_x_points(self):
            '''Data conversion:
            voltage = [(data value - yreference) * yincrement] + yorigin
            time = [(data point number - xreference) * xincrement] + xorigin'''
            xpoints = [(x - self.time_info["reference"]) * self.time_info["increment"] + self.time_info["origin"] for x in range(self.time_info["points"])]
            return xpoints
        time_channel = channel(name, read_function=lambda: compute_x_points(self))
        time_channel.set_delegator(self)
        self._add_channel(time_channel)
        time_channel.set_attribute('dependent_physical_channels',(None,))
        def get_time_info(self):
            return self.time_info
        time_info = channel(name + "_info", read_function=lambda: get_time_info(self))
        time_info.set_delegator(self)
        self._add_channel(time_info)
        time_info.set_attribute('dependent_physical_channels',(None,))
        return time_channel

    ###############################################New Add Channel Methods####################################################
    def add_Ychannel_waveform(self, name, number):
        '''Add named waveform channels to instrument. num is 1-4.  Add all control and readback channels by calling add_Ycontrol_Yreadback_channels()'''
        assert number in range(1,5)
        new_channel = channel(name, read_function=lambda: self._read_scope_channel(number))
        new_channel.set_delegator(self)  ##########################what does this do?
        self._add_channel(new_channel)
        if not numpy_missing:
            new_channel._set_type_affinity('PyICeBLOB')
        else:
            new_channel._set_type_affinity('PyICeFloatList')
        new_channel.set_attribute('dependent_physical_channels',(number,))
        self.add_Ycontrol_Yreadback_channels(name, number)
        return new_channel

    def add_Ycontrol_Yreadback_channels(self, name, number):
        '''Add named channel control and readback channels to instrument. num is 1-4.
        Use if control and readback channels are needed to set up a measurment and the actual waveform data is not logged.'''
        assert number in range(1,5)
        # Add Control Channels
        self.add_channel_probe_gain(name=f"{name}_probe_gain", number=number)
        self.add_channel_BWLimit(name=f"{name}_BWlimit", number=number)
        self.add_channel_invert(name=f"{name}_invert", number=number)
        self.add_channel_Yrange(name=f"{name}_Yrange", number=number)
        self.add_channel_Yoffset(name=f"{name}_Yoffset", number=number)
        self.add_channel_impedance(name=f"{name}_Impedance", number=number)
        self.add_channel_units(name=f"{name}_units", number=number)
        self.add_channel_coupling(name=f"{name}_coupling", number=number)
        self.add_channel_display(name=f"{name}_display", number=number)
        # Add Readback channels
        self.add_channel_Yrange_readback(name=f"{name}_Yrange_readback", number=number)
        self.add_channel_Yoffset_readback(name=f"{name}_Yoffset_readback", number=number)

    def add_Xcontrol_Xreadback_channels(self, prefix):
        # Add Control Channels
        self.add_channel_Xrange(name=f"{prefix}_Xrange")
        self.add_channel_Xposition(name=f"{prefix}_Xposition")
        self.add_channel_Xreference(name=f"{prefix}_Xreference")
        # Add Readback channels
        self.add_channel_Xrange_readback(name=f"{prefix}_Xrange_readback")
        self.add_channel_Xposition_readback(name=f"{prefix}_Xposition_readback")
        self.add_channel_Xreference_readback(name=f"{prefix}_Xreference_readback")

    def add_trigger_channels(self, prefix):
        self.add_channel_triggerlevel(name=f"{prefix}_trigger_level")
        self.add_channel_triggermode(name=f"{prefix}_trigger_mode")
        self.add_channel_triggerslope(name=f"{prefix}_trigger_slope")
        self.add_channel_triggersource(name=f"{prefix}_trigger_source")
        self.add_channel_triggertype(name=f"{prefix}_trigger_type")
        self.add_channel_trigger_glitch_range(name=f"{prefix}_glitch_range")
        self.add_channel_trigger_glitch_level(name=f"{prefix}_glitch_level")
        self.add_channel_trigger_glitch_source(name=f"{prefix}_glitch_source")
        self.add_channel_trigger_glitch_lessthan(name=f"{prefix}_glitch_lessthan")
        self.add_channel_trigger_glitch_polarity(name=f"{prefix}_glitch_polarity")
        self.add_channel_trigger_glitch_qualifier(name=f"{prefix}_glitch_qualifier")
        self.add_channel_trigger_glitch_greaterthan(name=f"{prefix}_glitch_greaterthan")
        self.add_channel_trigger_runt_polarity(name=f"{prefix}_runt_polarity")
        self.add_channel_trigger_runt_qualifier(name=f"{prefix}_runt_qualifier")
        self.add_channel_trigger_runt_source(name=f"{prefix}_runt_source")
        self.add_channel_trigger_runt_time(name=f"{prefix}_runt_time")
        self.add_channel_trigger_runt_level_high(name=f"{prefix}_trigger_runt_level_high")
        self.add_channel_trigger_runt_level_low(name=f"{prefix}_trigger_runt_level_low")
        self.add_channel_trigger_HFReject(name=f"{prefix}_trigger_HFReject")
        self.add_channel_trigger_pattern(name=f"{prefix}_pattern")
        self.add_channel_trigger_pattern_format(name=f"{prefix}_pattern_format")
        self.add_channel_trigger_pattern_greaterthan(name=f"{prefix}_pattern_greaterthan")
        self.add_channel_trigger_pattern_lessthan(name=f"{prefix}_pattern_lessthan")
        self.add_channel_trigger_pattern_qualifier(name=f"{prefix}_pattern_qualifier")
        self.add_channel_trigger_pattern_range(name=f"{prefix}_pattern_range")

    def add_aquire_channels(self, prefix):
        self.add_channel_acquire_type(name=f"{prefix}_acquire_type")
        self.add_channel_acquire_count(name=f"{prefix}_acquire_count")

    def add_channel_timebase(self,name):
        def compute_x_points(self):
            '''Data conversion:
            voltage = [(data value - yreference) * yincrement] + yorigin
            time = [(data point number - xreference) * xincrement] + xorigin'''
            time_info = self._read_scope_timebase_info()
            if not numpy_missing:
            # xpoints   = [(x - time_info["reference"]) * time_info["increment"] + time_info["origin"] for x in range(time_info["points"])]
                xpoints_gen   = map(lambda x: (x - time_info["reference"]) * time_info["increment"] + time_info["origin"], range(time_info["points"]))
                return fromiter(xpoints_gen, dtype=dtype('<d'))
            return [(x - time_info["reference"]) * time_info["increment"] + time_info["origin"] for x in range(time_info["points"])]
                
        new_channel = channel(name, read_function=lambda: compute_x_points(self))
        new_channel.set_delegator(self)
        self._add_channel(new_channel)
        if not numpy_missing:
            new_channel._set_type_affinity('PyICeBLOB')
        else:
            new_channel._set_type_affinity('PyICeFloatList')
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_time_info(self, name):  ## Obsolete?  Hasn't been in the logger since Jan 2021.
        new_channel = channel(name, read_function=lambda: self._read_scope_timebase_info())
        new_channel.set_delegator(self)
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def _read_scope_timebase_info(self):
        #DJS 2021/12/09. This method is almost identical to _read_scope_time_info. This one is called from add_channel_timebase and add_channel_time_info. The other is called from the delegated read of the instrument. This one discards the results after the return while the other stores results in an instance variable. I don't understand why there are two copies of essentially the same thing.
    
        time_info = {}
        enable_status = {}
        for scope_channel_number in range(1,5):
            enable_status[scope_channel_number] = int(self.get_interface().ask(f":CHANnel{scope_channel_number}:DISPlay?"))     #Is the channel enabled?
        an_enabled_channel = [chnum for chnum,enstatus in enable_status.items() if enstatus][0]                                         #Pick the first enabled channel
        self.get_interface().write(f':WAVeform:SOURce CHANnel{an_enabled_channel}')                                                     #Set the first enabled channel as waveform source
        time_info["points"]         = int(self.get_interface().ask(":WAVeform:POINts?"))                                                # int(preamble[2])
        time_info["increment"]      = float(self.get_interface().ask(":WAVeform:XINCrement?"))                                          # float(preamble[4])
        time_info["origin"]         = float(self.get_interface().ask(":WAVeform:XORigin?"))                                             # float(preamble[5])
        time_info["reference"]      = float(self.get_interface().ask(":WAVeform:XREFerence?"))                                          # float(preamble[6])
        time_info["scale"]          = time_info["increment"] * time_info["points"] / 10
        time_info["enable_status"]  = enable_status
        return time_info

    def add_all_timebase_trigger_aquisition_channels(self, prefix="scope"):
        self.add_Xcontrol_Xreadback_channels(prefix)
        self.add_trigger_channels(prefix)
        self.add_aquire_channels(prefix)
        self.add_channel_pointcount(name=f"{prefix}_points_count")
        self.add_channel_pointcount_readback(name=f"{prefix}_points_count_readback")
        self.add_channel_runmode(name=f"{prefix}_run_mode")
        self.add_channel_timebase(name=f"{prefix}_timedata")
        # self.add_channel_timebase_info(name=f"{prefix}_timedata_info")  Obsolete?  Hasn't been in the logger since Jan 2021.
    ###############################################END New Add Channel Methods####################################################

    def set_points(self, points):
        '''set the number of points returned by read_channel() or read_channels() points must be in range [100,250,500] or [1000,2000,5000]*10^[0-4] or [8000000]'''
        allowed_points = [100,250,500]
        allowed_points.extend(lab_utils.decadeListRange([1000,2000,5000],4))
        allowed_points.extend((8000000,))
        if points not in allowed_points:
            raise ValueError(f"\n\n{self.get_name()}: set_points: points argument muse be in: {allowed_points}")
        self.get_interface().write(f":WAVeform:POINts {points}")

    def get_channel_enable_status(self, number):
        return int(self.get_interface().ask(f":CHANnel{number}:DISPlay?"))

    def get_time_base(self):
        return float(self.get_interface().ask(":TIMebase:RANGe?")) / 10 # Always 10 horizontal divisions

    def _set_runmode(self, value):
        value = value.upper()
        if value not in ["RUN", "STOP", "SINGLE"]:
            raise ValueError("\n\nRun mode must be one of: RUN, STOP, SINGLE")
        self.get_interface().write(f":{value}")
        if value in ["RUN", "SINGLE"]:
            # Wait until it arms
            # Not sure if this makes sense for run or not....
            xrange = float(self.get_interface().ask(f":TIMebase:RANGe?"))
            timeout = 9 + math.ceil(1.5*xrange)                 #timeout will be 10s for most captures but grows for long captures.  This allows AER to go high the first time RUN or SINGLE is written.
            timeout_time = time.time() + timeout
            while not int(self.get_interface().ask(":AER?")):   #Asking AER? clears AER.  If SINGLE/SINGLE or RUN/RUN is written without a trigger in between, AER won't be high, and the timeout exception is raised. Note: SINGLE/RUN/SINGLE/RUN etc. CAN be written without triggers in between and AER goes high each time.
                time.sleep(0.01)
                if time.time() > timeout_time:
                    raise Exception(f'AER is still low {timeout}s after writing two {value} commands in a row to the scope without a scope trigger in between')
        else:
            # Wait until it stops
            self.operation_complete()

    def trigger_force(self):
        # self.get_interface().write(":RUN;:TRIGger:FORCe")
        self._set_runmode('SINGLE')
        xrange = float(self.get_interface().ask(f":TIMebase:RANGe?"))
        time.sleep(1.5*xrange)
        self.get_interface().write(":TRIGger:FORCe")
        while(True):
            if self.scope_stopped():
                #Stopped!
                break
        time.sleep(0.1) #Sleep additional .1s after scope stops
        # self.operation_complete()

    # def digitize(self):
        # self.get_interface().write(":DIGitize")
        # # self.operation_complete()

    def _read_scope_time_info(self):
        # print('time info')
        # print(self.get_interface().ask('WAV:SOURCE?'))
        # print(self.get_interface().ask('WAV:PRE?'))
        
        #DJS 2021/12/09. This method is almost identical to _read_scope_timebase_info. This one is called from the delegated read of the instrument. The other is called from add_channel_timebase and add_channel_time_info. This one stores results in an instance variable while the other discards the results after the return. I don't understand why there are two copies of essentially the same thing.
        
        self.time_info                = {}
        enable_status = {}
        for scope_channel_number in range(1,5):
            enable_status[scope_channel_number] = int(self.get_interface().ask(f":CHANnel{scope_channel_number}:DISPlay?"))
        an_enabled_channel = [chnum for chnum,enstatus in enable_status.items() if enstatus][0]       #Pick the first enabled channel
        self.get_interface().write(f':WAVeform:SOURce CHANnel{an_enabled_channel}')                                     #Set the first enabled channel as waveform source
        self.time_info["points"]      = int(self.get_interface().ask(":WAVeform:POINts?"))         # int(preamble[2])
        self.time_info["increment"]   = float(self.get_interface().ask(":WAVeform:XINCrement?"))   # float(preamble[4])
        self.time_info["origin"]      = float(self.get_interface().ask(":WAVeform:XORigin?"))      # float(preamble[5])
        self.time_info["reference"]   = float(self.get_interface().ask(":WAVeform:XREFerence?"))   # float(preamble[6])
        self.time_info["scale"]       = self.time_info["increment"] * self.time_info["points"] / 10
        self.time_info["enable_status"] = enable_status

    def _read_scope_channel(self, scope_channel_number):
        '''return list of y-axis points for named channel
            list will be datalogged by logger as a string in a single cell in the table
            trigger=False can by used to suppress acquisition of new data by the instrument so that
            data from a single trigger may be retrieved from each of the four channels in turn by read_channels()
        '''
        self.get_interface().write(f':WAVeform:SOURce CHANnel{scope_channel_number}')
        return self.fetch_waveform_data()
        # self.get_interface().write(':WAVeform:DATA?')
        # raw_data = self.get_interface().read_raw()
        # preamble = self.get_interface().ask(':WAVeform:PREamble?')

        # #Example: "#800027579 4.03266e-002, 1.25647e-004, 1.25647e-004, 1.25647e-004,......."
        # raw_data = raw_data[10:] #remove header
        # raw_data = raw_data.decode().split(",")
        # data = [float(x) for x in raw_data]
        # #TODO - implement binary transfer if speed becomes a problem
        # return data

    def scope_stopped(self):
        run_msk = 1 << 3
        cond = int(self.get_interface().ask(":OPERegister:CONDition?"))  #From Keysight app note. Is this really even a SCPI parse tree path???
        return (cond & run_msk) != run_msk

    def read_delegated_channel_list(self, channels):
        if self.force_trigger:
            self.trigger_force()
        results = results_ord_dict()
        timeout = 10
        last_remaining_time = timeout-1
        timeout_time = time.time() + timeout
        while(True):
            if self.scope_stopped():
                #Stopped!
                self._read_scope_time_info()
                for channel in channels:
                    results[channel.get_name()] = channel.read_without_delegator()
                break
            elif time.time() > timeout_time:
                for channel in channels:
                    # Trigger problem. Don't force bogus data
                    results[channel.get_name()] = None
                break
            else:
                remaining_time = int(timeout_time-time.time()) #round down
                if remaining_time < last_remaining_time:
                    last_remaining_time = remaining_time
                    print(f'Agilent Scope waiting for trigger: {remaining_time}')
                time.sleep(0.05)
        # self.digitize()
        # self.get_interface().write((":STOP")))# scope will timeout on :WAVeform:PREamble? if not "STOPped"
        # print("ACQ Complete: ", self.get_interface().ask((":ACQuire:COMPlete?")))
        return results

    def add_channel_probe_gain(self, name, number):
        def _set_probe_gain(number,value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f":CHANnel{number}:PROBe {value}")
        new_channel = channel(name, write_function=lambda value : _set_probe_gain(number, value))
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:PROBe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_BWLimit(self, name, number): #"Enable 25Mhz limit"
        def _set_BWLimit(number, value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f':CHANnel{number}:BWLimit {"ON" if value else "OFF"}')
        new_channel = integer_channel(name, size=1, write_function=lambda value: _set_BWLimit(number, value))
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:BWLimit?"))
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return self._add_channel(new_channel)

    def add_channel_trigger_HFReject(self, name):
        def _set_trigger_HFReject(value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f':TRIGger:HFReject {"ON" if value else "OFF"}')
        new_channel = integer_channel(name, size=1, write_function=lambda value: _set_trigger_HFReject(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:HFReject?"))
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return self._add_channel(new_channel)

    def add_channel_invert(self, name, number):
        def _set_invert(number, value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f':CHANnel{number}:INVert {"ON" if value else "OFF"}')
        new_channel = integer_channel(name, size=1, write_function=lambda value: _set_invert(number, value))
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:INVert?"))
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return self._add_channel(new_channel)

    def add_channel_Yrange(self, name, number):
        def _set_Yrange(number,value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f":CHANnel{number}:RANGe {value}")
        new_channel = channel(name, write_function=lambda value : _set_Yrange(number,value))
        # new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:RANGe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_Yoffset(self, name, number):
        def _set_Yoffset(number,value):
            # self.channel_display(number, True)   #Make sure the channel is on
            self.get_interface().write(f":CHANnel{number}:OFFSet {-value}")
        new_channel = channel(name, write_function=lambda value : _set_Yoffset(number,value))
        # new_channel._set_value(-1*self.get_interface().ask(f":CHANnel{number}:OFFSet?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_Yrange_readback(self, name, number):
        new_channel = channel(name, read_function=lambda : float(self.get_interface().ask(f":CHANnel{number}:RANGe?")))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_Yoffset_readback(self, name, number):
        new_channel = channel(name, read_function=lambda : -float(self.get_interface().ask(f":CHANnel{number}:OFFSet?")))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_impedance(self, name, number):
        def _set_impedance(number, value):
            # self.channel_display(number, True)   #Make sure the channel is on
            if value in [50, "50", 1000000, 1e6, "1000000", "1e6", "1M"]:
                value = "FIFTy" if value in [50, "50"] else "ONEMeg"
            else:
                raise ValueError("\n\nScope input impedance must be either 50, 1000000 or 1M")
            self.get_interface().write(f":CHANnel{number}:IMPedance {value}")
            # self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_impedance(number, value))
        new_channel.add_preset("50",    "50Ω")
        new_channel.add_preset("1M",    "1MΩ")
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:IMPedance?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_units(self, name, number):
        def _set_units(number, value):
            # self.channel_display(number, True)   #Make sure the channel is on
            if value.upper() in ["V", "A", "VOLTS", "AMPS"]:
                value = "VOLT" if value.upper() in ["V", "VOLTS"] else "AMPere"
            else:
                raise ValueError("\n\nUnits must be one of V, A, VOLTS, AMPS")
            self.get_interface().write(f":CHANnel{number}:UNITs {value}")
            # self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_units(number, value))
        new_channel.add_preset("VOLTS", "Volts")
        new_channel.add_preset("AMPS",  "Amperes")
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:UNITs?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_coupling(self, name, number):
        def _set_coupling(number, value):
            # self.channel_display(number, True)   #Make sure the channel is on
            if value.upper() not in ["AC", "DC"]:
                raise ValueError("\n\nUnits must be either AC or DC")
            self.get_interface().write(f":CHANnel{number}:COUPling {value}")
            # self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_coupling(number, value))
        new_channel.add_preset("AC", "AC")
        new_channel.add_preset("DC", "DC")
        new_channel._set_value(self.get_interface().ask(f":CHANnel{number}:COUPling?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_Xrange(self, name):
        new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":TIMebase:RANGe {value}"))
        # new_channel._set_value(self.get_interface().ask(f":TIMebase:RANGe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_Xposition(self, name):
        new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":TIMebase:POSition {-value}"))
        new_channel._set_value(-float(self.get_interface().ask(f":TIMebase:POSition?")))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_Xreference(self, name):
        def _set_xreference(value):
            if value.upper() not in ["LEFT", "CENTER", "RIGHT"]:
                raise ValueError("\n\nX reference must be one of must be one of: LEFT, CENTER, RIGHT")
            self.get_interface().write(f":TIMebase:REFerence {value}")
            # self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_xreference(value))
        new_channel.add_preset("LEFT",      "One Division from the left")
        new_channel.add_preset("CENTER",    "Screen Center")
        new_channel.add_preset("RIGHT",     "One Division from the right")
        new_channel._set_value(self.get_interface().ask(f":TIMebase:REFerence?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_Xrange_readback(self, name):
        new_channel = channel(name, read_function=lambda : float(self.get_interface().ask(f":TIMebase:RANGe?")))
        # new_channel._set_value(self.get_interface().ask(f":TIMebase:RANGe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_Xposition_readback(self, name):
        new_channel = channel(name, read_function=lambda : -float(self.get_interface().ask(f":TIMebase:POSition?")))
        # new_channel._set_value(-1*self.get_interface().ask(f":TIMebase:POSition?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_Xreference_readback(self, name):
        new_channel = channel(name, read_function=lambda : self.get_interface().ask(f":TIMebase:REFerence?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_runmode(self, name):
        new_channel = channel(name, write_function=lambda value : self._set_runmode(value))
        new_channel.add_preset("RUN",       "Free running mode")
        new_channel.add_preset("STOP",      "Stopped")
        new_channel.add_preset("SINGLE",    "Waiting for trigger")
        # new_channel._set_value(self.get_interface().ask(f":{value}"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_triggerlevel(self, name): # TODO Needs operation complete
        new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":TRIGger:LEVel {value}"))
        new_channel._set_value(self.get_interface().ask(f":TRIGger:LEVel?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_triggermode(self, name):
        def _set_triggermode(value):
            if value.upper() not in ["AUTO", "NORMAL"]:
                raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL")
            self.get_interface().write(f":TRIGger:SWEep {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_triggermode(value))
        new_channel.add_preset("AUTO",       "Find a trigger level")
        new_channel.add_preset("NORMAL",     "Use defined trigger level")
        new_channel._set_value(self.get_interface().ask(f":TRIGger:SWEep?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_triggerslope(self, name):
        def _set_triggerslope(value):
            if value.upper() not in ["NEGATIVE", "POSITIVE", "EITHER", "ALTERNATE"]:
                raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL, EITHER, ALTERNATE")
            self.get_interface().write(f":TRIGger:SLOPe {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_triggerslope(value))
        new_channel.add_preset("POSITIVE",      "Positive edges")
        new_channel.add_preset("NEGATIVE",      "Negative edges")
        new_channel.add_preset("EITHER",        "Either edge")
        new_channel.add_preset("ALTERNATE",     "Alternate between edges")
        new_channel._set_value(self.get_interface().ask(f":TRIGger:SLOPe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_triggersource(self, name):
        def _set_triggersource(value):
            valid_sources = ["EXT", "LINE", "WGEN", "CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4"]
            if value.upper() not in valid_sources:
                raise ValueError(f"\n\nTrigger mode must be one of: {valid_sources}")
            self.get_interface().write(f":TRIGger:SOURce {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_triggersource(value))
        new_channel.add_preset("EXT",       "External Trigger")
        new_channel.add_preset("LINE",      "Line Trigger")
        new_channel.add_preset("WGEN",      "Waveform Generator")
        new_channel.add_preset("CHANNEL1",  "Channel 1")
        new_channel.add_preset("CHANNEL2",  "Channel 2")
        new_channel.add_preset("CHANNEL3",  "Channel 3")
        new_channel.add_preset("CHANNEL4",  "Channel 4")
        new_channel._set_value(self.get_interface().ask(f":TRIGger:SOURce?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_acquire_type(self, name):
        def _set_acquiretype(value):
            if value.upper() not in ["NORMAL", "AVERAGE", "HRESOLUTION", "PEAK"]:
                raise ValueError("\n\nAcquire type must be one of: NORMAL, AVERAGE, HRESOLUTION, PEAK")
            self.get_interface().write(f":ACQuire:TYPE {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_acquiretype(value))
        new_channel.add_preset("NORMAL",        "Sets the oscilloscope in the normal mode")
        new_channel.add_preset("AVERAGE",       "sets the oscilloscope in the averaging mode. You can set the count by sending the :ACQuire:COUNt command followed by the number of averages. In this mode, the value for averages is an integer from 1 to 65536 (Acquire Count section of manual says 2..65326, setting to 1 results in Data Out of Range (SLM)). The COUNt value determines the number of averages that must be acquired")
        new_channel.add_preset("HRESOLUTION",   "Sets the oscilloscope in the high-resolution mode (also known as smoothing). This mode is used to reduce noise at slower sweep speeds where the digitizer samples faster than needed to fill memory for the displayed time range. For example, if the digitizer samples at 200 MSa/s, but the effective sample rate is 1 MSa/s (because of a slower sweep speed), only 1 out of every 200 samples needs to be stored. Instead of storing one sample (and throwing others away), the 200 samples are averaged together to provide the value for one display point. The slower the sweep speed, the greater the number of samples that are averaged together for each display point")
        new_channel.add_preset("PEAK",          "sets the oscilloscope in the peak detect mode. In this mode, :ACQuire:COUNt has no meaning")
        new_channel._set_value(self.get_interface().ask(f":ACQuire:TYPE?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_acquire_count(self, name):
        def _set_acquirecount(value):
            if value not in range(2,65536+1):
                raise ValueError("\n\nAcquire Count must be in [2..65536]")
            self.get_interface().write(f":ACQuire:COUNt {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_acquirecount(value))
        ######################################################################
        # This line is questionable - it might try to read before a trigger  #
        ######################################################################
        new_channel._set_value(self.get_interface().ask(f":ACQuire:COUNt?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_pointcount(self, name):
        new_channel = channel(name, write_function=lambda value : self.set_points(value))
        # new_channel._set_value(self.get_interface().ask(":WAVeform:POINts?"))  #Do not ask the scope for points when channel is created.  WAVeform:SOURce may be set to a channel that's off.
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_pointcount_readback(self, name):
        new_channel = channel(name, read_function=lambda : self.time_info["points"])
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_triggertype(self, name):
        def _set_triggertype(value):
            if value.upper() not in ["EDGE", "GLITCH", "PATTERN", "TV", "DELAY", "EBURST", "OR", "RUNT", "SHOLD", "TRANSITION", "SBUS1", "SBUS2", "USB"]:
                raise ValueError(f"\Sorry, I don't know what TRIGger:MODE {value} is. Must be one of  : EDGE, GLITCH, PATTERN, TV, DELAY, EBURST, OR, RUNT, SHOLD, TRANSITION, SBUS1, SBUS2, USB")
            self.get_interface().write(f":TRIGger:MODE {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_triggertype(value))
        new_channel.add_preset("EDGE",      "")
        new_channel.add_preset("GLITCH",    "")
        new_channel.add_preset("PATTERN",   "")
        new_channel.add_preset("TV",        "")
        new_channel.add_preset("DELAY",     "")
        new_channel.add_preset("EBURST",    "")
        new_channel.add_preset("OR",        "")
        new_channel.add_preset("RUNT",      "")
        new_channel.add_preset("SHOLD",     "")
        new_channel.add_preset("TRANSITION","")
        new_channel.add_preset("SBUS1",     "")
        new_channel.add_preset("SBUS2",     "")
        new_channel.add_preset("USB",       "")
        new_channel._set_value(self.get_interface().ask(f":TRIGger:MODE?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_pattern(self, name):
        def _set_trigger_pattern(value):
            self.get_interface().write(f":TRIGger:PATTern \"{value}\"")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value: _set_trigger_pattern(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:PATTern?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_pattern_qualifier(self, name):
        def _set_trigger_pattern_qualifier(value):
            if value not in ["ENTered", "GREaterthan", "LESSthan", "INRange", "OUTRange", "TIMeout"]:
                raise ValueError("\nTrigger pattern qualifier must be ENTered, GREaterthan, LESSthan, INRange, "
                                 "OUTRange, TIMeout")
            self.get_interface().write(f":TRIGger:PATTern:QUALifier {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_pattern_qualifier(value))
        new_channel.add_preset("ENTered", "")
        new_channel.add_preset("GREaterthan", "")
        new_channel.add_preset("LESSthan", "")
        new_channel.add_preset("INRange", "")
        new_channel.add_preset("OUTRange", "")
        new_channel.add_preset("TIMeout", "")
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:QUALifier?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_trigger_pattern_format(self, name):
        def _set_trigger_pattern_format(value):
            if value.upper() not in ['ASCII', 'HEX']:
                raise ValueError('\nTrigger pattern format must be ASCII or HEX')
            self.get_interface().write(f":TRIGger:PATTern:FORMat {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value: _set_trigger_pattern_format(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:PATTern:FORMat?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_pattern_greaterthan(self, name):
        def _set_trigger_pattern_greaterthan(value):
            self.get_interface().write(f":TRIGger:PATTern:GREaterthan {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value: _set_trigger_pattern_greaterthan(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:PATTern:GREaterthan?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel
    
    def add_channel_trigger_pattern_lessthan(self, name):
        def _set_trigger_pattern_lessthan(value):
            self.get_interface().write(f":TRIGger:PATTern:LESSthan {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value: _set_trigger_pattern_lessthan(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:PATTern:LESSthan?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_pattern_range(self, name):
        def _set_trigger_pattern_range(less_than, greater_than):
            self.get_interface().write(f":TRIGger:PATTern:RANGe {less_than:e},{greater_than:e}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda less_than,greater_than : _set_trigger_pattern_range(less_than,greater_than))
        new_channel._set_value(self.get_interface().ask(":TRIGger:PATTern:RANGe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_greaterthan(self, name):
        def _set_trigger_glitch_greaterthan(value):
            self.get_interface().write(f":TRIGger:GLITch:GREaterthan {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_greaterthan(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:GREaterthan?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_lessthan(self, name):
        def _set_trigger_glitch_lessthan(value):
            self.get_interface().write(f":TRIGger:GLITch:LESSthan {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_lessthan(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:LESSthan?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_level(self, name):
        def _set_trigger_glitch_level(value):
            self.get_interface().write(f":TRIGger:GLITch:LEVel {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_level(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:LEVel?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_source(self, name):
        def _set_trigger_glitch_source(value):
            self.get_interface().write(f":TRIGger:GLITch:SOURce {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_source(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:SOURce?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_polarity(self, name):
        def _set_trigger_glitch_polarity(value):
            if value.upper() not in ["POSITIVE", "NEGATIVE"]:
                raise ValueError("\nTrigger glitch polarity must be either POSITIVE or NEGATIVE")
            self.get_interface().write(f":TRIGger:GLITch:POLarity {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_polarity(value))
        new_channel.add_preset("POSITIVE", "")
        new_channel.add_preset("NEGATIVE", "")
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:POLarity?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_qualifier(self, name):
        def _set_trigger_glitch_qualifier(value):
            if value.upper() not in ["GREATERTHAN", "LESSTHAN", "RANGE"]:
                raise ValueError("\nTrigger glitch qualifier must be GREATERTHAN, LESSTHAN, or RANGE")
            self.get_interface().write(f":TRIGger:GLITch:QUALifier {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_glitch_qualifier(value))
        new_channel.add_preset("GREATERTHAN", "")
        new_channel.add_preset("LESSTHAN", "")
        new_channel.add_preset("RANGE", "")
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:QUALifier?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_glitch_range(self, name):
        def _set_trigger_glitch_range(less_than,greater_than):
            self.get_interface().write(f":TRIGger:GLITch:RANGe {less_than:e},{greater_than:e}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda less_than,greater_than : _set_trigger_glitch_range(less_than,greater_than))
        new_channel._set_value(self.get_interface().ask(":TRIGger:GLITch:RANGe?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel


    def add_channel_trigger_runt_polarity(self, name):
        def _set_trigger_runt_polarity(value):
            if value.upper() not in ["POSITIVE", "NEGATIVE", "EITHER"]:
                raise ValueError("\nTrigger runt polarity must be POSITIVE, NEGATIVE, or EITHER")
            self.get_interface().write(f":TRIGger:RUNT:POLarity {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_runt_polarity(value))
        new_channel.add_preset("POSITIVE", "")
        new_channel.add_preset("NEGATIVE", "")
        new_channel.add_preset("EITHER", "")
        new_channel._set_value(self.get_interface().ask(":TRIGger:RUNT:POLarity?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_runt_qualifier(self, name):
        def _set_trigger_runt_qualifier(value):
            if value.upper() not in ["GREATERTHAN", "LESSTHAN", "RANGE"]:
                raise ValueError("\nTrigger runt qualifier must be GREATERTHAN, LESSTHAN, or RANGE")
            self.get_interface().write(f":TRIGger:RUNT:QUALifier {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_runt_qualifier(value))
        new_channel.add_preset("GREATERTHAN", "")
        new_channel.add_preset("LESSTHAN", "")
        new_channel.add_preset("RANGE", "")
        new_channel._set_value(self.get_interface().ask(":TRIGger:RUNT:QUALifier?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_runt_source(self, name):
        def _set_trigger_runt_source(value):
            self.get_interface().write(f":TRIGger:RUNT:SOURce {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_runt_source(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:RUNT:SOURce?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_runt_time(self, name):
        def _set_trigger_runt_time(value):
            self.get_interface().write(f":TRIGger:RUNT:TIME {value}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_runt_time(value))
        new_channel._set_value(self.get_interface().ask(":TRIGger:RUNT:TIME?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_runt_level_high(self,name):
        def _set_trigger_level_high(value):
            source = self.get_interface().ask(":TRIGger:RUNT:SOURce?")
            self.get_interface().write(f":TRIGger:LEVel:HIGH {value}, {source}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_level_high(value))
        # new_channel = new_channel._set_value(self.get_interface().ask(f":TRIGger:LEVel:HIGH?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_trigger_runt_level_low(self,name):
        def _set_trigger_level_low(value):
            source = self.get_interface().ask(":TRIGger:RUNT:SOURce?")
            self.get_interface().write(f":TRIGger:LEVel:LOW {value}, {source}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda value : _set_trigger_level_low(value))
        # new_channel = new_channel._set_value(self.get_interface().ask(f":TRIGger:LEVel:LOW?"))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_meas_frequency(self, name, number):
        def _get_frequency_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope FREQUENCY measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:FREQuency?"))
        new_channel = channel(name, read_function = lambda : _get_frequency_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_dutycycle(self, name, number):
        def _get_dutycycle_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope DUTY CYCLE measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:DUTYcycle?"))
        new_channel = channel(name, read_function = lambda : _get_dutycycle_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_risetime(self, name, number):
        def _get_risetime_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope RISE TIME measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:RISetime?"))
        new_channel = channel(name, read_function = lambda : _get_risetime_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_falltime(self, name, number):
        def _get_falltime_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope FALL TIME measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:FALLtime?"))
        new_channel = channel(name, read_function = lambda : _get_falltime_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def channel_display(self, number, value):
        self.get_interface().write(f':CHANnel{number}:DISPlay {"ON" if value else "OFF"}')
        self.operation_complete()

    def add_channel_display(self, name, number):
        # def _set_display(channel_number, value):
            # self.get_interface().write(f':CHANnel{channel_number}:DISPlay {"ON" if value else "OFF"}')
            # self.operation_complete()
        new_channel = channel(name, write_function=lambda value: self.channel_display(number, value))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_delay(self, name, first_channel, second_channel):
        def _get_delay_measurement(first_channel, second_channel):
            self.get_interface().write(f":MEASure:SOURce CHANnel{first_channel},CHANnel{second_channel}")
            return float(self.get_interface().ask(":MEASure:DELay?")) if float(self.get_interface().ask(":MEASure:DELay?")) != 9.9e37 else float("Inf")
        new_channel = channel(name, read_function = lambda: _get_delay_measurement(first_channel, second_channel))
        self._add_channel(new_channel)
        self.add_channel_meas_delay_spec1(name=f"{name}_edge1_spec")
        self.add_channel_meas_delay_spec2(name=f"{name}_edge2_spec")
        self.add_channel_meas_define_abs_thresh(name=f"{name}_thresh1", number = first_channel)
        self.add_channel_meas_define_abs_thresh(name=f"{name}_thresh2", number = second_channel)
        new_channel.set_attribute('dependent_physical_channels',(first_channel, second_channel))
        return new_channel

    def add_channel_meas_delay_spec1(self, name):
        def _set_define_delay(edge_spec1):
            edge_spec = self.get_interface().ask(":MEASure:DEFine?").split(",")
            self.get_interface().write(f":MEASure:DEFine DELay,{edge_spec1},{edge_spec[1]}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda edge_spec1: _set_define_delay(edge_spec1))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_meas_delay_spec2(self, name):
        def _set_define_delay(edge_spec2):
            edge_spec = self.get_interface().ask(":MEASure:DEFine?").split(",")
            self.get_interface().write(f":MEASure:DEFine DELay,{edge_spec[0]},{edge_spec2}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda edge_spec2: _set_define_delay(edge_spec2))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(None,))
        return new_channel

    def add_channel_meas_define_abs_thresh(self, name, number):
        def _set_define_absolute_threshold(number, thresh):
            self.get_interface().write(f":MEASure:DEFine THResholds,ABSolute,{1.8*thresh},{thresh},{0.2*thresh},CHANnel{number}")
            self.operation_complete()
        new_channel = channel(name, write_function=lambda thresh: _set_define_absolute_threshold(number, thresh))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_pwidth(self, name, number):
        def _get_pwidth_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope PWIDTH measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:PWIDth?"))
        new_channel = channel(name, read_function = lambda : _get_pwidth_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_nwidth(self, name, number):
        def _get_nwidth_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope NWIDTH measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:NWIDth?"))
        new_channel = channel(name, read_function = lambda : _get_nwidth_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def add_channel_meas_vmax(self, name, number):
        def _get_vmax_measurement(number):
            if not self.scope_stopped():
                self._set_runmode('STOP')
                print("Warning: Scope VMAX measurement stopped the scope.  If this is unexpected check scope triggers.")
            self.get_interface().write(f":MEASure:SOURce CHANnel{number}")
            return float(self.get_interface().ask(":MEASure:VMAX?"))
        new_channel = channel(name, read_function = lambda : _get_vmax_measurement(number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels',(number,))
        return new_channel

    def save_to_usb(self, file_name):
        self.get_interface().write(":SAVE:IMAGe:FORMat BMP8bit")
        self.get_interface().write(f':SAVE:IMAGe:STARt "{file_name}"')
        self.operation_complete()

    #############################
    # Boneyard
    #############################

    # def add_channel_meas_delay(self, name, first_channel, first_trigger, second_channel, second_trigger):
        # def _get_delay_measurement():
            # return self.get_interface().read(":MEASure:DELay?")
            # self.get_interface().write(f":MEASure:DEFine DELay,{first_trigger}{first_channel},{second_trigger}{second_channel}")
            # self.get_interface().write(f":MEASure:DELay CHANnel{first_channel},CHANnel{second_channel}")
            # self.operation_complete()
        # new_channel = channel(name, read_function=lambda : _get_delay_measurement())
        # self._add_channel(new_channel)
        # return new_channel
