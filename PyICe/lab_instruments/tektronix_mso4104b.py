from PyICe.lab_core import *
import time

class tektronix_4104b(scpi_instrument,delegator):
    ''' Tektronix Oscilloscope - MDO/MSO/DPO4000/B '''
    def __init__(self, interface_visa, force_trigger=False, reset=False):
        '''interface_visa"'''
        self.str_encoding = 'latin-1'
        self._base_name = 'tektronix_4104B'
        delegator.__init__(self)
        scpi_instrument.__init__(self,f"tektronix_4104B @ {interface_visa}")
        self.add_interface_visa(interface_visa,timeout=10)
        if reset:
            self.reset() 
        self.get_interface().write(('DATA:ENCdg ASCIi').encode(self.str_encoding))
        self.get_interface().write(('DATA:WIDth 2').encode(self.str_encoding))
        self.get_interface().write(('HEADer 0').encode(self.str_encoding))
        self.force_trigger = force_trigger
   
    def add_Ychannel(self, channel_name, channel_number):
        '''Add named vertical channel to instrument.  channel_number is 1-4.'''
        assert isinstance(channel_number, int)
        scope_channel = channel(channel_name, read_function=lambda: self._read_scope_channel(channel_number))
        scope_channel.set_delegator(self)
        self._add_channel(scope_channel)
        self.get_interface().write((f'SELect:CH{channel_number} ON').encode(self.str_encoding)) # make sure it's on
        self.get_interface().write((f'DATA:SOUrce CH{channel_number}').encode(self.str_encoding))
        def get_channel_settings(channel_number):
            result              = {}
            result['scale']     = float(self.get_interface().ask((f"CH{channel_number}:SCALe?").encode(self.str_encoding)))
            result['offset']    = float(self.get_interface().ask((f"CH{channel_number}:OFFSet?").encode(self.str_encoding)))
            result['position']  = float(self.get_interface().ask((f"CH{channel_number}:POSition?").encode(self.str_encoding)))
            result['units']     = self.get_interface().ask((f"CH{channel_number}:YUNits?").encode(self.str_encoding)).decode(self.str_encoding).strip('"')
            result['label']     = self.get_interface().ask((f"CH{channel_number}:LABel?").encode(self.str_encoding)).decode(self.str_encoding).strip('"')
            result['bwlimit']   = float(self.get_interface().ask((f"CH{channel_number}:BANdwidth?").encode(self.str_encoding)))
            result['coupling']  = self.get_interface().ask((f"CH{channel_number}:COUPling?").encode(self.str_encoding)).decode(self.str_encoding)
            result['impedance'] = float(self.get_interface().ask((f"CH{channel_number}:TERmination?").encode(self.str_encoding)))
            return result
        # Extended Channels - for Writting Channel Settings
        self.add_channel_probe_gain(channel_name=f"{channel_name}_probe_gain", channel_number=channel_number)
        self.add_channel_BWLimit(channel_name=f"{channel_name}_BWlimit", channel_number=channel_number)
        self.add_channel_Yrange(channel_name=f"{channel_name}_Yrange", channel_number=channel_number)
        self.add_channel_Yoffset(channel_name=f"{channel_name}_Yoffset", channel_number=channel_number)
        self.add_channel_Yposition(channel_name=f"{channel_name}_Yposition", channel_number=channel_number)
        self.add_channel_impedance(channel_name=f"{channel_name}_Impedance", channel_number=channel_number)
        self.add_channel_units(channel_name=f"{channel_name}_units", channel_number=channel_number)
        self.add_channel_coupling(channel_name=f"{channel_name}_coupling", channel_number=channel_number)
        # Extended Channels - for Reading Channel Settings/Info
        trace_info = channel(channel_name + "_info", read_function=lambda: get_channel_settings(channel_number))
        trace_info.set_delegator(self)
        self._add_channel(trace_info)
        return scope_channel

    def add_Xchannels(self, prefix):
        self.add_channel_Xrange(channel_name=f"{prefix}_Xrange")
        self.add_channel_Xposition(channel_name=f"{prefix}_Xposition")
        self.add_channel_Xreference(channel_name=f"{prefix}_Xreference")
        self.add_channel_triggersource(channel_name=f"{prefix}_trigger_source")
        self.add_channel_triggerlevel(channel_name=f"{prefix}_trigger_level")
        self.add_channel_triggermode(channel_name=f"{prefix}_trigger_mode")
        self.add_channel_triggerslope(channel_name=f"{prefix}_trigger_slope")
        self.add_channel_acquire_type(channel_name=f"{prefix}_acquire_type")
        self.add_channel_acquire_count(channel_name=f"{prefix}_acquire_count")
        self.add_channel_pointcount(channel_name=f"{prefix}_points_count")
        self.add_channel_runmode(channel_name=f"{prefix}_run_mode")
        self.add_channel_time(channel_name=f"{prefix}_timedata")
        
    def add_channel_time(self, channel_name):
        def _compute_x_points(self):
            '''Data conversion:
            voltage = [(data value - yreference) * yincrement] + yorigin
            time = [(data point number - xreference) * xincrement] + xorigin'''
            xpoints = [(x - self.time_info["reference"]) * self.time_info["increment"] + self.time_info["origin"] for x in range(self.time_info["points"])]
            return xpoints
        time_channel = channel(channel_name, read_function=lambda: _compute_x_points(self))
        time_channel.set_delegator(self)
        self._add_channel(time_channel)
        def _get_time_info(self):
            return self.time_info
        time_info = channel(channel_name + "_info", read_function=lambda: _get_time_info(self))
        time_info.set_delegator(self)
        self._add_channel(time_info)
        return time_channel
    
    def set_points(self, stop, start = 1):
        ''' No. of acquired points: DATA:STOP value - DATA:STARt value should be less than time_info['points'] or WFMOutpre:NR_PT? '''
        self.get_interface().write((f"DATA:STARt {start}").encode(self.str_encoding))
        self.get_interface().write((f"DATA:STOP {stop}").encode(self.str_encoding))
        
    def get_channel_enable_status(self, channel_number):
        return int(self.get_interface().ask((f"SELect:CH{channel_number}?").encode(self.str_encoding)).decode(self.str_encoding))
    
    def get_time_base(self):
        return float(self.get_interface().ask("HORizontal:SCAle?").encode(self.str_encoding))
        
    def add_measurement_channel(self, channel_name, channel_number=1, measurement="FREQuency"):
        '''Add named channel, channel_number: 1-4 and mesurement type:
            AMPlitude|AREa|BURst|CARea|CMEan|CRMs|DELay|FALL|FREQuency|HIGH|HITS|LOW|MAXimum|MEAN|MEDian|MINImum|NDUty|NEDGECountNOVershoot|NPULSECount|NWIdth|PEAKHits|PEDGECount|
            PDUty|PERIod|PHAse|PK2Pk|POVershoot|PPULSECount|PWIdth|RISe|RMSSIGMA1|SIGMA2|SIGMA3|STDdev|WAVEFORMS '''
        new_channel = channel(channel_name + f"_Meas_{measurement}", read_function=lambda: self._read_immediate_measurement(channel_number, measurement))
        return self._add_channel(new_channel)
        
    def trigger_force(self):
        ''' Will only complete if TRIGger:STATE? is set to READy, otherwise ignored '''
        self.get_interface().write(("TRIGger FORCe").encode(self.str_encoding))
        self.operation_complete()
     
    def _read_scope_time_info(self):
        self.time_info                  = {}
        self.time_info['points']        = int(self.get_interface().ask(("WFMOutpre:NR_PT?").encode(self.str_encoding)))
        self.time_info['increment']     = float(self.get_interface().ask(("WFMOutpre:xincr?").encode(self.str_encoding)))
        self.time_info['origin']        = float(self.get_interface().ask(("WFMOutpre:xZEro?").encode(self.str_encoding)))
        self.time_info['reference']     = float(self.get_interface().ask(("WFMOutpre:PT_off?").encode(self.str_encoding)))
        self.time_info['scale']         = self.time_info['increment'] * self.time_info['points'] / 10
        self.time_info['enable_status'] = {}
        for channel_number in range(1,5):
            self.time_info['enable_status'][channel_number] = int(self.get_interface().ask((f"SELect:CH{channel_number}?").encode(self.str_encoding)))
    
    def _read_scope_channel(self, channel_number):
        '''return list of y-axis points for named channel
            list will be datalogged by logger as a string in a single cell in the table
            Data Conversion: yvalue = [(data value - yreference) * yincrement] + yorigin '''
        self.get_interface().write((f'DATA:SOUrce CH{channel_number}').encode(self.str_encoding))
        raw_data = self.get_interface().ask(('CURVe?').encode(self.str_encoding))
        raw_data = raw_data.decode(self.str_encoding)
        raw_data = raw_data.split(',')
        raw_data = [float(x) for x in raw_data]
        YMULT=float(self.get_interface().ask(('WFMOutpre:YMUlt?').encode(self.str_encoding)).decode(self.str_encoding))
        YOFF=float(self.get_interface().ask(('WFMOutpre:YOFf?').encode(self.str_encoding)).decode(self.str_encoding))
        YZERO=float(self.get_interface().ask(('WFMOutpre:YZEro?').encode(self.str_encoding)).decode(self.str_encoding))
        data = [(int(x)-YOFF)*YMULT+YZERO for x in raw_data]
        return data
   
    def read_delegated_channel_list(self,channels):
        if self.force_trigger:
            self.trigger_force()
        self.operation_complete()
        self._read_scope_time_info()
        results = results_ord_dict()
        for channel in channels:
            results[channel.get_name()] = channel.read_without_delegator()
        return results

    def add_channel_probe_gain(self, channel_name, channel_number):
        def _set_probe_gain(channel_number, value):
            value = 1/value 
            self.get_interface().write((f"CH{channel_number}:PRObe:GAIN {value}").encode(self.str_encoding))
        new_channel = channel(channel_name, write_function=lambda value : _set_probe_gain(channel_number, value))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_BWLimit(self, channel_name, channel_number):
        ''' Available bandwidth limits vary by model and are also influenced by probes '''
        def _set_BWLimit(channel_number, value):
            if value in ["ON", "OFF"]:   # Agilent valid arguments are ON (25MHZ) or OFF (Full)
                value = 20e6 if value == "ON" else "FULL"
            if value not in ["FULL", 250e6, 20e6]:
                raise ValueError("\n\nBandwidth Limit Setting must be one of: FULL, 250e6 or 20e6")
            self.get_interface().write((f"CH{channel_number}:BANdwidth {value}").encode(self.str_encoding))
        new_channel = channel(channel_name, write_function=lambda value : _set_BWLimit(channel_number, value))
        new_channel.add_preset("FULL",    "Enable Full BWLimit")
        new_channel.add_preset(250e6,     "Set to 250MHz BWLimit")
        new_channel.add_preset(20e6,      "Set to 20MHz BWLimit")
        self._add_channel(new_channel)
        return new_channel

    def add_channel_Yrange(self, channel_name, channel_number):
        ''' Range = Scale x 8? '''    
        def _set_Yrange(channel_number, value):
            value = value/8
            self.get_interface().write((f"CH{channel_number}:SCAle {value}").encode(self.str_encoding))
        new_channel = channel(channel_name, write_function=lambda value : _set_Yrange(channel_number, value))
        self._add_channel(new_channel)
        return new_channel
        
    def add_channel_Yscale(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda value : self.get_interface().write((f"CH{channel_number}:SCAle {value}").encode(self.str_encoding)))
        self._add_channel(new_channel)
        return new_channel
            
    def add_channel_Yoffset(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda value : self.get_interface().write((f"CH{channel_number}:OFFSet {value}").encode(self.str_encoding)))
        self._add_channel(new_channel)
        return new_channel
        
    def add_channel_Yposition(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda value : self.get_interface().write((f"CH{channel_number}:POSition {value}").encode(self.str_encoding)))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_impedance(self, channel_name, channel_number):
        def _set_impedance(channel_number, value):
            if value in [50, "50", 1000000, 1e6, "1000000", "1e6", "1M"]:
                value = "FIFty" if value in [50, "50"] else "MEG"
            self.get_interface().write((f":CH{channel_number}:TERmination {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_impedance(channel_number, value))
        new_channel.add_preset("50",    "50Ω")
        new_channel.add_preset("1M",    "1MΩ")
        self._add_channel(new_channel)
        return new_channel

    def add_channel_units(self, channel_name, channel_number):
        def _set_units(channel_number, value):
            if value.upper() in ["V", "A", "VOLTS", "AMPS"]:
                value = "V" if value.upper() in ["V", "VOLTS"] else "A"
            else:
                raise ValueError("\n\nUnits must be one of V, A, VOLTS, AMPS")
            self.get_interface().write((f":CH{channel_number}:YUNits {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_units(channel_number, value))
        new_channel.add_preset("VOLTS", "Volts")
        new_channel.add_preset("AMPS",  "Amperes")
        self._add_channel(new_channel)
        return new_channel
        
    def add_channel_coupling(self, channel_name, channel_number):
        def _set_coupling(channel_number, value):
            if value.upper() not in ["AC", "DC", "DCREJect"]:
                raise ValueError("\n\nUnits must be either AC, DC or DCREJect")
            self.get_interface().write((f":CH{channel_number}:COUPling {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_coupling(channel_number, value))
        new_channel.add_preset("AC", "AC")
        new_channel.add_preset("DC", "DC")
        self._add_channel(new_channel)
        return new_channel

    def add_channel_Xrange(self, channel_name):
        ''' Xrange = SCALE x 10 '''
        def _set_Xrange(value):
            value = value/10
            self.get_interface().write((f"HORizontal:SCALE {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_Xrange(value))
        self._add_channel(new_channel)
        return new_channel
    
    def add_channel_Xscale(self, channel_name):
        new_channel = channel(channel_name, write_function=lambda value : self.get_interface().write((f"HORizontal:SCALE {value}").encode(self.str_encoding)))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_Xposition(self, channel_name):
        def _set_Xposition(value):
            self.get_interface().write((f"HORizontal:DELay:TIMe {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_Xposition(value))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_Xreference(self, channel_name): # TODO - for check on actual scope
        def _set_xreference(value):
            self.get_interface().write((f"HORizontal:DELay:MODe OFF").encode(self.str_encoding))
            if value.upper() in ["LEFT", "CENTER", "RIGHT"]: #Agilent valid arguments
                if value == "LEFT":
                    value = 10
                if value == "CENTER":
                    value = 50
                if value == "RIGHT":
                    value = 90                
            self.get_interface().write((f"HORizontal:POSition {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_xreference(value))
        new_channel.add_preset(50,    "Screen Center")
        new_channel.set_min_write_limit(0)
        new_channel.set_max_write_limit(100)
        self._add_channel(new_channel)
        return new_channel
        
    def add_channel_runmode(self, channel_name): # TODO - for check on actual scope
        def _set_runmode(value):
            if value.upper() not in ["RUN", "STOP", "OFF", "ON" "SINGLE"]:
                raise ValueError("\n\nRun mode must be one of: RUN, ON, OFF, STOP, SINGLE")
            if value in ["RUN", "ON"]:
                self.get_interface().write((f"ACQuire:STOPAfter RUNStop; :STATE {value}").encode(self.str_encoding))
            if value in ["STOP", "OFF"]:
                self.get_interface().write((f"ACQuire:STATE {value}").encode(self.str_encoding))
            if value == "SINGLE":
                self.get_interface().write((f"ACQuire:STOPAfter SEQuence; :STATE {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_runmode(value))
        new_channel.add_preset("RUN",       "Free running mode")
        new_channel.add_preset("STOP",      "Stopped")
        new_channel.add_preset("SINGLE",    "Waiting for trigger")
        self._add_channel(new_channel)
        return new_channel
            
    def add_channel_triggerlevel(self, channel_name): # TODO Needs operation complete
        def _set_triggerlevel(value):
            trigger_source = self.get_interface().ask((f"TRIGger:A:EDGE:Source?").encode(self.str_encoding))
            self.get_interface().write((f"TRIGger:A:LEVel:{trigger_source} {value}").encode(self.str_encoding))
        new_channel = channel(channel_name, write_function=lambda value : _set_triggerlevel(value))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_triggermode(self, channel_name):
        def _set_triggermode(value):
            if value.upper() not in ["AUTO", "NORMAL"]:
                raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL")
            self.get_interface().write((f"TRIGger:A:MODe {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_triggermode(value))
        new_channel.add_preset("AUTO",       "Find a trigger level")
        new_channel.add_preset("NORMAL",     "Use defined trigger level")
        self._add_channel(new_channel)
        return new_channel
            
    def add_channel_triggerslope(self, channel_name):
        def _set_triggerslope(value):
            if value.upper() not in ["NEGATIVE", "POSITIVE", "EITHER"]:
                raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL, EITHER")
            self.get_interface().write((f"TRIGger:A:EDGE:SLOpe {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_triggerslope(value))
        new_channel.add_preset("POSITIVE",      "Positive edges")
        new_channel.add_preset("NEGATIVE",      "Negative edges")
        new_channel.add_preset("EITHER",        "Either edge")
        self._add_channel(new_channel)
        return new_channel
            
    def add_channel_triggersource(self, channel_name):
        def _set_triggersource(value):
            if value.upper() in ["CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4", "EXT"]: # Agilent trigger sources arguments (except WGEN)
                if value.upper() == "CHANNEL1": 
                    value = "CH1"
                if value.upper() == "CHANNEL2":
                    value = "CH2"
                if value.upper() == "CHANNEL3":
                    value = "CH3"
                if value.upper() == "CHANNEL4":
                    value = "CH4"
                else:
                    value = "AUX"
            if value.upper() not in ["AUX", "CH1", "CH2", "CH3", "CH4", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14", "D15", "LINE", "RF"]:
                raise ValueError("\n\nTrigger mode must be one of: EXT, LINE, WGEN, CHANx where x=[1..4]]")
            self.get_interface().write((f"TRIGger:A:EDGE:SOUrce {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_triggersource(value))
        new_channel.add_preset("AUX",       "External Trigger")
        new_channel.add_preset("LINE",      "Line Trigger")
        new_channel.add_preset("CH1",  "Channel 1")
        new_channel.add_preset("CH2",  "Channel 2")
        new_channel.add_preset("CH3",  "Channel 3")
        new_channel.add_preset("CH4",  "Channel 4")
        self._add_channel(new_channel)
        return new_channel

    def add_channel_acquire_type(self, channel_name):
        def _set_acquiretype(value):
            if value.upper() in ["NORMAL", "HRESOLUTION"]:
                value = "SAMPLE" if value in ["NORMAL"] else "HIRES"                
            if value.upper() not in ["SAMPLE", "PEAKDETECT", "HIRES", "AVERAGE", "ENVELOPE"]:
                raise ValueError("\n\nAcquire type must be one of: SAMPLE, PEAKDETECT, HIRES, AVERAGE, ENVELOPE")
            self.get_interface().write((f"ACQuire:MODe {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_acquiretype(value))
        new_channel.add_preset("SAMPLE",        "Sets the oscilloscope in the normal mode.")
        new_channel.add_preset("AVERAGE",       "Sets the oscilloscope in the averaging mode, in which the resulting waveform shows an average of SAMple data points from several separate waveform acquisitions. The number of waveform acquisitions that go into making up the average waveform is set using the ACQuire:NUMAVg command.")
        new_channel.add_preset("HIRES",         "Sets the oscilloscope in the high-resolution mode, where the displayed data point value is the average of all the samples taken during the acquisition interval.")
        new_channel.add_preset("PEAKDETECT",    "Sets the oscilloscope in the peak detect mode, where the high-low range is displayed as a vertical column that extends from the highest to the lowest value sampled during the acquisition interval.. PEAKdetect mode can reveal the presence of aliasing or narrow spikes.")
        new_channel.add_preset("ENVELOPE",      "Sets the oscilloscope in the envelope mode, where the resulting waveform shows the PEAKdetect range of data points from every waveform acquisition.")
        self._add_channel(new_channel)
        return new_channel
        
    def add_channel_acquire_count(self, channel_name):  # number of acquisitions for averaging
        def _set_acquirecount(value):
            if value not in [2, 4, 8, 16, 32, 64, 128, 256, 512]:
                raise ValueError("\n\nAcquire Count must be from 2 to 512 in powers of two")
            self.get_interface().write((f"ACQuire:NUMAVg {value}").encode(self.str_encoding))
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value : _set_acquirecount(value))
        self._add_channel(new_channel)
        return new_channel
            
    def add_channel_pointcount(self, channel_name):
        new_channel = channel(channel_name, write_function=lambda value : self.set_points(value))
        self._add_channel(new_channel)
        return new_channel
        
    def _read_immediate_measurement(self, channel_number, measurement):
        '''Return float value of selected measurement corresponding to the named channel'''
        self.get_interface().write((f"MEASurement:IMMed:SOUrce1 CH{channel_number}; Type {measurement}").encode(self.str_encoding))
        #self.get_interface().write((f"MEASurement:IMMed:Type {measurement}").encode(self.str_encoding))
        return float(self.get_interface().ask("MEASurement:IMMed:Value?"))
        
    def clear_display(self):
        self.get_interface().write(("MESSage:STATE 0").encode(self.str_encoding))
        self.get_interface().write(("DISplay:PERSistence CLEAR").encode(self.str_encoding))

    def fetch_display_screenshot(self, format='png'):
        format = self._display_screenshot_image_format_mapping[format]
        self.get_interface().write(("HARDCopy:INKSaver").encode(self.str_encoding))
        self.get_interface().write(("SAVe:IMAGE:FILEFORMAT PNG").encode(self.str_encoding))
        self.get_interface().write(("HARDCopy START").encode(self.str_encoding))
        return self.read()

    def set_channel_label_text(self, channel_number, label_text):
        ''' Sets channel label '''
        self.get_interface().write((f"CH{channel_number}:LABel '{label_text}'").encode(self.str_encoding))
