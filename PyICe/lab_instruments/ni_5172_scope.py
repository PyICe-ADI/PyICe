from PyICe.lab_core import *
import numpy as np
import matplotlib.pyplot as plt
import niscope
from niscope.errors import DriverError

class pxie_5172(instrument):

    def __init__(self, resource_name: str) -> None:
        self._base_name: str = "PXIe-5172_SCOPE"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")
        self.session = niscope.Session(resource_name=resource_name, reset_device=True)

    """ Setup Methods  # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def set_channel(self, channel_num: int, enabled: bool) -> None:
        self.session.channels[channel_num].channel_enabled = enabled

    def get_enabled_channels(self) -> list[int]:
        en_channels = self.session.enabled_channels.split(',')
        return [int(ch) for ch in en_channels]

    def disable_all_Ychannels(self) -> None:
        for channel_num in [0, 1, 2, 3, 4, 5, 6, 7]:
            self.set_channel(channel_num=channel_num, enabled=False)

    def enable_channels(self, channel_nums: set[int]) -> None:
        for channel_num in channel_nums:
            self.set_channel(channel_num=channel_num, enabled=True)

    def resync_scope(self):
        """Reset the scope and reconfigure physical instrument to desired used channels.
           Enabled channels is based on listed attributes. """
        enabled_channels = []
        for ch in self.get_all_channels_list():
            try:
                for physical_channel in ch.get_attribute('dependent_physical_channels'):
                    if physical_channel is None:
                        continue
                    enabled_channels.append(physical_channel)
            except ChannelAttributeException as e:
                raise Exception(
                    f'Oscilloscopes requires "dependent_physical_channels" attribute of all scope channels.')
        enabled_unique = set(enabled_channels)
        self.disable_all_Ychannels()
        self.enable_channels(enabled_unique)

    def setup_channels(self, scope_channels: dict, prefix: str="scope") -> None:
        """ Helper method to set up each specific waveform channel in scope_channels list and call
            add_all_timebase_trigger_acquisition_channels """
        for scope_channel in scope_channels:
            channel_name = scope_channel
            channel_number = scope_channels[scope_channel]
            self.add_Ychannel_waveform(channel_name=channel_name, channel_number=channel_number)
            self.add_Ycontrol_Yreadback_channels(channel_name=channel_name, channel_number=channel_number)
        self.add_all_timebase_trigger_acquisition_channels(prefix=prefix)

    def add_Ycontrol_Yreadback_channels(self, channel_name: str, channel_number: int) -> None:
        """Add all control and readback channels for the specified Y waveform channel."""
        self.add_channel_Yscale(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_Yrange(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_Yoffset(channel_name=channel_name, channel_number=channel_number)

        self.add_channel_coupling(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_bandwidth_limit(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_impedance(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_impedance_readback(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_probe_gain(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_probe_gain_readback(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_units(channel_name=channel_name, channel_number=channel_number)

        self.add_channel_Yscale_readback(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_Yrange_readback(channel_name=channel_name, channel_number=channel_number)
        self.add_channel_Yoffset_readback(channel_name=channel_name, channel_number=channel_number)

    def add_all_timebase_trigger_acquisition_channels(self, prefix) -> None:
        """ Helper method to easily add time base, Xcontrol, Xreadback, trigger, and acquisition channels"""

        """ Configure some default settings for trigger and sample rate to prevent error in the initial setup of channels. """
        self.set_channel(channel_num=0, enabled=True)
        self.set_trigger_source('CHANNEL0')
        self.session.trigger_type = niscope.TriggerType.EDGE
        self.session.min_sample_rate = 1000000  # 1MS/s minimum sample rate

        """ Add all X control channels."""
        self.add_channel_Xscale(prefix)
        self.add_channel_Xrange(prefix)
        self.add_channel_Xposition(prefix)
        self.add_channel_Xscale_readback(prefix)
        self.add_channel_Xrange_readback(prefix)
        self.add_channel_Xposition_readback(prefix)
        """ Add all trigger control channels."""
        self.add_channel_trigger_type(prefix)
        self.add_channel_trigger_source(prefix)
        self.add_channel_trigger_source_readback(prefix)
        self.add_channel_trigger_slope(prefix)
        self.add_channel_trigger_coupling(prefix)
        self.add_channel_trigger_level(prefix)
        self.add_channel_trigger_level_readback(prefix)
        self.add_channel_trigger_mode(prefix)
        """ Add all acquisition control channels."""
        self.add_channel_acquisition_type(prefix)
        self.add_channel_run_mode(prefix)
        self.add_channel_points_count(prefix)
        self.add_channel_points_count_readback(prefix)
        self.add_channel_identity(prefix)
        self.add_channel_trigger_delay(prefix)
        self.add_channel_trigger_delay_readback(prefix)
        self.add_channel_sample_rate(prefix)
        self.add_channel_sample_rate_readback(prefix)
        self.add_channel_timebase(prefix)
        self.add_clear_measurements_channel(prefix)

    """ Waveform Data Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def read_scope_channel(self, channel_num: int):
        record_length = self.get_points_count()
        waveform = self.session.channels[channel_num].fetch(num_samples=record_length, timeout=0.0)
        wf = waveform[0]
        y_data = np.frombuffer(wf.samples, dtype=np.float64)  # Convert to NumPy array (voltage samples) for easier processing
        return y_data

    def get_waveform_data(self, channel_num: int):
        try:
            return self.read_scope_channel(channel_num)
        except DriverError as e:
            if e.code == -1074118614:  # Acquisition not initiated
                self.session.initiate()
                time.sleep(0.2)
                try:
                    return self.read_scope_channel(channel_num)
                except DriverError as e2:
                    raise Exception(f"Acquisition has not been initiated. Call channels.write('scope_run_mode', 'RUN') before fetch.")

    def read_scope_time(self):
        en_channels = self.get_enabled_channels()
        record_length = self.get_points_count()
        waveform = self.session.channels[en_channels[0]].fetch(num_samples=record_length, timeout=0.0)
        wf = waveform[0]
        # x_start = wf.absolute_initial_x  # Real-world timestamp
        x_start = wf.relative_initial_x  # Oscilloscope time range.
        x_increment = wf.x_increment
        x_data = x_start + np.arange(record_length) * x_increment  # Convert to NumPy array (time data) for easier processing
        return x_data

    def get_scope_time_data(self):
        try:
            return self.read_scope_time()
        except DriverError as e:
            if e.code == -1074118614:  # Acquisition not initiated
                self.session.initiate()
                time.sleep(0.2)
                try:
                    return self.read_scope_time()
                except DriverError as e2:
                    raise Exception(f"Acquisition has not been initiated. Call channels.write('scope_run_mode', 'RUN') before fetch.")


    def add_Ychannel_waveform(self, channel_name, channel_number):
        """ Add named waveform channel, Ycontrol and Yreadback channels of the waveform."""
        new_channel = channel(channel_name, read_function=lambda: self.get_waveform_data(channel_number))
        self._add_channel(new_channel)
        new_channel._set_type_affinity('PyICeBLOB')
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_timebase(self, channel_name):
        """Add time channel that stores the x-axis data points in seconds"""
        new_channel = channel(channel_name + "_timedata", read_function=lambda: self.get_scope_time_data())
        self._add_channel(new_channel)
        new_channel._set_type_affinity('PyICeBLOB')
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    """ Vertical(Y) Control Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def set_yscale(self, channel_num: int, value: float) -> None:
        self.session.channels[channel_num].vertical_range = value * 8.0  # scale is in volts/div, range is in volts

    def get_yscale(self, channel_num: int) -> float:
        return self.session.channels[channel_num].vertical_range / 8.0  # scale is in volts/div, range is in volts

    def add_channel_Yscale(self, channel_name: str, channel_number: int) -> channel:
        new_channel = channel(channel_name + '_Yscale', write_function=lambda value: self.set_yscale(channel_number, value))
        new_channel._set_value(self.get_yscale(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_Yscale_readback(self, channel_name: str, channel_number: int) -> channel:
        """ Return the vertical scale (volt/division) of a channel."""
        new_channel = channel(channel_name + '_Yscale_readback', read_function=lambda: self.get_yscale(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_yrange(self, channel_num: int, value: float) -> None:
        self.session.channels[channel_num].vertical_range = value

    def get_yrange(self, channel_num: int) -> float:
        return float(self.session.channels[channel_num].vertical_range)

    def add_channel_Yrange(self, channel_name: str, channel_number: int) -> channel:
        new_channel = channel(channel_name + '_Yrange', write_function=lambda value: self.set_yrange(channel_number, value))
        new_channel._set_value(self.get_yrange(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_Yrange_readback(self, channel_name: str, channel_number: int) -> channel:
        new_channel = channel(channel_name + '_Yrange_readback', read_function=lambda: self.get_yrange(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_yoffset(self, channel_num: int, value: float) -> None:
        self.session.channels[channel_num].vertical_offset = -value

    def get_yoffset(self, channel_num: int) -> float:
        return -float(self.session.channels[channel_num].vertical_offset)

    def add_channel_Yoffset(self, channel_name: str, channel_number: int) -> channel:
        new_channel = channel(channel_name + '_Yoffset', write_function=lambda value: self.set_yoffset(channel_number, value))
        new_channel._set_value(self.get_yoffset(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_Yoffset_readback(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_Yoffset_readback', read_function=lambda: self.get_yoffset(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_coupling(self, channel_num: int, value: str) -> None:
        """ Default:  DC """
        vertical_couplings: dict = {
            'AC': 0,
            'DC': 1,
        }
        if value.upper() not in vertical_couplings:
            raise ValueError(f"Valid values for vertical coupling are: {list(vertical_couplings.keys())}.")
        self.session.channels[channel_num].vertical_coupling = niscope.VerticalCoupling(vertical_couplings[value])

    def get_coupling(self, channel_num: int) -> float:
        return self.session.channels[channel_num].vertical_coupling.name

    def add_channel_coupling(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_coupling', write_function=lambda value: self.set_coupling(channel_number, value))
        new_channel.add_preset("AC", "AC")
        new_channel.add_preset("DC", "DC")
        new_channel._set_value(self.get_coupling(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_probe_attenuation(self, channel_num: int, value: float) -> None:
        """ Default:  1.0 """
        self.session.channels[channel_num].probe_attenuation = value

    def get_probe_attenuation(self, channel_num: int) -> float:
        return self.session.channels[channel_num].probe_attenuation

    def add_channel_probe_gain(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_probe_gain', write_function=lambda value: self.set_probe_attenuation(channel_number, value))
        new_channel._set_value(self.get_probe_attenuation(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_probe_gain_readback(self, channel_name, channel_number):
        new_channel = channel(channel_name + '_probe_gain_readback', read_function=lambda: self.get_probe_attenuation(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_bandwidth_limit(self, channel_num: int, enabled: bool) -> None:
        """ Default:  DISABLED """
        if enabled:
            self.session.channels[channel_num].max_input_frequency = 20e6  # 20MHz
        else:
            self.session.channels[channel_num].max_input_frequency = 100e6  # 100MHz (full bandwidth)

    def get_bandwidth_limit(self, channel_num: int) -> str:
        if self.session.channels[channel_num].max_input_frequency == 20e6:
            return 'ENABLED'
        return 'DISABLED'

    def add_channel_bandwidth_limit(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_BWlimit', write_function=lambda value: self.set_bandwidth_limit(channel_number, value))
        new_channel.add_preset("ON", "20MHz bandwidth")
        new_channel.add_preset("OFF", "Full bandwidth")  # 100MHz actual bandwidth
        new_channel._set_value(self.get_bandwidth_limit(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_impedance(self, channel_num: int, value: str) -> None:
        """ Default:  1M """
        input_impedances: dict = {
            50: 50,
            "50": 50,
            1e6: 1000000,
            "1M": 1000000,
            "1MEG": 1000000,
        }
        if isinstance(value, str):
            value = value.upper()
        if value not in input_impedances:
            raise ValueError(f"Valid values for impedance are: {list(input_impedances.keys())}.")
        self.session.channels[channel_num].input_impedance = input_impedances[value]

    def get_impedance(self, channel_num: int) -> float | str:
        if self.session.channels[channel_num].input_impedance == 50.0:
            return 50
        return '1M'

    def add_channel_impedance(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_impedance', write_function=lambda value: self.set_impedance(channel_number, value))
        new_channel.add_preset("50", "50Ω")
        new_channel.add_preset("1M", "1MΩ")
        new_channel._set_value(self.get_impedance(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_impedance_readback(self, channel_name, channel_number):
        new_channel = channel(channel_name + '_impedance_readback', read_function=lambda: self.get_impedance(channel_number))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    """ Horizontal(X) Control Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def set_xscale(self, time_per_div: float) -> None:
        x_divisions: int = 10 * 2 # No of division (t/div). When multiplied by 2 the InstrumentStudio display shows the correct time range.
        ref_position: float = self.get_xposition()  # Get current reference position
        sample_rate: float = self.get_sample_rate()  # Get current sample rate or set to 1MS/s as minimum
        # if sample_rate < 1000000: # 1MS/s minimum sample rate
        #     sample_rate = 1000000
        num_points: int = int(sample_rate * time_per_div * x_divisions) # Calculate initial number of points

        # Tried to override so that num_points do not exceed 300K, but NI-SCOPE REMOTE mode enforces this automatically.
        # max_num_points: int = 300000  # Limited to 300K when in REMOTE operation
        # if num_points > max_num_points:
        #     sample_rate = max_num_points / (time_per_div * x_divisions)
        #     num_points = max_num_points
        # print(f"Sample rate: {sample_rate:.2f} with {num_points} points.")

        # t/dv        Sample Rate     Num Points
        # 1e-3        1000000         20000
        # 10e-3       1000000         200000
        # 100e-3      150000          300000

        self.session.configure_horizontal_timing(
            min_sample_rate=sample_rate,
            min_num_pts=num_points,
            ref_position=ref_position,
            num_records=1,
            enforce_realtime=True
        )

    def get_xscale(self) -> float:
        x_divisions: int = 20  # No of division (t/div). When multiplied by 2 the InstrumentStudio display shows the correct time range.
        time_per_div = self.get_points_count() / (self.get_sample_rate() * x_divisions)
        return float(time_per_div)

    def add_channel_Xscale(self, channel_name: str):
        new_channel = channel(channel_name + '_Xscale', write_function=lambda value: self.set_xscale(value))
        new_channel._set_value(self.get_xscale())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_Xscale_readback(self, channel_name):
        new_channel = channel(channel_name + '_Xscale_readback', read_function=lambda: self.get_xscale())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_xrange(self, value: float) -> None:
        self.set_xscale(time_per_div=value / 10.0)

    def add_channel_Xrange(self, channel_name: str):
        new_channel = channel(channel_name + '_Xrange', write_function=lambda value: self.set_xrange(value))
        new_channel._set_value(self.get_xscale() * 10)
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_Xrange_readback(self, channel_name):
        new_channel = channel(channel_name + '_Xrange_readback', read_function=lambda: self.get_xscale() * 10)
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_xposition(self, value: float) -> None:
        """ Default:  50.0 """
        self.session.horz_record_ref_position = value

    def get_xposition(self) -> float:
        return self.session.horz_record_ref_position

    def add_channel_Xposition(self, channel_name: str):
        new_channel = channel(channel_name + '_Xposition', write_function=lambda value: self.set_xposition(value))
        new_channel._set_value(self.get_xposition())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_Xposition_readback(self, channel_name):
        new_channel = channel(channel_name + '_Xposition_readback', read_function=lambda: self.get_xposition())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    """ Trigger Control Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def set_trigger_type(self, value: str) -> None:
        """ Default:  IMMEDIATE """
        trigger_types: dict = {
            'IMMEDIATE': 6,
            'EDGE': 1,
            'DIGITAL': 1002,
            'HYSTERESIS': 1001,
            'SOFTWARE': 1004,
            'WINDOW': 1003
        }
        if value.upper() not in trigger_types:
            raise ValueError(f"Valid values for trigger type are: {list(trigger_types.keys())}.")
        if self.session.trigger_source not in ['0', '1', '2', '3', '4', '5', '6', '7']:
            raise ValueError(f"Select a trigger source before setting trigger type.")

        self.session.trigger_type = niscope.TriggerType(trigger_types[value])

    def get_trigger_type(self) -> str:
        return self.session.trigger_type.name

    def add_channel_trigger_type(self, channel_name: str):
        new_channel = channel(channel_name + "_trigger_type", write_function=lambda value: self.set_trigger_type(value))
        new_channel.add_preset("EDGE", "")
        new_channel.add_preset("DIGITAL", "")
        new_channel.add_preset("HYSTERESIS", "")
        new_channel.add_preset("SOFTWARE", "")
        new_channel.add_preset("WINDOW", "")
        new_channel.add_preset("IMMEDIATE", "")
        new_channel._set_value(self.get_trigger_type())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_mode(self, value: str) -> None:
        """ Default:  NORMAL """
        trigger_modes: dict = {
            'NORMAL': 1,
            'AUTO': 2,
        }
        if value.upper() not in trigger_modes:
            raise ValueError(f"Valid values for trigger mode are: {list(trigger_modes.keys())}.")
        self.session.trigger_modifier = niscope.TriggerModifier(trigger_modes[value])

    def get_trigger_mode(self) -> str:
        if self.session.trigger_modifier.value == 1:
            return 'NORMAL'
        else:
            return 'AUTO'

    def add_channel_trigger_mode(self, channel_name: str):
        new_channel = channel(channel_name + '_trigger_mode', write_function=lambda value: self.set_trigger_mode(value))
        new_channel.add_preset("AUTO", "Find a trigger level")
        new_channel.add_preset("NORMAL", "User defined trigger level")
        new_channel._set_value(self.get_trigger_mode())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_source(self, value: str) -> None:
        """ Default: VAL_IMMEDIATE """
        trigger_sources: dict = {
            'CHANNEL0': '0',
            'CHANNEL1': '1',
            'CHANNEL2': '2',
            'CHANNEL3': '3',
            'CHANNEL4': '4',
            'CHANNEL5': '5',
            'CHANNEL6': '6',
            'CHANNEL7': '7',
            'CH0': '0',
            'CH1': '1',
            'CH2': '2',
            'CH3': '3',
            'CH4': '4',
            'CH5': '5',
            'CH6': '6',
            'CH7': '7',
            'C0': '0',
            'C1': '1',
            'C2': '2',
            'C3': '3',
            'C4': '4',
            'C5': '5',
            'C6': '6',
            'C7': '7',
        }
        if value.upper() not in trigger_sources:
            raise ValueError(f"Valid values for trigger source are: {list(trigger_sources.keys())}.")
        self.session.trigger_source = trigger_sources[value]

    def get_trigger_source(self) -> str:
        return f"CHANNEL{self.session.trigger_source}"

    def add_channel_trigger_source(self, channel_name: str):
        new_channel = channel(channel_name + '_trigger_source', write_function=lambda value: self.set_trigger_source(value))
        new_channel.add_preset("CHANNEL0", "Channel 0")
        new_channel.add_preset("CHANNEL1", "Channel 1")
        new_channel.add_preset("CHANNEL2", "Channel 2")
        new_channel.add_preset("CHANNEL3", "Channel 3")
        new_channel.add_preset("CHANNEL4", "Channel 4")
        new_channel.add_preset("CHANNEL5", "Channel 5")
        new_channel.add_preset("CHANNEL6", "Channel 6")
        new_channel.add_preset("CHANNEL7", "Channel 7")
        new_channel._set_value(self.get_trigger_source())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_trigger_source_readback(self, channel_name):
        new_channel = channel(channel_name + "_trigger_source_readback", read_function=lambda: self.get_trigger_source())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_level(self, value: float) -> None:
        """ Default:  0.0 """
        self.session.trigger_level = value

    def get_trigger_level(self) -> float:
        return self.session.trigger_level

    def add_channel_trigger_level(self, channel_name):
        new_channel = channel(channel_name + '_trigger_level', write_function=lambda value: self.set_trigger_level(value))
        new_channel._set_value(self.get_trigger_level())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_trigger_level_readback(self, channel_name):
        new_channel = channel(channel_name + '_trigger_level_readback', read_function=lambda: self.get_trigger_level())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_slope(self, value: str) -> None:
        """ Default:  POSITIVE """
        trigger_slopes: dict = {
            'NEGATIVE': 0,
            'POSITIVE': 1,
            'FALL': 0,
            'RISE': 1,
        }
        if value.upper() not in trigger_slopes:
            raise ValueError(f"Valid values for trigger slope are: {list(trigger_slopes.keys())}.")
        self.session.trigger_slope = niscope.TriggerSlope(trigger_slopes[value])

    def get_trigger_slope(self) -> str:
        return self.session.trigger_slope.name

    def add_channel_trigger_slope(self, channel_name):
        new_channel = channel(channel_name + '_trigger_slope', write_function=lambda value: self.set_trigger_slope(value))
        new_channel.add_preset("POSITIVE", "Positive edges")
        new_channel.add_preset("NEGATIVE", "Negative edges")
        new_channel._set_value(self.get_trigger_slope())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_coupling(self, value: str = 'DC') -> None:
        """ Default:  DC """
        trigger_couplings: dict = {
            'DC': 1,
        }
        if value.upper() not in trigger_couplings:
            raise ValueError(f"Valid values for trigger coupling are: {list(trigger_couplings.keys())}.")
        self.session.trigger_coupling = niscope.TriggerCoupling(trigger_couplings[value])

    def get_trigger_coupling(self) -> str:
        return self.session.trigger_coupling.name

    def add_channel_trigger_coupling(self, channel_name):
        new_channel = channel(channel_name + '_trigger_coupling', write_function=lambda value: self.set_trigger_coupling(value))
        new_channel.add_preset("DC", "DC trigger coupling")
        new_channel._set_value(self.get_trigger_coupling())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_trigger_delay(self, value: float) -> None:
        """ Valid values: 0.0 - 171.8 seconds. Default:  0.0 """
        self.session.trigger_delay_time = value

    def get_trigger_delay(self) -> float:
        time_delta = self.session.trigger_delay_time
        return float(time_delta.total_seconds())

    def add_channel_trigger_delay(self, channel_name):
        new_channel = channel(channel_name + '_trigger_delay', write_function=lambda value: self.set_trigger_delay(value))
        new_channel._set_value(self.get_trigger_delay())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_trigger_delay_readback(self, channel_name):
        new_channel = channel(channel_name + '_trigger_delay_readback', read_function=lambda: self.get_trigger_delay())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    """ Acquisition Control Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def set_acquisition_type(self, value: str) -> None:
        """ Always set to NORMAL at REMOTE mode. """
        acq_types: dict = {
            "SAMPLE": "NORMAL",
            "NORMAL": "NORMAL",
        }
        if value.upper() not in acq_types:
            raise ValueError(f"Valid values for vertical co upling are: {list(acq_types.keys())}.")
        self.session.channels.acquisition_type = niscope.AcquisitionType.NORMAL

    def get_acquisition_type(self) -> str:
        return self.session.acquisition_type.name

    def add_channel_acquisition_type(self, channel_name: str):
        new_channel = channel(channel_name + '_acquisition_type', write_function=lambda value: self.set_acquisition_type(value))
        new_channel.add_preset("NORMAL", "")
        new_channel._set_value(self.get_acquisition_type())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_points_count(self, value: int) -> None:
        """ Default:  10000 """
        self.session.horz_min_num_pts = value

    def get_points_count(self) -> int:
        return int(self.session.horz_record_length)

    def add_channel_points_count(self, channel_name):
        new_channel = channel(channel_name + '_points_count', write_function=lambda value: self.set_points_count(value))
        new_channel._set_value(self.get_points_count())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_points_count_readback(self, channel_name):
        new_channel = channel(channel_name + '_points_count_readback', read_function=lambda: self.get_points_count())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def set_sample_rate(self, value: float) -> None:
        self.session.min_sample_rate = value

    def get_sample_rate(self) -> float:
        return float(self.session.horz_sample_rate)

    def add_channel_sample_rate(self, channel_name):
        new_channel = channel(channel_name + '_sample_rate', write_function=lambda value: self.set_sample_rate(value))
        new_channel._set_value(self.get_sample_rate())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_sample_rate_readback(self, channel_name):
        new_channel = channel(channel_name + '_sample_rate_readback', read_function=lambda: self.get_sample_rate())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def get_identity(self) -> str:
        return  f'{self.session.instrument_model} {self.session.serial_number}'

    def add_channel_identity(self, channel_name):
        new_channel = channel(channel_name + '_identity', read_function=lambda: self.get_identity())
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    def add_channel_units(self, channel_name, channel_number):
        new_channel = channel(channel_name + '_units')
        new_channel.add_preset('A', '')
        new_channel.add_preset('V', '')
        new_channel._set_value('V')
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def set_run_mode(self, value: str) -> None:
        if value.upper() not in ["RUN", "STOP", "SINGLE"]:
            raise ValueError(f"Valid values for run mode are: [RUN, STOP, SINGLE].")

        if value.upper() == "STOP":
            self.session.abort()
        else:
            self.session.abort()
            time.sleep(0.2)
            self.session.initiate()

    def add_channel_run_mode(self, channel_name):
        new_channel = channel(channel_name + '_run_mode', write_function=lambda value: self.set_run_mode(value))
        new_channel.add_preset("RUN", "")
        new_channel.add_preset("STOP", "")
        new_channel.add_preset("SINGLE", "")
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    """ Measurement Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def get_measurement(self, channel_num: int, meas_param: str) -> float:
        meas_types: dict = {
            'RISE_TIME': 0,
            'FALL_TIME': 1,
            'FREQUENCY': 2,
            'PERIOD': 3,
            'VOLTAGE_RMS': 4,
            'VOLTAGE_PEAK_TO_PEAK': 5,
            'VOLTAGE_MAX': 6,
            'VOLTAGE_MIN': 7,
            'VOLTAGE_HIGH': 8, # NO MEASUREMENT CHANNEL
            'VOLTAGE_LOW': 9, # NO MEASUREMENT CHANNEL
            'VOLTAGE_AVERAGE': 10,
            'WIDTH_NEG': 11,
            'WIDTH_POS': 12,
            'DUTY_CYCLE_NEG': 13,
            'DUTY_CYCLE_POS': 14,
            'AMPLITUDE': 15,
            'VOLTAGE_CYCLE_RMS': 16,
            'VOLTAGE_CYCLE_AVERAGE': 17, # NO MEASUREMENT CHANNEL
            'OVERSHOOT': 18,
            'PRESHOOT': 19,
            'LOW_REF_VOLTS': 1000, # NO MEASUREMENT CHANNEL
            'MID_REF_VOLTS': 1001, # NO MEASUREMENT CHANNEL
            'HIGH_REF_VOLTS': 1002, # NO MEASUREMENT CHANNEL
            'AREA': 1003,
            'CYCLE_AREA': 1004, # NO MEASUREMENT CHANNEL
            'INTEGRAL': 1005, # NO MEASUREMENT CHANNEL
            'VOLTAGE_BASE': 1006,
            'VOLTAGE_TOP': 1007,
            'FFT_FREQUENCY': 1008, # NO MEASUREMENT CHANNEL
            'FFT_AMPLITUDE': 1009, # NO MEASUREMENT CHANNEL
            'RISE_SLEW_RATE': 1010,
            'FALL_SLEW_RATE': 1011,
            'AC_ESTIMATE': 1012, # NO MEASUREMENT CHANNEL
            'DC_ESTIMATE':  1013, # NO MEASUREMENT CHANNEL
            'TIME_DELAY': 1014,
            'AVERAGE_PERIOD': 1015, # NO MEASUREMENT CHANNEL
            'AVERAGE_FREQUENCY': 1016, # NO MEASUREMENT CHANNEL
            'VOLTAGE_BASE_TO_TOP': 1017, # NO MEASUREMENT CHANNEL
            'PHASE_DELAY': 1018 # NO MEASUREMENT CHANNEL
        }
        results = self.session.channels[channel_num].fetch_measurement_stats(niscope.ScalarMeasurement(meas_types[meas_param]))
        return results[0].result

    def clear_measurement(self, value: bool) -> None:
        if value:
            self.session.clear_waveform_measurement_stats()

    def add_clear_measurements_channel(self, channel_name: str):
        new_channel = channel(channel_name + '_clear_measurements', write_function=lambda value: self.clear_measurement(value))
        new_channel._read = lambda: False
        new_channel.add_preset(True, '')
        new_channel.add_preset(False, '')
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (None,))
        return new_channel

    """ Amplitude Measurement Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def add_channel_meas_amplitude(self, channel_name: str, channel_number: int):
        new_channel = channel(channel_name + '_meas_amplitude', read_function=lambda: self.get_measurement(channel_num=channel_number, meas_param='AMPLITUDE'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_max(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_max", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_MAX'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_min(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_min", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_MIN'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_peak_to_peak(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_pk2pk", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_PEAK_TO_PEAK'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_pos_overshoot(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_povershoot", read_function=lambda: self.get_measurement(channel_number, 'OVERSHOOT'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_neg_overshoot(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_novershoot", read_function=lambda: self.get_measurement(channel_number, 'PRESHOOT'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_mean(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_mean", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_AVERAGE'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_rms(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_rms", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_RMS'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_acrms(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_acrms", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_CYCLE_RMS'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_top(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_top", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_TOP'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_base(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_base", read_function=lambda: self.get_measurement(channel_number, 'VOLTAGE_BASE'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_area(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_area", read_function=lambda: self.get_measurement(channel_number, 'AREA'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    """ Time Measurement Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def add_channel_meas_period(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_period", read_function=lambda: self.get_measurement(channel_number, 'PERIOD'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_frequency(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_frequency", read_function=lambda: self.get_measurement(channel_number, 'FREQUENCY'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_pos_width(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_pwidth", read_function=lambda: self.get_measurement(channel_number, 'WIDTH_POS'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_neg_width(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_nwidth", read_function=lambda: self.get_measurement(channel_number, 'WIDTH_NEG'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_rise_time(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_rise_time", read_function=lambda: self.get_measurement(channel_number, 'RISE_TIME'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_fall_time(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_fall_time", read_function=lambda: self.get_measurement(channel_number, 'FALL_TIME'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_rise_slew_rate(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_rise_slew_rate", read_function=lambda: self.get_measurement(channel_number, 'RISE_SLEW_RATE'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_fall_slew_rate(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_fall_slew_rate", read_function=lambda: self.get_measurement(channel_number, 'FALL_SLEW_RATE'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_pos_duty(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_pduty", read_function=lambda: self.get_measurement(channel_number, 'DUTY_CYCLE_POS'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_neg_duty(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_nduty", read_function=lambda: self.get_measurement(channel_number, 'DUTY_CYCLE_NEG'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def add_channel_meas_delay(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_meas_delay", read_function=lambda: self.get_measurement(channel_number, 'TIME_DELAY'))
        self._add_channel(new_channel)
        new_channel.set_attribute('dependent_physical_channels', (channel_number,))
        return new_channel

    def plot_scope_channel(self, channel_num: int):
        """
        PLOT THE WAVEFORM FROM THE SELECTED CHANNEL USING MATPLOTLIB
        Note:  This function may trigger a QApplication runtime error when launching channels.gui()
        """
        record_length = self.get_points_count()
        waveform = self.session.channels[channel_num].fetch(num_samples=record_length, timeout=0.0)
        wf = waveform[0]
        y_data = np.frombuffer(wf.samples, dtype=np.float64)  # Convert to NumPy array (voltage samples) for easier processing

        x_start = wf.relative_initial_x
        x_increment = wf.x_increment
        x_data = x_start + np.arange(record_length) * x_increment  # Convert to NumPy array (time data) for easier processing
        x_scale = self.get_xscale()
        y_scale = self.get_yscale(channel_num)

        # PLOT THE WAVEFORM USING MATPLOTLIB
        plt.figure(figsize=(10, 8))
        plt.plot(x_data, y_data, label=f"Channel {wf.channel}")
        plt.xlim(x_scale * -5.0, x_scale * 5.0)
        plt.ylim(y_scale * -4.0, y_scale * 4.0)
        plt.xticks(np.linspace(x_scale * -5.0, x_scale * 5.0, 11))
        plt.yticks(np.linspace(y_scale * -4.0, y_scale * 4.0, 9))
        plt.title("Oscilloscope Waveform PXIe-5172")
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
        plt.grid(True)
        plt.legend()
        plt.show()

    def __del__(self):
        """ This ensures the class cleans up explicitly. Prevents the driver’s background cleanup from firing at exit."""
        try:
            self.session.close()
        except Exception:
            pass

if __name__ == "__main__":
    channels = master()
    scope_channels = {"CH0": 0}
    scope = pxie_5172("PXI1Slot3")
    channels.add(scope)
    print(f'MODEL: {scope.session.instrument_model}')
    print(f'SERIAL: {scope.session.serial_number}')
    scope.setup_channels(scope_channels=scope_channels)
    scope.resync_scope()
    # scope.add_channel_meas_amplitude(channel_name="CH0", channel_number=0)
    # scope.add_channel_meas_frequency(channel_name="CH0", channel_number=0)
    breakpoint()
    scope.__del__()