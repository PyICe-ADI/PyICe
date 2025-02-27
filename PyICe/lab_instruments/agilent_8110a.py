from PyICe.lab_core import *

class Agilent_8110a(scpi_instrument):
    '''
    HP 150MHz Dual Channel Pattern Generator from the early 1990's
    The manual advises to use the short form of SCPI commands to save communication time since this thing has a lousy GPIB port.
    It also advises to turn the display off but there doesn't seem to be a speed issue turning off seems ill advised for debug reasons.
    '''

    def __init__(self, interface_visa, debug_comms=False):
        self._debug_comms = debug_comms
        self._base_name = 'agilent_8110a'
        instrument.__init__(self, f"agilent_8110a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write("*RST")
        '''
        Minimum width of a pulse duration (1 or 0) in the digital pattern.
        Set by add_channel_pulse_period()
        '''
        self.timestep = 6.65e-9

    def add_channel_trigger_source(self, channel_name):
        '''
        Sets the trigger source of the instrument.
        '''
        sources = { "IMMEDIATE":    {"COMMAND": "IMM",  "COMMENT": "Also known as CONTINUOUS through the front panel, makes it free-run."},
                    "INTERNAL":     {"COMMAND": "INT",  "COMMENT": "Unknown - Untested - gives SCPI errors. Please update if you know."},
                    "INTERNAL1":    {"COMMAND": "INT1", "COMMENT": "Unknown - Untested - gives SCPI errors. Please update if you know."},
                    "INTERNAL2":    {"COMMAND": "INT2", "COMMENT": "Unknown - Untested - gives SCPI errors. Please update if you know."},
                    "EXTERNAL":     {"COMMAND": "EXT",  "COMMENT": "Triggers off the EXT input on the front panel."},
                    "EXTERNAL1":    {"COMMAND": "EXT1", "COMMENT": "Triggers off the EXT input on the front panel."},
                    "MANUAL":       {"COMMAND": "MAN",  "COMMENT": "Triggers off the front panel button."},
                    "SOFTWARE":     {"COMMAND": "MAN",  "COMMENT": "Triggers off *TRG. Same as the MANUAL setting but looks cooler."}
                  }
        def set_trigger_source(source):
            if source not in sources:
                print(f"\n\nAgilent 8110A: Sorry don't know how to set trigger source to: '{source}'. Try one of:")
                for source in sources:
                    print(f"    -{source}")
                raise Exception("Bad trigger source.\n\n")
            self.get_interface().write(f":ARM:SOUR {sources[source]['COMMAND']}")
        new_channel = channel(channel_name, write_function=set_trigger_source)
        for source in sources:
            new_channel.add_preset(source, sources[source]['COMMENT'])
        return self._add_channel(new_channel)

    def add_channel_trigger_sense(self, channel_name):
        '''
        Sets the trigger sense of the instrument to EDGE or LEVEL.
        '''
        def set_trigger_sense(sense):
            if sense not in ["EDGE", "LEVEL"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set trigger sense to: '{sense}', try 'EDGE' or 'LEVEL'.\n\n")
            self.get_interface().write(f":ARM:SENS {sense}")
        new_channel = channel(channel_name, write_function=set_trigger_sense)
        new_channel.add_preset("EDGE", "Trigger sense to EDGEs")
        new_channel.add_preset("LEVEL", "Trigger sense to LEVEL")
        return self._add_channel(new_channel)

    def add_channel_trigger_impedance(self, channel_name):
        '''
        Sets the impedance of the EXT INPUT connector.
        '''
        def set_trigger_impedance(impedance):
            if impedance not in [50, "10K"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set EXT input impedance to: '{impedance}', try '50' or '10K'.\n\n")
            self.get_interface().write(f":ARM:IMP {'50OHM' if impedance==50 else '10KOHM'}")
        new_channel = channel(channel_name, write_function=set_trigger_impedance)
        new_channel.add_preset(50, "50Ω input impedance")
        new_channel.add_preset("10K", "10kΩ input impedance")
        return self._add_channel(new_channel)

    def add_channel_arm_level(self, channel_name):
        '''
        Sets the trigger level of the front panel EXT INPUT trigger input.
        '''
        def set_arm_level(voltage):
            self.get_interface().write(f":ARM:LEV {voltage:0.4f}V")
        new_channel = channel(channel_name, write_function=set_arm_level)
        new_channel.set_min_write_limit(-10)
        new_channel.set_max_write_limit(10)
        return self._add_channel(new_channel)

    def add_channel_trigger_slope(self, channel_name):
        '''
        Sets the trigger slope of the EXT INPUT connector.
        '''
        slopes = {  "POSITIVE":    {"COMMAND": "POS",  "COMMENT": "Positive Edge"},
                    "NEGATIVE":    {"COMMAND": "NEG",  "COMMENT": "Negative Edge"},
                    "EITHER":      {"COMMAND": "EITH", "COMMENT": "Either Edge"},
                 }
        def set_trigger_slope(slope):
            if slope not in slopes:
                print(f"\n\nAgilent 8110A: Sorry don't know how to set EXT trigger slope slope to: '{slope}'. Try one of:")
                for slope in slopes:
                    print(f"    -{slope}")
                raise Exception("Bad Slope Settin.\n\n")
            self.get_interface().write(f":ARM:SLOP {slopes[slope]['COMMAND']}")
        new_channel = channel(channel_name, write_function=set_trigger_slope)
        for slope in slopes:
            new_channel.add_preset(slope, slopes[slope]['COMMENT'])
        return self._add_channel(new_channel)

    def add_channel_ouput_mode(self, channel_name):
        '''
        Sets the output of the two channels to be current mode or voltage mode (yes this instrumnt supports current mode - woot!).
        There is no independent mode control per channel, it's both or none.
        '''
        def set_ouput_mode(mode):
            if mode not in ["VOLTAGE", "CURRENT"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set ouput mode to: '{mode}', try 'VOLTAGE' or 'CURRENT'.\n\n")
            self.get_interface().write(f":SOUR:HOLD {'VOLT' if mode=='VOLTAGE' else 'CURR'}")
        new_channel = channel(channel_name, write_function=set_ouput_mode)
        new_channel.add_preset("VOLTAGE", "Voltage Mode Output")
        new_channel.add_preset("CURRENT", "Current Mode Output")
        return self._add_channel(new_channel)

    def add_channel_ouput_state(self, channel_name, number):
        '''
        Sets the output state of each channel to on or off.
        '''
        def set_ouput_state(state):
            if state not in ["ON", "OFF", True, False]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set ouput state to: '{state}', try 'ON', 'OFF', True or False.\n\n")
            state = "ON" if state==True else state
            state = "OFF" if state==False else state
            self.get_interface().write(f":OUTP{number} {'ON' if state=='ON' else 'OFF'}")
        new_channel = channel(channel_name, write_function=set_ouput_state)
        new_channel.add_preset("ON", "Enable Output")
        new_channel.add_preset("OFF", "Disable Output")
        # new_channel.set_write_delay(0.1) #FUD
        return self._add_channel(new_channel)

    def add_channel_ouput_polarity(self, channel_name, number):
        '''
        Sets the output polarity of each channel to NORMAL or INVERTED.
        '''
        def set_ouput_polarity(polarity):
            if polarity not in ["NORMAL", "INVERTED"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set ouput polarity to: '{polarity}', try 'NORMAL' or 'INVERTED'.\n\n")
            self.get_interface().write(f":OUTP{number}:POL {'NORM' if polarity=='NORMAL' else 'INV'}")
        new_channel = channel(channel_name, write_function=set_ouput_polarity)
        new_channel.add_preset("NORMAL", "Normal Output Polarity")
        new_channel.add_preset("INVERTED", "Inverted Output Polarity")
        return self._add_channel(new_channel)

    def add_channel_ouput_impedance(self, channel_name, number):
        '''
        Sets the source impedance of the signal coming out of this instrument.
        Only 50Ω and 1kΩ are available.
        The instrument will round the requested value to the nearer of these but this driver only supports those two to prevent confusion.
        See also: add_channel_external_impedance() for the expected downstream impedance.
        '''
        def set_ouput_impedance(impedance):
            if impedance not in [50, "1K"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set ouput impedance to: '{impedance}', try '50' or '1K'.\n\n")
            self.get_interface().write(f":OUTP{number}:IMP:INT {'50OHM' if impedance==50 else '1KOHM'}")
        new_channel = channel(channel_name, write_function=set_ouput_impedance)
        new_channel.add_preset(50, "50Ω Source impedance")
        new_channel.add_preset("1K", "1kΩ Source impedance")
        return self._add_channel(new_channel)

    def add_channel_external_impedance(self, channel_name, number):
        '''
        Sets the expected external impedance of the downstream client.
        This presumably lets you tell the instrument what voltage to make downstream without having to work out the voltage divider ratio yourself.
        Values from 2.5Ω to 999kΩ are "Specified" (meaning "supported" or what?) but the instrument seems to take and hold values outside this range without error.
        This driver will only support the so-called "Specified" range.
        See also: add_channel_ouput_impedance() for the actual instrument output impedance.
        '''
        def set_external_impedance(impedance):
            self.get_interface().write(f":OUTP{number}:IMP:EXT {impedance:0.4f}OHM")
        new_channel = channel(channel_name, write_function=set_external_impedance)
        new_channel.set_min_write_limit(2.5)
        new_channel.set_max_write_limit(999e3)
        return self._add_channel(new_channel)

    def add_channel_high_voltage_level(self, channel_name, number):
        '''
        Sets the high level of the voltage waveform while being aware of ratio of the downstream impedance and its own source imepdance.
        '''
        def set_high_voltage_level(voltage):
            self.get_interface().write(f":SOUR:VOLT{number}:LEV:IMM:HIGH {voltage}V")
        new_channel = channel(channel_name, write_function=set_high_voltage_level)
        new_channel.set_min_write_limit(-9.9)
        new_channel.set_max_write_limit(10)
        return self._add_channel(new_channel)
        
    def add_channel_low_voltage_level(self, channel_name, number):
        '''
        Sets the Low level of the voltage waveform while being aware of ratio of the downstream impedance and its own source imepdance.
        '''
        def set_low_voltage_level(voltage):
            self.get_interface().write(f":SOUR:VOLT{number}:LEV:IMM:LOW {voltage:0.4f}V")
        new_channel = channel(channel_name, write_function=set_low_voltage_level)
        new_channel.set_min_write_limit(-9.9)
        new_channel.set_max_write_limit(10)
        return self._add_channel(new_channel)

    def add_channel_high_current_level(self, channel_name, number):
        '''
        Sets the high level of the current waveform while being aware of ratio of the downstream impedance and its own source imepdance.
        '''
        def set_high_current_level(current):
            self.get_interface().write(f":SOUR:CURR{number}:LEV:IMM:HIGH {current:0.5f}A")
        new_channel = channel(channel_name, write_function=set_high_current_level)
        new_channel.set_min_write_limit(-0.4)
        new_channel.set_max_write_limit(0.396)
        return self._add_channel(new_channel)
        
    def add_channel_low_current_level(self, channel_name, number):
        '''
        Sets the Low level of the current waveform while being aware of ratio of the downstream impedance and its own source imepdance.
        '''
        def set_low_current_level(current):
            self.get_interface().write(f":SOUR:CURR{number}:LEV:IMM:LOW {current:0.5f}A")
        new_channel = channel(channel_name, write_function=set_low_current_level)
        new_channel.set_min_write_limit(-0.4)
        new_channel.set_max_write_limit(0.396)
        return self._add_channel(new_channel)

    def add_channel_trasition_leading(self, channel_name, number):
        '''
        Sets the leading edge speed of the waveform.
        '''
        def set_transition_leading(time):
            self.get_interface().write(f":SOUR:PULS:TRAN{number}:LEAD {time}S")
        new_channel = channel(channel_name, write_function=set_transition_leading)
        new_channel.set_min_write_limit(1.8e-9)
        new_channel.set_max_write_limit(0.2)
        return self._add_channel(new_channel)
        
    def add_channel_trasition_trailing(self, channel_name, number):
        '''
        Sets the trailing edge speed of the waveform.
        '''
        def set_transition_trailing(time):
            self.get_interface().write(f":SOUR:PULS:TRAN{number}:TRA {time}S")
        new_channel = channel(channel_name, write_function=set_transition_trailing)
        new_channel.set_min_write_limit(1.8e-9)
        new_channel.set_max_write_limit(0.2)
        return self._add_channel(new_channel)

    def add_channel_pulse_width(self, channel_name, number):
        '''
        Sets the pulse width of a given channel?
        Unclear if this applies in Pattern mode.
        '''
        def set_pulse_width(pulse_width):
            self.get_interface().write(f":SOUR:PULS:WIDT{number} {pulse_width}S")
        new_channel = channel(channel_name, write_function=set_pulse_width)
        new_channel.set_min_write_limit(3.3e-9)
        new_channel.set_max_write_limit(0.999)
        return self._add_channel(new_channel)
        
    def add_channel_pulse_period(self, channel_name):
        '''
        Sets the pulse period.
        In Pattern mode, this seems to set both the mark and space times of each pulse.
        '''
        def set_pulse_period(pulse_period):
            self.get_interface().write(f":SOUR:PULS:PER {pulse_period}S")
        new_channel = channel(channel_name, write_function=set_pulse_period)
        new_channel.set_min_write_limit(6.65e-9)
        new_channel.set_max_write_limit(0.999)
        return self._add_channel(new_channel)
        
        
    def add_channel_delay(self, channel_name, number):
        '''
        Sets the delay of a given channel.
        Adding a delay of 800ps anecdotally makes the two channels line perfectly. This may only be true when the edges are set to 2ns so caveat-emptor.
        **** WARNING ****
        Setting the delay of a channel that is in manual trigger pattern mode causes the pattern become to malformed and actually hangs the machine from accepting further trigger requests.
        Returning the trigger mode to CONTINUOUS (aka IMMEDIATE) can clear this hung state but it should be avoided.
        Setting the state to CONTINUOUS (IMMEDIATE) while changing the delay or setting the delay before going to triggered mode for the first time seems safe.
        *** WARNING ***
        '''
        def set_delay(delay):
            self.get_interface().write(f":SOUR:PULS:DEL{number} {delay}s")
        new_channel = channel(channel_name, write_function=set_delay)
        new_channel.set_min_write_limit(0)
        new_channel.set_max_write_limit(0.999)
        return self._add_channel(new_channel)

    def add_channel_trigger(self, channel_name):
        '''
        Triggers the instrument assuming it's in manual mode.
        '''
        def trigger(value):
            self.trigger()
        new_channel = channel(channel_name, write_function=trigger)
        new_channel.add_preset("GO", "Trigger a pattern. Writing any value will work here.")
        return self._add_channel(new_channel)
        
    def add_channel_pattern(self, channel_name, number):
        '''
        Sends a pattern of up to 4096 bits (1's and 0s) to the pattern memory of a given channel.
        Available channels are 1, 2 and 3 which is the strobe output on the front panel.
        Data types supported are:
            - CSV lists (no encompassing brackets of any kind). This is useful for use with the PyICe GUI.
            - Python list of integers of either 0 to 1.
        '''
        def set_pattern(pattern):
            if type(pattern) is str:
                pattern = pattern.split(",") # Always a list of strings hereafter
            pattern = ''.join(str(value) for value in pattern)
            length_of_data = len(pattern)
            if length_of_data > 4096:
                raise Exception(f"\n\nAgilent 8110A: Too many values ({length_of_data}) sent to the pattern. Maximum number possible is 4096.\n\n")
            if not all(value=='0' or value=='1' for value in pattern):
                raise Exception(f"\n\nAgilent 8110A: Values other than 1 or 0 sent to the pattern. Stick to 1 and 0 for single channel pattern writes.\n\n")
            self.get_interface().write(f":DIG:STIM:PATT:DATA{number} #{len(str(length_of_data))}{length_of_data}{pattern}")
        new_channel = channel(channel_name, write_function=set_pattern)
        return self._add_channel(new_channel)
        
    def add_channels_pattern(self, channel_name):
        '''
        Sends a patterns of up to 4096 bits (1's and 0s) to all three channels (1, 2 and Strobe out on the front panel) at the same time.
        The lower three bits of each byte control the channels, the upper 5 bits are ignored.
        The bits are as follows:
        Code   Dec  STROBE   OUT2    OUT1
        --------------------------------
        0 0 0   [0]   0       0       0
        0 0 1   [1]   0       0       1
        0 1 0   [2]   0       1       0
        0 1 1   [3]   0       1       1
        1 0 0   [4]   1       0       0
        1 0 1   [5]   1       0       1
        1 1 0   [6]   1       1       0
        1 1 1   [7]   1       1       1
        Data types supported are:
            - CSV lists (no encompassing brackets of any kind). This is useful for use with the PyICe GUI.
            - Python list of integers of either 0 to 1.
        '''
        def set_patterns(pattern):
            if type(pattern) is str:
                pattern = pattern.split(",") # Always a list of strings hereafter
            pattern = ''.join(str(value) for value in pattern)
            length_of_data = len(pattern)
            if length_of_data > 4096:
                raise Exception(f"\n\nAgilent 8110A: Too many values ({length_of_data}) sent to the pattern. Maximum number possible is 4096.\n\n")
            if not all(value in [str(val) for val in range(8)] for value in pattern):
                raise Exception(f"\n\nAgilent 8110A: Values other than 0 to 7 sent to the pattern. Stick to values from 0 to 7 for this 3-bit write.\n\n")
            self.get_interface().write(f":DIG:STIM:PATT:DATA #{len(str(length_of_data))}{length_of_data}{pattern}")
        new_channel = channel(channel_name, write_function=set_patterns)
        return self._add_channel(new_channel)
        
    def add_channel_pattern_state(self, channel_name):
        '''
        Enables the outputs to follow the pattern generator vs just free running pulses.
        '''
        def set_pattern_state(state):
            if state not in ["ON", "OFF", True, False]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set pattern state to: '{state}', try 'ON', 'OFF', True or False.\n\n")
            state = "ON" if state==True else state
            state = "OFF" if state==False else state
            self.get_interface().write(f"DIG:STIM:PATT:STATE {state}")
        new_channel = channel(channel_name, write_function=set_pattern_state)
        new_channel.add_preset("ON", "Enable Pattern")
        new_channel.add_preset("OFF", "Disable Pattern")
        return self._add_channel(new_channel)
        
    def add_channel_pattern_format(self, channel_name, number):
        '''
        Sets the per-channel output patterns to be RZ or NRZ (Return to Zero or Non Return to Zero).
        '''
        def set_pattern_format(pulse_format):
            if pulse_format not in ["RZ", "NRZ"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set pattern format to: '{pulse_format}', try 'RZ' or 'NRZ'.\n\n")
            self.get_interface().write(f":DIG:STIM:SIGN{number}:FORM {pulse_format}")
        new_channel = channel(channel_name, write_function=set_pattern_format)
        new_channel.add_preset("RZ", "Return to Zero")
        new_channel.add_preset("NRZ", "Non Return to Zero")
        return self._add_channel(new_channel)

class TWI():

    def __init__(self, time_step):
        self.time_step = time_step
        self.tbuf = 1300e-9
        self.thd_sta = 600e-9
        self.tlow = 1300e-9
        self.thd_dat = 0e-9     # Allowed to be 0ns to 900ns
        self.thigh = 600e-9
        self.tsu_dat = 100e-9
        self.tsu_sta = 600e-9   # Restart
        self.tsu_sto = 600e-9
        self.tsp = 50e-9
        self.tlead = 1.8e-9
        self.ttrail = 1.8e-9
        self.frequency = 1 / ( self.tlead + self.thigh + self.tlow + self.ttrail)
        self.SCL = []
        self.SDA = []

    def biterator(self, byte):
        '''Iterates over the bits of an integer from left to right.'''
        length = byte.bit_length()
        for index in range(length):
            yield 1 if byte << index & 1 << length-1 == 1 << length-1 else 0

    def add_lead_in(self, SDA, SCL):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)
        
    def add_lead_out(self, SDA, SCL):
        self.SCL.extend(SCL)
        self.SDA.extend(SDA)

    def add_start(self):
        self.SCL.extend([1])
        self.SDA.extend([0])
        self.dwell(self.thd_sta)
        self.SCL.extend([0])
        self.SDA.extend([0])
        self.dwell(self.tlow - self.tsu_dat)

    def add_stop(self):
        self.SCL.extend([1])
        self.SDA.extend([1])
        self.dwell(self.tbuf)

    def add_data_to_low(self):
        self.SCL.extend([0])
        self.SDA.extend([0])
        self.dwell(self.tlow)

    def add_clock_high(self):
        self.SCL.extend([1])
        self.SDA.extend([0])
        self.dwell(self.tsu_sto)

    def add_data_bit(self, d):
        self.SCL.extend([0])
        self.SDA.extend([d])
        self.dwell(self.tsu_dat)
        self.SCL.extend([1])
        self.SDA.extend([d])
        self.dwell(self.thigh)
        self.SCL.extend([0])
        self.SDA.extend([d])
        self.dwell(self.thd_dat)

    def add_ack_bit(self):
        self.dwell(self.tlow)
        self.add_data_bit(1)

    def add_byte(self, byte):
        for bit in self.biterator(byte):
            self.dwell(self.tlow)
            twi.add_data_bit(bit)
        twi.add_ack_bit()

    def add_addr7(self, addr7, R_Wb):
        self.add_byte(addr7*2 + R_Wb)

    def dwell(self, tdwell):
        cycles = round(tdwell / self.time_step)
        self.SCL.extend(self.SCL[-1:] * cycles)
        self.SDA.extend(self.SDA[-1:] * cycles)

    def get_SDA(self):
        return self.SDA
        
    def get_SCL(self):
        return self.SCL

if __name__ == "__main__":   

    from PyICe import lab_interfaces
    interface_factory = lab_interfaces.interface_factory()
    interface_factory.set_gpib_adapter_visa(adapter_number=0)
    my_interface = interface_factory.get_visa_gpib_interface(gpib_adapter_number=0, gpib_address_number=1, timeout=10)
    pulsegen = Agilent_8110a(my_interface)
    pulsegen.add_channel_ouput_mode("pulsegen_output_mode")
    pulsegen.add_channel_ouput_state("pulsegen_output_state1", number=1)
    pulsegen.add_channel_ouput_state("pulsegen_output_state2", number=2)
    pulsegen.add_channel_ouput_impedance("pulsegen_output_impedance1", number=1)
    pulsegen.add_channel_ouput_impedance("pulsegen_output_impedance2", number=2)
    pulsegen.add_channel_external_impedance("pulsegen_external_impedance1", number=1)
    pulsegen.add_channel_external_impedance("pulsegen_external_impedance2", number=2)
    pulsegen.add_channel_high_voltage_level("pulsegen_high_voltage1", number=1)
    pulsegen.add_channel_high_voltage_level("pulsegen_high_voltage2", number=2)
    pulsegen.add_channel_low_voltage_level("pulsegen_low_voltage1", number=1)
    pulsegen.add_channel_low_voltage_level("pulsegen_low_voltage2", number=2)
    pulsegen.add_channel_ouput_polarity("pulsegen_polarity1", number=1)
    pulsegen.add_channel_ouput_polarity("pulsegen_polarity2", number=2)
    pulsegen.add_channel_trigger_source("pulsegen_trigger_source")
    pulsegen.add_channel_trigger_sense("pulsegen_trigger_sense")
    pulsegen.add_channel_arm_level("pulsegen_trigger_level")
    pulsegen.add_channel_trigger_slope("pulsegen_trigger_slope")
    pulsegen.add_channel_trigger("pulsegen_trigger")
    pulsegen.add_channel_pattern("pulsegen_pattern1", number=1)
    pulsegen.add_channel_pattern("pulsegen_pattern2", number=2)
    pulsegen.add_channels_pattern("pulsegen_pattern_all")
    pulsegen.add_channel_pulse_period("pulsegen_pulse_period")
    pulsegen.add_channel_trasition_leading("pulsegen_edge_leading1", number=1)
    pulsegen.add_channel_trasition_leading("pulsegen_edge_leading2", number=2)
    pulsegen.add_channel_trasition_trailing("pulsegen_edge_trailing1", number=1)
    pulsegen.add_channel_trasition_trailing("pulsegen_edge_trailing2", number=2)
    pulsegen.add_channel_pattern_state("pulsegen_pattern_state")
    pulsegen.add_channel_pattern_format("pulsegen_pattern_format1", number=1)
    pulsegen.add_channel_pattern_format("pulsegen_pattern_format2", number=2)
    pulsegen.add_channel_delay("add_channel_delay1", number=1)
    pulsegen.add_channel_delay("add_channel_delay2", number=2)
    m = master()
    m.add(pulsegen)
    
    m.write("pulsegen_output_mode", "VOLTAGE")
    m.write("pulsegen_output_impedance1", 50)
    m.write("pulsegen_output_impedance2", 50)
    m.write("pulsegen_external_impedance1", 50)
    m.write("pulsegen_external_impedance2", 50)
    m.write("pulsegen_high_voltage1", 2)
    m.write("pulsegen_high_voltage2", 2)
    m.write("pulsegen_low_voltage1", 0)
    m.write("pulsegen_low_voltage2", 0)
    m.write("pulsegen_polarity1", "NORMAL")
    m.write("pulsegen_polarity2", "NORMAL")
    m.write("pulsegen_trigger_sense", "EDGE")
    m.write("pulsegen_pulse_period", 6.65e-9)
    m.write("pulsegen_edge_leading1", 1.8e-9)
    m.write("pulsegen_edge_leading2", 1.8e-9)
    m.write("pulsegen_edge_trailing1", 1.8e-9)
    m.write("pulsegen_edge_trailing2", 1.8e-9)
    m.write("pulsegen_pattern_state", True)
    m.write("pulsegen_pattern_format1", "NRZ")
    m.write("pulsegen_pattern_format2", "NRZ")
    m.write("pulsegen_trigger_source", "IMMEDIATE")
    # m.write("add_channel_delay1", 800e-12)
    m.write("pulsegen_trigger_source", "SOFTWARE")
    m.write("pulsegen_output_state1", "ON")
    m.write("pulsegen_output_state2", "ON")

    twi = TWI(time_step=pulsegen.timestep)
    twi.add_lead_in(SCL=[1,1], SDA=[0,0])
    twi.add_stop()
    twi.add_start()
    twi.add_addr7(0x69, R_Wb=0)
    twi.add_data_to_low()
    twi.add_clock_high()
    twi.add_stop()
    twi.add_lead_out(SCL=[0,0,1], SDA=[0,0,0])
    
    from PyICe.lab_utils.eng_string import eng_string
    print("FREQ", eng_string(twi.frequency, fmt=':.2f', si=True, units="Hz"))
    print("Pattern Length", len(twi.get_SCL()))
    m.write("pulsegen_pattern1", twi.get_SCL())
    m.write("pulsegen_pattern2", twi.get_SDA())
    m.write("pulsegen_trigger", "GO")
    m.gui()
    
    
# Done:
    # :ARM:IMPedance
    # :ARM:LEVe1
    # :ARM:SENSe
    # :ARM:SLOPe
    # :ARM:SOURce
    # *TRG
    # :TRIGger:IMPedance
    # :TRIGger:LEVe1
    # :TRIGger:SLOPe
    # :TRIGger:SOURce
    # [:SOURce]:HOLD VOLTage|CURRent
    # [:SOUR]:VOLT[1|2][:LEV][:IMMediate]:HIGH
    # [:SOUR]:VOLT[1|2][:LEV][:IMMediate]:LOW
    # [:SOUR]:CURR[1|21[:LEV][:IMM]:HIGH
    # [:SOUR]:CURR[1|2][:LEV][:IMMediate]:LOW
    # :OUTPut[1|2][:STATe] ON|OFF|0|1
    # :OUTPut[1|2]:IMPedance[:INTernal]
    # :OUTPut[1|2]:IMPedance:EXTernal
    # :OUTPut[1|2]:POLarity
    # [:SOURce]:PULSe:PERiod
    # [:SOURce]:PULSe:WIDTh[1|2]
    # [:SOURce]:PULSe:TRANsition[1|2][:LEADing]
    # f:SOURcel:PULSe:TRANsition[1|2]:TRAiling
    # :DIGitall:STIMulus]:PATTern[:STATE]
    # :DIGital[:STIMulus]:SIGNal[1|2]:FORMat
    # :DIGital[:STIMulus]:PATTern:DATA[1|2|3]

# WIP:

# To Do:

    # :ARM:EWIDth:STATe
    # :ARM:FREQuency
    # :ARM:PERiod
    # :CHANnel:MATH
    # :DIGital[:STIMulus]:PATTern:PRBS[1|2|3]
    # :DIGital[:STIMulus]:PATTern:PRESet[1|2|3]
    # :DIGital[:STIMulus]:PATTern:UPDate
    # :DISPlay[:WINDow][:STATe]
    # :MMEMory:CATalog?
    # :MMEMory:CDIRectory
    # :MMEMory:COPY
    # :MMEMory:DELete
    # :MMEMory:INITialize
    # :MMEMory:LOAD:STATe
    # :MMEMory:STORe:STATe
    # [:SOURce]:CORRection[1|2]:EDELay[:TIME]
    # [:SOUR]:CURRent[1|2][:LEV][:IMM][:AMPL]
    # [:SOUR]:CURR[1|2][:LEVel][:IMM]:OFFS
    # [:SOURce]:CURRent[1|2]:LIMit[:HIGH]
    # [:SOURce]:CURRent[1|2]:LIMit:LOW
    # [:SOURce]:CURRent[1|2]: LIMit:STATe
    # [:SOURce]:FREQuency[:CW|:FIXed]
    # [:SOURce]:FREQuency[:CW|:FIXed]:AUTO
    # [:SOURce]:PHASe[1|2][:ADJust]
    # [:SOURce]:PULSe:DCYCle[1|2]
    # [:SOURce]:PULSe:DELay[1|2]
    # [:SOURce]:PULSe:DELay[1|2j:HOLD
    # [:SOURce]:PULSe:DELay[1|2]:UNIT
    # [:SOURce]:PULSe:DOUBle[1|2][:STATe]
    # [:SOURce]:PULSe:DOUBle[1|2]:DELay
    # [:SOURce]:PULSe:DOUBle[1|2]:DELay:HOLD
    # [:SOURce]:PULSe:DOUBle[1|21:DELay:UNIT
    # [:SOURce]:PULSe:HOLD [1|2]
    # [:SOURce]:PULSe:PERiod:AUTO
    # [:SOURce]:PULSe:TrailingDELay[1|2]
    # [:SOURce]:PULSe:TRANsition[1|2]:HOLD
    # [:SOURce]:PULSe:TRANsition[1|2]:UNIT
    # [:SOURce]:PULSe:TRAN[1|2]:TRAiling:AUTO
    # [:SOURce]:PULSe:TRIGger[1|2]:VOLTage
    # [:SOURce]:ROSCillator:SOURce
    # [:SOURce]:ROSCillator:ENIernal:FREQuency
    # [SOUR]:VOLT[1|2][:LEV][:IMM][:AMPLitude]
    # [:SOUR]:VOLTage[1|2][:LEV][:IMM]:OFFSet
    # [:SOURce]:VOLTage[1|2]:LIMit[:HIGH]
    # [:SOURce]:VOLTage[1|2]:LIMit:LOW
    # [:SOURce]:VOLTage[1|2]:LIMit:STATe
    # :STATus:OPERation
    # :STATus:PRESet
    # :STATus:QUEStionable
    # :SYSTem:CHECk[:ALL][:STATe]
    # :SYSTem:ERRor?
    # :SYSTem:KEY
    # :SYSTem:PRESet
    # :SYSTem:SECurity[:STATe]
    # :SYSTem:SET
    # :SYSTem:VERSion?
    # :SYSTem:WARNing[:COUNt]?
    # :SYSTem:WARNing:STRing?
    # :SYSTem:WARNing:BUFFer?
    # :TRIGger:COUNt