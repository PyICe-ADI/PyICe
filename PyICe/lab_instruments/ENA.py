"""E N A instrument driver.

>>> from PyICe.lab_instruments.ENA import scpi_NA

"""
from ..lab_core import *  # noqa: F403
import abc

screen_configs = '''
┌───────────┐
│           │D1
│           │
│     1     │
│           │
│           │
└───────────┘
┌─────┬─────┐
│     │     │D12
│     │     │
│  1  │  2  │
│     │     │
│     │     │
└─────┴─────┘
┌───────────┐
│     1     │D1_2
│           │
├───────────┤
│           │
│     2     │
└───────────┘
┌───────┬───┐
│       │   │D112
│       │   │
│    1  │ 2 │
│       │   │
│       │   │
└───────┴───┘
┌───────────┐
│           │D1_1_2
│     1     │
│           │
├───────────┤
│     2     │
└───────────┘
┌───┬───┬───┐
│   │   │   │D123
│   │   │   │
│ 1 │ 2 │ 3 │
│   │   │   │
└───┴───┴───┘
┌───────────┐
│     1     │D1_2_3
├───────────┤
│     2     │
├───────────┤
│     3     │
└───────────┘
┌─────┬─────┐
│  1  │  2  │D12_33
│     │     │
├─────┴─────┤
│           │
│     3     │
│           │
└───────────┘
┌───────────┐
│           │D11_23
│     1     │
│           │
├─────┬─────┤
│     │     │
│  2  │  3  │
└─────┴─────┘
┌─────┬─────┐
│  1  │     │D13_23
│     │     │
├─────┤  3  │
│     │     │
│  2  │     │
└─────┴─────┘
┌─────┬─────┐
│     │  2  │D12_13
│     │     │
│  1  ├─────┤
│     │     │
│     │  3  │
└─────┴─────┘
┌──┬──┬──┬──┐
│  │  │  │  │D1234
│  │  │  │  │
│ 1│ 2│ 3│ 4│
│  │  │  │  │
└──┴──┴──┴──┘
┌───────────┐
│     1     │D1_2_3_4
├───────────┤
│     2     │
├───────────┤
│     3     │
├───────────┤
│     4     │
└───────────┘
┌─────┬─────┐
│  1  │  2  │D12_34
│     │     │
├─────┼─────┤
│     │     │
│  3  │  4  │
└─────┴─────┘'''


class scpi_NA(scpi_instrument, abc.ABC):
    """TODO: Add docstring."""
    # todo abstract methods?
# class keysight_e5061b_base(scpi_NA, abc.ABC):


class keysight_e5061b_base(scpi_NA, metaclass=abc.ABCMeta):
    # class keysight_e5061b_base(abc.ABC):
    """TODO: Add docstring."""

    def __init__(self, interface_visa, halt_sweep=True):
        """Initialize Keysight E5061B ENA network analyzer.
        Calls the parent class constructor and initializes instance-specific
        attributes for keysight_e5061b_base.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface address string.
            halt_sweep: If True (default), stops continuous sweep on all
                channels. Set to False to leave the instrument sweeping
                (useful when reading existing front-panel data).
        """
        self._base_name = 'Keysight E5061B ENA network analyzer'
        super(keysight_e5061b_base, self).__init__(
            f"Keysight E5061B @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        # todo trace dict to track down channel_name?
        self._configured_traces = {ch: [] for ch in range(1, 5)}
        # turn off unpoulated channels to avoid confusing status condition
        # register monitoring sweep/trigger status?
        if halt_sweep:
            for i in range(1, 5):
                self.get_interface().write(f':INITiate{i}:CONTinuous OFF')

    def discover_and_configure(self, base_name='ena'):
        """Query the instrument for its current front-panel configuration and register channels.

        Discovers which channels/traces are active on the instrument and calls
        the appropriate add_channel_* methods so that this instrument object has
        registered PyICe channels matching the live hardware state. Includes
        trace data, sweep settings, display layout, trigger, source power,
        bias, and per-trace display scaling channels.

        Prompts the user to name each discovered trace.

        Args:
            base_name: Prefix for auto-created setting channel names.

        Returns:
            A summary dict of what was discovered and configured.
        """
        iface = self.get_interface()
        discovered = {}

        for channel_number in range(1, 5):
            trace_count = int(iface.ask(f':CALCulate{channel_number}:PARameter:COUNt?'))
            if trace_count == 0:
                continue

            ch_key = f'ch{channel_number}'
            discovered[ch_key] = {'traces': []}

            if not self._configured_traces[channel_number]:
                self.add_xchannels(f'{base_name}_{ch_key}', channel_number=channel_number)

            self.add_channel_display_split(f'{base_name}_{ch_key}_display_split', channel_number=channel_number)

            for trace_number in range(1, trace_count + 1):
                if trace_number in self._configured_traces[channel_number]:
                    continue

                iface.write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
                measurement = iface.ask(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine?')
                data_format = iface.ask(f':CALCulate{channel_number}:SELected:FORMat?')

                print(f"  Channel {channel_number}, Trace {trace_number}: {measurement} ({data_format})")
                user_name = ''
                while not len(user_name):
                    user_name = input(f"    Name for this trace: ")
                trace_name = f'{base_name}_{user_name}'

                self.add_channel_ydata(trace_name, trace_number=trace_number, channel_number=channel_number)
                self._configured_traces[channel_number].append(trace_number)

                if hasattr(self, 'add_channel_rlevel'):
                    self.add_channel_rlevel(f'{trace_name}_rlevel',
                                            channel_number=channel_number, trace_number=trace_number)
                if hasattr(self, 'add_channel_pdiv'):
                    self.add_channel_pdiv(f'{trace_name}_pdiv',
                                          channel_number=channel_number, trace_number=trace_number)

                discovered[ch_key]['traces'].append({
                    'trace_number': trace_number,
                    'measurement': measurement,
                    'format': data_format,
                    'channel_name': trace_name,
                })

            if hasattr(self, 'add_channel_divisions'):
                self.add_channel_divisions(f'{base_name}_{ch_key}_divisions', channel_number=channel_number)

        # Trigger
        trigger_names = [ch.get_name() for ch in self.get_all_channels_list()
                         if ch.get_attribute('channel_type') == 'trig_control']
        if not trigger_names:
            self.add_channel_trigger(f'{base_name}')

        # Source power
        self.add_channels_source_power(f'{base_name}_source_power')

        # Bias control
        self.add_channels_bias_control(f'{base_name}_bias')

        # GP port control
        self.add_channels_gp_control(f'{base_name}_gp')

        print(f"Discovered {sum(len(v['traces']) for v in discovered.values())} trace(s) "
              f"across {len(discovered)} channel(s).")
        for ch_key, info in discovered.items():
            for t in info['traces']:
                print(f"  {ch_key} trace {t['trace_number']}: {t['measurement']} ({t['format']})")
        return discovered

    def _check_trace_unconfigured(self, trace_number, channel_number):
        # what about more than 4 measurements from the same sweep (logged but
        # not displayed)
        assert trace_number in range(
            1, 5), f'trace_number argument {trace_number} must be between 1 and 4 inclusive.'
        assert channel_number in range(
            1, 5), f'trace_number argument {trace_number} must be between 1 and 4 inclusive.'
        if trace_number in self._configured_traces[channel_number]:
            raise Exception(
                f'Trace {trace_number} already configured in channel {channel_number}.')
        else:
            self._configured_traces[channel_number].append(trace_number)
        if max(self._configured_traces[channel_number]) == 1:
            layout = 'D1'
        elif max(self._configured_traces[channel_number]) == 2:
            layout = 'D1_2'
        elif max(self._configured_traces[channel_number]) == 3:
            layout = 'D1_2_3'
        elif max(self._configured_traces[channel_number]) == 4:
            layout = 'D1_2_3_4'
        else:
            raise Exception(
                "ENA network Analyzer: I'm lost - '_check_trace_unconfigured'")
        # {D1|D12|D1_2|D112|D1_1_2|D123|D1_2_3|D12_33|D11_23|D13_23|D12_13| D1234|D1_2_3_4|D12_34}
        self.get_interface().write(
            f':DISPlay:WINDow{channel_number}:SPLit {layout}')
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter:COUNt {max(self._configured_traces[channel_number])}')
        # TODO What about setting channel count and layout???

    def add_channels(self, channel_name, channel_number=1):
        """Shortcut method to add chx/trace1 channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the channels.
            channel_number: Instrument channel number.

        Returns:
            List of created channel objects.
        """
        channels = []
        channels.extend(
            self.add_xchannels(
                channel_name,
                channel_number=channel_number))
        # what about multiple channels? Just one trigger??
        channels.append(self.add_channel_trigger(channel_name))
        # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))
        channels.append(self.add_channel_error(f'{channel_name}_errors'))
        return channels

    def add_channel_display_split(self, channel_name, channel_number):
        """Add a channel display split.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the new channel.
            channel_number: Physical channel number.

        Returns:
            The newly created channel object.
        """
        '''Configures the screen splitting of the display.

        Args:
            channel_name: Name for the display split channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created display split channel.
        '''
        new_channel = channel(
            channel_name, write_function=lambda layout: self.get_interface().write(
                f':DISPlay:WINDow{channel_number}:SPLit {layout}'))
        new_channel._read = lambda: self.get_interface().ask(
            ':DISPlay:WINDow{channel_number}:SPLit?')
        new_channel.add_preset("D1")
        new_channel.add_preset("D12")
        new_channel.add_preset("D1_2")
        new_channel.add_preset("D112")
        new_channel.add_preset("D1_1_2")
        new_channel.add_preset("D123")
        new_channel.add_preset("D1_2_3")
        new_channel.add_preset("D12_33")
        new_channel.add_preset("D11_23")
        new_channel.add_preset("D13_23")
        new_channel.add_preset("D12_13")
        new_channel.add_preset("D1234")
        new_channel.add_preset("D1_2_3_4")
        new_channel.add_preset("D12_34")
        new_channel.set_attribute('channel_type', 'screen_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_display_split.__doc__)
        return self._add_channel(new_channel)
    add_channel_display_split.__doc__ += '\n' + screen_configs

    def add_xchannels(self, channel_name, channel_number=1):
        """Shortcut method to add chx x-axis channels.
        Adds a new xchannels to the object's internal collection.

        Appends a new xchannels entry to the object's internal collection.

        Args:
            channel_name: Base name for the x-axis channels.
            channel_number: Instrument channel number.

        Returns:
            List of created x-axis channel objects.
        """
        channels = []
        channels.append(
            self.add_channel_xdata(
                f'{channel_name}_fpoints',
                channel_number=channel_number))
        channels.append(
            self.add_channel_start_freq(
                f'{channel_name}_fstart',
                channel_number=channel_number))
        channels.append(
            self.add_channel_stop_freq(
                f'{channel_name}_fstop',
                channel_number=channel_number))
        channels.append(
            self.add_channel_points(
                f'{channel_name}_point_count',
                channel_number=channel_number))
        channels.append(
            self.add_channel_sweep_type(
                f'{channel_name}_sweep_type',
                channel_number=channel_number))
        channels.append(
            self.add_channel_IFBW(
                f'{channel_name}_RBW',
                channel_number=channel_number))
        # channels.append(self.add_channel_IFBW_readback(f'{channel_name}_RBW_readback', channel_number=channel_number))
        channels.append(
            self.add_channel_sweep_time(
                f'{channel_name}_sweep_time',
                channel_number=channel_name))
        return channels

    def add_channel_error(self, channel_name):
        """Error readback channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the error channel.

        Returns:
            The newly created error channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: '\n'.join(
                self.get_errors()))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_error.__doc__)
        return self._add_channel(new_channel)

    def _read_trace_data(self, trace_number, channel_number, complex=False):
        # ascii. TODO binary?
        # Indicates the array data (formatted data array) of NOP
        # (number of measurement points)×2. Where n is an
        # integer between 1 and NOP.
        #  Data(n×2-2) :Data (primary value) at the nth measurement point.
        #  Data(n×2-1) :Data (secondary value) at the
        # n-th measurement point. Always 0 when the data
        # format is not the Smith chart format or the polar
        # format.
        # The index of the array starts from 0.
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        resp = self.get_interface().ask(
            f':CALCulate{channel_number}:SELected:DATA:FDATa?').split(',')
        if not complex:
            return [float(y) for i, y in enumerate(resp) if not i % 2]
        else:
            raise Exception('ENA: _read_trace_data: Implement me!')

    def _read_x_data(self, channel_number):
        resp = self.get_interface().ask(
            f':SENSe{channel_number}:FREQuency:DATA?').split(',')
        return [float(x) for x in resp]

    def add_channel_ydata(self, channel_name,
                          trace_number=1, channel_number=1):
        """Trace data vector.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the y-data channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The newly created y-data channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda trace_number=trace_number,
            channel_number=channel_number: self._read_trace_data(
                trace_number,
                channel_number))
        new_channel.set_attribute('trace_number', trace_number)
        new_channel.set_attribute('channel_type', 'y_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_ydata.__doc__)
        return self._add_channel(new_channel)

    def add_channel_xdata(self, channel_name, channel_number=1):
        """Frequency sweep data vector.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the x-data channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created x-data channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._read_x_data(channel_number))
        new_channel.set_attribute('channel_type', 'x_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_xdata.__doc__)
        return self._add_channel(new_channel)

    def add_channel_start_freq(self, channel_name, channel_number=1):
        """Sweep start (low) frequency control.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the start frequency channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created start frequency channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda freq,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:FREQuency:STARt {freq}'))
        new_channel.add_preset(3)
        new_channel.add_preset(10)
        new_channel.add_preset(100)
        new_channel.add_preset(300)
        new_channel.add_preset(1e3)
        new_channel.add_preset(1e4)
        new_channel.add_preset(1e5)
        new_channel._set_value(
            float(
                self.get_interface().ask(
                    f':SENSe{channel_number}:FREQuency:STARt?')))
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_start_freq.__doc__)
        return self._add_channel(new_channel)

    def add_channel_stop_freq(self, channel_name, channel_number=1):
        """Sweep stop (high) frequency control.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the stop frequency channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created stop frequency channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda freq,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:FREQuency:STOP {freq}'))
        new_channel._read = lambda: float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        new_channel.add_preset(1e6)
        new_channel.add_preset(3e6)
        new_channel.add_preset(10e6)
        new_channel.add_preset(30e6)
        new_channel.add_preset(100e6)
        new_channel.add_preset(300e6)
        # new_channel._set_value(float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?')))
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_stop_freq.__doc__)
        return self._add_channel(new_channel)

    def add_channel_points(self, channel_name, channel_number=1):
        """Number of trace data points.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the points channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created points channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda points,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:SWEep:POINts {points}'))
        new_channel._read = lambda: int(
            self.get_interface().ask(
                f':SENSe{channel_number}:SWEep:POINts?'))
        # new_channel._set_value(int(self.get_interface().ask(f':SENSe{channel_number}:SWEep:POINts?')))
        new_channel.add_preset(201)
        new_channel.add_preset(1601)
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_points.__doc__)
        return self._add_channel(new_channel)

    def add_channel_sweep_type(self, channel_name, channel_number=1):
        """Sweep variable control.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the sweep type channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created sweep type channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda stype,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:SWEep:TYPE {stype}'))
        new_channel._set_value(
            self.get_interface().ask(
                f':SENSe{channel_number}:SWEep:TYPE?'))
        new_channel.add_preset('LINear')
        new_channel.add_preset('LOGarithmic')
        new_channel.add_preset('SEGMent')
        new_channel.add_preset('POWer')
        new_channel.add_preset('BIAS')
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_sweep_type.__doc__)
        return self._add_channel(new_channel)

    def add_channel_IFBW(self, channel_name, channel_number=1):
        """IF/resolution bandwidth. TODO: Disrespected when IFBW set to AUTO.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the IFBW channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created IFBW channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda rbw,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:BANDwidth:RESolution {rbw}'))
        new_channel._read = lambda: float(
            self.get_interface().ask(
                f':SENSe{channel_number}:BANDwidth:RESolution?'))
        # new_channel._set_value(float(self.get_interface().ask(f':SENSe{channel_number}:BANDwidth:RESolution?')))
        new_channel.add_preset(1)
        new_channel.add_preset(5)
        new_channel.add_preset(10)
        new_channel.add_preset(50)
        new_channel.add_preset(100)
        new_channel.add_preset(500)
        new_channel.add_preset(1000)
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_IFBW.__doc__)
        return self._add_channel(new_channel)
    # def add_channel_IFBW_readback(self, channel_name, channel_number=1):
        # '''redback of RBW. May differ from setting because of discretized steps.'''
        # new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: float(self.get_interface().ask(f':SENSe{channel_number}:BANDwidth:RESolution?')))
        # new_channel.set_attribute('channel_type', 'x_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_IFBW_readback.__doc__)
        # return self._add_channel(new_channel)
    # TODO IFBW Auto and Auto Limit control channels.

    def add_channel_sweep_time(self, channel_name, channel_number=1):
        """Sweep time control.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SWEep:TIME:DATA`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the sweep time channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created sweep time channel.
        """
        channel_number = 1  # TODO

        def _set_sweep_time(time, channel_number=channel_number):
            if time == 'AUTO':  # TODO seperate auto channel?
                self.get_interface().write(
                    f':SENSe{channel_number}:SWEep:TIME:AUTO ON')
            else:
                self.get_interface().write(
                    f':SENSe{channel_number}:SWEep:TIME:AUTO OFF')
                self.get_interface().write(
                    f':SENSe{channel_number}:SWEep:TIME:DATA {time}')
        new_channel = channel(channel_name, write_function=_set_sweep_time)
        new_channel._read = lambda: float(self.get_interface().ask(
            # Auto setting suppressed
            f':SENSe{channel_number}:SWEep:TIME:DATA?'))
        new_channel.add_preset('AUTO')
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_sweep_time.__doc__)
        return self._add_channel(new_channel)

    def add_channel_display(self, channel_name):
        """Display control channel.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the display channel.
        """
        # axis linlog-y, reference level, scale/div, autoscale, division_count, etc
        # trace allocation

    def add_channels_gp_control(self, channel_name):  # todo channl number???
        """General purpose port control channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Base name for the GP control channels.

        Returns:
            List of created GP control channel objects.
        """
        channels = []
        r_z = channel(
            f'{channel_name}_R_Z',
            write_function=lambda z: self.get_interface().write(
                f':INPut:IMPedance:GPPort:R {z}'))
        r_z._read = lambda: int(
            float(
                self.get_interface().ask(
                    ':INPut:IMPedance:GPPort:R?')))
        r_z.set_description(self.get_name() + ': ' +
                            self.add_channels_gp_control.__doc__)
        r_z.add_preset(50)
        r_z.add_preset(1e6)
        channels.append(self._add_channel(r_z))

        t_z = channel(
            f'{channel_name}_T_Z',
            write_function=lambda z: self.get_interface().write(
                f':INPut:IMPedance:GPPort:T {z}'))
        t_z._read = lambda: int(
            float(
                self.get_interface().ask(
                    ':INPut:IMPedance:GPPort:T?')))
        t_z.set_description(self.get_name() + ': ' +
                            self.add_channels_gp_control.__doc__)
        t_z.add_preset(50)
        t_z.add_preset(1e6)
        channels.append(self._add_channel(t_z))

        r_a = channel(
            f'{channel_name}_R_Atten',
            write_function=lambda a: self.get_interface().write(
                f':INPut:ATTenuation:GPPort:R {a}'))
        r_a._read = lambda: int(
            float(
                self.get_interface().ask(
                    ':INPut:ATTenuation:GPPort:R?')))
        r_a.set_description(self.get_name() + ': ' +
                            self.add_channels_gp_control.__doc__)
        r_a.add_preset(0)
        r_a.add_preset(20)
        channels.append(self._add_channel(r_a))

        t_a = channel(
            f'{channel_name}_T_Atten',
            write_function=lambda a: self.get_interface().write(
                f':INPut:ATTenuation:GPPort:T {a}'))
        t_a._read = lambda: int(
            float(
                self.get_interface().ask(
                    ':INPut:ATTenuation:GPPort:T?')))
        t_a.set_description(self.get_name() + ': ' +
                            self.add_channels_gp_control.__doc__)
        t_a.add_preset(0)
        t_a.add_preset(20)
        channels.append(self._add_channel(t_a))

        return channels

    def add_channels_bias_control(self, channel_name):  # TODO channel number!
        """Bias sweep currently unsupported TODO.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Base name for the bias control channels.

        Returns:
            List of created bias control channel objects.
        """
        channels = []

        def _write_bias_enable_port(p):
            if p == 'Off':
                self.get_interface().write(':SOURce:BIAS:ENABle OFF')
            elif p in ('LFOut', 'P1'):
                self.get_interface().write(f':SOURce:BIAS:PORT {p}')
                # should this really be here and mixed??
                self.get_interface().write(':SOURce:BIAS:ENABle ON')
            else:
                raise Exception(f'Unexpected channel write value {p}')

        def _read_bias_enable_port():
            en = int(self.get_interface().ask(':SOURce:BIAS:ENABle?'))
            if en:
                port = self.get_interface().ask(':SOURce:BIAS:PORT?')
                if port == 'LFO':
                    port = 'LFOut'
                return port
            else:
                return 'Off'
        bias_port_en_ch = channel(
            f'{channel_name}_port',
            write_function=_write_bias_enable_port)
        bias_port_en_ch._read = _read_bias_enable_port
        bias_port_en_ch.set_description(
            self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
        bias_port_en_ch.add_preset('Off')
        bias_port_en_ch.add_preset('LFOut', 'G/P source port')
        bias_port_en_ch.add_preset('P1', 'S-param port 1')
        channels.append(self._add_channel(bias_port_en_ch))

        bias_voltage_ch = channel(
            f'{channel_name}_voltage',
            write_function=lambda v: self.get_interface().write(
                f':SOURce:BIAS:VOLTage {v}'))
        bias_voltage_ch._read = lambda: float(
            self.get_interface().ask(':SOURce:BIAS:VOLTage?'))
        bias_voltage_ch.set_description(
            self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
        bias_voltage_ch.add_preset(0)
        channels.append(self._add_channel(bias_voltage_ch))

        return channels

    # TODO channel number!
    def add_channels_source_power(self, channel_name, port='GP'):
        """Source power control in dBm.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the source power channel.
            port: Port selection, either 'GP' or a port number.

        Returns:
            Tuple of created power channel objects.

        Raises:
            Exception: If port is not 'GP' (non-GP ports not yet implemented).
        """
        # NB 460 Continuous switching may damage source. This error occurs when different power ranges are selected in multiple channel measurement settings to avoid source attenuator damage.
        # TODO sync channel powers...
        assert port in ('GP', 1, 2, 3, 4)
        if port == 'GP':
            power_ch = channel(
                f'{channel_name}',
                write_function=lambda p: self.get_interface().write(
                    f':SOURce{1}:POWer:GPPort:LEVel:IMMediate:AMPLitude {p}'))
            power_ch._read = lambda: float(self.get_interface().ask(
                f':SOURce{1}:POWer:GPPort:LEVel:IMMediate:AMPLitude?'))
            power_ch.set_description(
                self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
            power_ch.add_preset(0)
            power_ch.set_min_write_limit(-45)
            power_ch.set_max_write_limit(10)
            self._add_channel(power_ch)
            return (power_ch,)
        else:
            raise Exception('ENA add_channels_power_source: Implement me')
            # :SOURce{[1]-4}:POWer:PORT{[1]|2}[:LEVel][:IMMediate][:AMPLitude] <numeric>
            # :SOURce{[1]-4}:POWer:PORT{[1]|2}[:LEVel][:IMMediate][:AMPLitude]?
            # :SOURce{[1]-4}:POWer[:LEVel]:SLOPe[:DATA] <numeric>
            # :SOURce{[1]-4}:POWer[:LEVel]:SLOPe[:DATA]?
            # :SOURce{[1]-4}:POWer[:LEVel][:IMMediate][:AMPLitude] <numeric>
            # :SOURce{[1]-4}:POWer[:LEVel][:IMMediate][:AMPLitude]?

    def add_marker(self, channel_name, marker_number,
                   trace_number, channel_number=1):
        """Add marker channels for x and y readback.
        Sends the ``:`` SCPI command to the instrument.
        Adds a new marker to the object's internal collection.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Base name for the marker channels.
            marker_number: Marker number on the instrument.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            List of created marker channel objects.
        """
        channels = []
        assert marker_number in range(1, 11)
        m_x = channel(f'{channel_name}_x', write_function=lambda x: self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:X {x}'))
        m_x._read = lambda: float(
            self.get_interface().ask(
                f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:X?'))
        m_x.set_description(self.get_name() + ': ' + self.add_marker.__doc__)
        m_x.set_attribute('trace_number', trace_number)
        m_x.set_attribute('marker_number', marker_number)
        channels.append(self._add_channel(m_x))

        m_y = channel(f'{channel_name}_y', read_function=lambda: float(self.get_interface().ask(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:Y?').split(',')[0]))
        m_y.set_description(self.get_name() + ': ' + self.add_marker.__doc__)
        m_y.set_attribute('trace_number', trace_number)
        m_y.set_attribute('marker_number', marker_number)
        channels.append(self._add_channel(m_y))

        return channels

        # SCPI.CALCulate(1).PARameter(1).SELect
        # SCPI.CALCulate(1).SELected.MARKer(1).ACTivate
        # SCPI.CALCulate(1).SELected.MARKer(1).X = 1E9
        # MkrX = SCPI.CALCulate(1).SELected.MARKer(1).X
        # MkrY = SCPI.CALCulate(1).SELected.MARKer(1).Y
        # SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TYPE = "targ"
        # SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TRACking = True
        # SrchTrac = SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TRACking

    def add_channel_trigger(self, channel_name):
        # TODO channel number!
        # todo all-channel controls?
        """Trigger control channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:TRIGger:SEQuence:SOURce`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Base name for the trigger channels.

        Returns:
            Tuple of mode, source, and slope trigger channels.
        """
        channel_number = 1

        def _single_abort_trigger_wait(run_mode):
            """Channels.write function for the {ENA}_trigger_mode channel.

            Configures the ENA to run a continuous measurement sweep or
            triggers a single measurement sweep.

            When triggering a single sweep, this function will wait and
            poll a bitfield in the ENA that indicates if a measurement
            is active or not until the measurement is no longer active.

            When setting the ENA to continuous sweep, the ENA will be
            set to continuous sweep mode, and this function will return
            control of the program.

            This trigger code was derived from the examples in the ENA
            user manual, "Starting a Measurement Cycle (Triggering the
            Instrument)" and "Waiting for the End of Measurement", on
            pages 613 and 614. However, in waiting for the end, the
            recommendations are to form an SRQ or use the "*OPC?"
            command. Both of these recommendations would use the
            measurement status bit in the operation status condition
            register, so the measurement status bit is polled in this
            function instead. This is because the SRQ involves
            unnecessary steps, and the OPC command is a blocking
            command that will cause the instrument to time out in its
            VISA communication.

            Args:
                run_mode (string): Sets the sweep mode of the ENA, must
                    be "Single" or "Continuous".

            Raises:
                Exception: If run_mode is not "Single" or "Continuous"
            """
            if run_mode not in ['Single', 'Continuous']:
                exception_str = f'ENA: Unknown trigger/run mode {run_mode}. Expected ' + \
                    '"Single" or "Continuous".'
                raise Exception(exception_str)
            if run_mode == 'Single':
                self.get_interface().write(':ABORt')
            self.get_interface().write(
                f':INITiate{channel_number}:CONTinuous ON')
            if run_mode == 'Single':
                expected_time = float(
                    self.get_interface().ask(':SENSe:SWEep:TIME?'))
                self.get_interface().write(':TRIGger:SOURce BUS')
                self.get_interface().write(':TRIGger:SINGle')
                datetime_now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                print(
                    f'{datetime_now_str} trigger time. Expected sweep time {expected_time}s.')
            else:
                self.get_interface().write(':TRIGger:SOURce INTernal')
                print('ENA Continuous sweep activated.')
                return
            status = True
            while status:
                time.sleep(0.1)  # ?!?
                status_register = int(
                    self.get_interface().ask(':STATus:OPERation:CONDition?'))
                # Bitmask 'Measurement' bit
                status = (status_register & int('00010000')) >> 4
                # print(f'Waiting for status 0 (idle). Got {status} ({type(status)})')

        def _single_write_cb(ch, v):
            # print(f'{ch.get_name()} writtent to {v}')
            if v == 'Single':
                ch._set_value('Stop')
        mode_channel = channel(
            f'{channel_name}_trigger_mode',
            write_function=_single_abort_trigger_wait)
        # mode_channel._read = lambda: None #Don't cache value that only has
        # side-effect value
        mode_channel.add_preset('Single')
        mode_channel.add_preset('Continuous')
        mode_channel.add_write_callback(_single_write_cb)
        inital_mode = int(
            self.get_interface().ask(
                f':INITiate{channel_number}:CONTinuous?'))
        if inital_mode:
            mode_channel._set_value('Continuous')
        else:
            # sort of... It might be finishing the last sweep!
            mode_channel._set_value('Stop')
        mode_channel.set_attribute('channel_type', 'trig_control')
        mode_channel.set_description(
            self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(mode_channel)

        #
        source_channel = channel(
            f'{channel_name}_trigger_source',
            write_function=lambda s: self.get_interface().write(
                f':TRIGger:SEQuence:SOURce {s}'))
        source_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:SOURce?')
        source_channel.add_preset('INTernal')
        source_channel.add_preset('EXTernal')
        source_channel.add_preset('MANual}')
        source_channel.add_preset('BUS}')

        source_channel.set_attribute('channel_type', 'trig_control')
        source_channel.set_description(
            self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(source_channel)

        slope_channel = channel(
            f'{channel_name}_trigger_slope',
            write_function=lambda s: self.get_interface().write(
                f':TRIGger:SEQuence:EXTernal:SLOPe {s}'))
        slope_channel._read = lambda: self.get_interface().ask(
            ':TRIGger:SEQuence:EXTernal:SLOPe?')
        slope_channel.add_preset('POSitive')
        slope_channel.add_preset('NEGative')
        slope_channel.set_attribute('channel_type', 'trig_control')
        slope_channel.set_description(
            self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(slope_channel)

        # todo event, scope, delay

        return (mode_channel, source_channel, slope_channel)
        # todo read_delegated blocking / autotrigger??

    @classmethod
    def plot_from_database(cls, db_filename, table_name, rows=None, output_svg=True):
        """Read logged ENA data from SQLite and produce a frequency-response plot.

        Does not require an instrument connection. Identifies x_data (frequency)
        and y_data (trace) columns using the companion metadata table written by
        instrument_data_dump, or falls back to naming conventions for older files.

        Args:
            db_filename: Path to the SQLite database file.
            table_name: Name of the data table to plot.
            rows: Which measurement rows to plot. Accepts:
                - None: plot all rows (overlaid)
                - int: plot a single row by index
                - slice: plot a range of rows
                - list of int: plot specific rows
            output_svg: If True (default), render to SVG file alongside the
                database. The file is named '{db_basename}_{table_name}.svg'.

        Returns:
            The LTC_plot.Page object for further customization or rendering.
        """
        from ..lab_utils.sqlite_data import sqlite_data
        from .. import LTC_plot
        import sqlite3
        import numpy
        import os

        colors = [LTC_plot.LT_RED_1, LTC_plot.LT_BLUE_1, LTC_plot.LT_GREEN_1,
                  LTC_plot.LT_COPPER_1, LTC_plot.LT_RED_2, LTC_plot.LT_BLUE_2,
                  LTC_plot.LT_GREEN_2, LTC_plot.LT_COPPER_2]

        # --- Discover column roles from metadata table or naming convention ---
        meta_table = f'{table_name}_channel_meta'
        conn = sqlite3.connect(db_filename)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (meta_table,))
        has_meta = cursor.fetchone() is not None

        x_columns = []  # (column_name,)
        y_columns = []  # (column_name, measurement_label)

        if has_meta:
            rows_meta = conn.execute(
                f'SELECT channel_name, channel_type, measurement FROM [{meta_table}]'
            ).fetchall()
            for ch_name, ch_type, measurement in rows_meta:
                if ch_type == 'x_data':
                    x_columns.append(ch_name)
                elif ch_type == 'y_data':
                    label = measurement if measurement else ch_name
                    y_columns.append((ch_name, label))
        else:
            # Fallback: columns ending in '_fpoints' are frequency axes,
            # other numpy array columns are traces
            db_temp = sqlite_data(table_name=table_name, database_file=db_filename)
            col_names = db_temp.get_column_names()
            col_types = db_temp.get_column_types()
            for name in col_names:
                if name.endswith('_fpoints'):
                    x_columns.append(name)
                elif col_types.get(name) == numpy.ndarray:
                    y_columns.append((name, name))

        conn.close()

        if not x_columns or not y_columns:
            raise ValueError(
                f"Could not identify trace data in table '{table_name}'. "
                f"Found {len(x_columns)} x_data and {len(y_columns)} y_data columns.")

        # --- Load data rows ---
        db = sqlite_data(table_name=table_name, database_file=db_filename)
        total_rows = len(db)

        if rows is None:
            row_indices = list(range(total_rows))
        elif isinstance(rows, int):
            row_indices = [rows]
        elif isinstance(rows, slice):
            row_indices = list(range(*rows.indices(total_rows)))
        else:
            row_indices = list(rows)

        # --- Match y columns to their x column (shared prefix before _fpoints) ---
        def find_x_for_y(y_name):
            for x_name in x_columns:
                prefix = x_name.rsplit('_fpoints', 1)[0]
                if y_name.startswith(prefix):
                    return x_name
            return x_columns[0]

        # --- Build the plot ---
        freq_min = float('inf')
        freq_max = 0
        y_min = float('inf')
        y_max = float('-inf')

        trace_data_pairs = []
        for row_idx in row_indices:
            row = db[row_idx]
            for y_col, label in y_columns:
                x_col = find_x_for_y(y_col)
                x_arr = row[x_col]
                y_arr = row[y_col]
                if x_arr is None or y_arr is None:
                    continue
                freq_min = min(freq_min, x_arr.min())
                freq_max = max(freq_max, x_arr.max())
                y_min = min(y_min, y_arr.min())
                y_max = max(y_max, y_arr.max())
                row_label = f'{label} [row {row_idx}]' if len(row_indices) > 1 else label
                trace_data_pairs.append((x_arr, y_arr, row_label))

        if not trace_data_pairs:
            raise ValueError(f"No valid trace data found in selected rows of '{table_name}'.")

        # Round axis limits to nice values
        y_margin = (y_max - y_min) * 0.1 if y_max > y_min else 5
        y_plot_min = y_min - y_margin
        y_plot_max = y_max + y_margin
        ydivs = 10
        yminor = 2

        bode_plot = LTC_plot.plot(
            plot_title=f'{table_name}',
            plot_name=table_name,
            xaxis_label='FREQUENCY (Hz)',
            yaxis_label='MAGNITUDE (dB)',
            xlims=(freq_min, freq_max),
            ylims=(y_plot_min, y_plot_max),
            xminor=1,
            xdivs=10,
            yminor=yminor,
            ydivs=ydivs,
            logx=True,
            logy=False,
        )

        for i, (x_arr, y_arr, label) in enumerate(trace_data_pairs):
            color = colors[i % len(colors)]
            data = list(zip(x_arr.tolist(), y_arr.tolist()))
            bode_plot.add_trace(axis=1, data=data, color=color, legend=label)

        bode_plot.add_legend(axis=1, location=(0.01, 0.01),
                             justification='lower left', use_axes_scale=False)

        # --- Render ---
        page = LTC_plot.Page(rows_x_cols=None, page_size=None, plot_count=1)
        page.add_plot(plot=bode_plot)

        if output_svg:
            base = os.path.splitext(db_filename)[0]
            svg_name = f'{base}_{table_name}_bode'
            page.create_svg(svg_name)
            print(f'Plot saved to {svg_name}.svg')

        return page


class keysight_e5061b(keysight_e5061b_base):
    """Keysight_e5061b (keysight_e5061b_base subclass)."""
    # def __init__(self, interface_visa):
    # super(keysight_e5061b, self).__init__(interface_visa)
    def add_channels(self, channel_name, channel_number=1):
        """Add a channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
            channel_number: Physical channel number.

        Returns:
            The newly created channel object.
        """
        channels = []
        channels.append(
            super(
                keysight_e5061b,
                self).add_channels(
                channel_name=channel_name,
                channel_number=channel_number))
        return channels

    def add_channel_limit(self, channel_name):
        """Limit channel.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the limit channel.
        """
        # SCPI.CALCulate(Ch).SELected.LIMit.DATA = Data
        # Data = SCPI.CALCulate(Ch).SELected.LIMit.DATA

    def add_channel_TR_mag(self, channel_name, trace_number, channel_number=1):
        """T/R log magnitude measurement channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the TR magnitude channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The created y-data channel configured for TR magnitude.
        """
        self._check_trace_unconfigured(
            trace_number=trace_number,
            channel_number=channel_number)
        channels = []
        channels.append(
            self.add_channel_ydata(
                f'{channel_name}',
                trace_number=trace_number,
                channel_number=channel_number))  # _ypoints
        channels[-1].set_attribute('measurement', 'T/R Log Magnitude')

        stop_f = float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(
                # max for G/P port
                f':SENSe{channel_number}:FREQuency:STOP 30E+6')
        float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(
            f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic')
        # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:DEFine TR')
        self.get_interface().write(
            # {LIN|LOG}
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN')
        # return channels
        return channels[0]

    def add_channel_T_mag(self, channel_name, trace_number, channel_number=1):
        """T log magnitude measurement channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the T magnitude channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The created y-data channel configured for T magnitude.
        """
        self._check_trace_unconfigured(
            trace_number=trace_number,
            channel_number=channel_number)
        channels = []
        channels.append(
            self.add_channel_ydata(
                f'{channel_name}',
                trace_number=trace_number,
                channel_number=channel_number))  # _ypoints
        channels[-1].set_attribute('measurement', 'T Log Magnitude')

        stop_f = float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(
                # max for G/P port
                f':SENSe{channel_number}:FREQuency:STOP 30E+6')
        float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(
            f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic')
        # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:DEFine T')
        self.get_interface().write(
            # {LIN|LOG}
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN')
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))

    def add_channel_R_mag(self, channel_name, trace_number, channel_number=1):
        """R log magnitude measurement channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the R magnitude channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The created y-data channel configured for R magnitude.
        """
        self._check_trace_unconfigured(
            trace_number=trace_number,
            channel_number=channel_number)
        channels = []
        channels.append(
            self.add_channel_ydata(
                f'{channel_name}',
                trace_number=trace_number,
                channel_number=channel_number))  # _ypoints
        channels[-1].set_attribute('measurement', 'R Log Magnitude')

        stop_f = float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(
                # max for G/P port
                f':SENSe{channel_number}:FREQuency:STOP 30E+6')
        float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(
            f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic')
        # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:DEFine R')
        self.get_interface().write(
            # {LIN|LOG}
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN')
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))

    def add_channel_TR_phase(
            self, channel_name, trace_number, channel_number=1):
        """T/R expanded phase measurement channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the TR phase channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The created y-data channel configured for TR phase.
        """
        # "3"	"E5061B"	":CALCulate:SELected:FORMat PHASe"	""
        self._check_trace_unconfigured(
            trace_number=trace_number,
            channel_number=channel_number)
        channels = []
        channels.append(
            self.add_channel_ydata(
                f'{channel_name}',
                trace_number=trace_number,
                channel_number=channel_number))  # _ypoints
        channels[-1].set_attribute('measurement', 'T/R Expanded Phase')
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(
            f':CALCulate{channel_number}:SELected:FORMat UPHase')
        # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:DEFine TR')
        self.get_interface().write(
            # {LIN|LOG}
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN')
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))

    def add_channel_rlevel(self, channel_name, channel_number, trace_number):
        """:DISPlay:WINDow{}:TRACe{}:Y:SCALe:RLEVel value.

        This command sets/gets the value of the reference division line,
        for the selected trace (Tr) of the selected channel (Ch).

        Args:
            channel_name: Name for the reference level channel.
            channel_number: Instrument channel number.
            trace_number: Trace number on the instrument.

        Returns:
            The newly created reference level channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda value,
            channel_number=channel_number,
            trace_number=trace_number: self.get_interface().write(
                f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RLEVel {value}'))
        new_channel._read = lambda: self.get_interface().ask(
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RLEVel?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_rlevel.__doc__)
        return self._add_channel(new_channel)

    # Seems to just track RLEVEL?.... ####
    # def add_channel_rposition(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:RPOSition value
        # This command specifies the position of a reference division line with its number
        # (an integer assigned starting from 0 from the lowest division),
        # for the selected trace (Tr) of selected channel (Ch).'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RPOSition {int(value)}'))
        # new_channel._read = lambda: int(self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RPOSition?'))
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_rposition.__doc__)
        # return self._add_channel(new_channel)

    # Doesn't seem to do anything? ....
    # def add_channel_top(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:TOP value
        # This command sets or gets the maximum scale value for the Log-Y Axis.'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:TOP {value}'))
        # new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:TOP?')
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_top.__doc__)
        # return self._add_channel(new_channel)

    # def add_channel_bottom(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:BOTTom value
        # This command sets or gets the minimum scale value for the Log-Y Axis.'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:BOTTom {value}'))
        # new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:BOTTom?')
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_bottom.__doc__)
        # return self._add_channel(new_channel)

    def add_channel_divisions(self, channel_name, channel_number):
        """:DISPlay:WINDow{}:Y:SCALe:DIVisions value.

        This command sets/gets the number of divisions in all the graphs,
        for the selected channel (Ch).

        Args:
            channel_name: Name for the divisions channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created divisions channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda value,
            channel_number=channel_number: self.get_interface().write(
                f':DISPlay:WINDow{channel_number}:Y:SCALe:DIVisions {value}'))
        new_channel._read = lambda: self.get_interface().ask(
            f':DISPlay:WINDow{channel_number}:Y:SCALe:DIVisions?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_divisions.__doc__)
        return self._add_channel(new_channel)

    def add_channel_pdiv(self, channel_name, channel_number, trace_number):
        """:DISPlay:WINDow{}:TRACe{}:Y:SCALe:PDIVision value.

        For the selected trace (Tr) of selected channel (Ch), when the data
        format is not the Smith chart format or the polar format, sets the
        scale per division. When the data format is the Smith chart format
        or the polar format, sets the full scale value (the value of the
        outermost circumference).

        Args:
            channel_name: Name for the per-division channel.
            channel_number: Instrument channel number.
            trace_number: Trace number on the instrument.

        Returns:
            The newly created per-division channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda value,
            channel_number=channel_number,
            trace_number=trace_number: self.get_interface().write(
                f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:PDIVision {value}'))
        new_channel._read = lambda: self.get_interface().ask(
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:PDIVision?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_pdiv.__doc__)
        return self._add_channel(new_channel)

    def add_channel_sparam(
            self, channel_name, trace_number, x, y, channel_number=1):
        """S-parameter log magnitude measurement channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the S-parameter channel.
            trace_number: Trace number on the instrument.
            x: S-parameter source port number.
            y: S-parameter destination port number.
            channel_number: Instrument channel number.

        Returns:
            The created y-data channel configured for S-parameter measurement.
        """
        assert x in range(1, 3)  # What about 4-port machines?
        assert y in range(1, 3)  # What about 4-port machines?
        self._check_trace_unconfigured(
            trace_number=trace_number,
            channel_number=channel_number)
        channels = []
        channels.append(
            self.add_channel_ydata(
                f'{channel_name}',
                trace_number=trace_number,
                channel_number=channel_number))  # _ypoints
        channels[-1].set_attribute('measurement', f'S{x}{y} Log Magnitude')
        stop_f = float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 3e9:
            self.get_interface().write(
                f':SENSe{channel_number}:FREQuency:STOP 3E+9')
        float(
            self.get_interface().ask(
                f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(
            f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic')
        # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:DEFine S{x}{y}')
        self.get_interface().write(
            # {LIN|LOG}
            f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN')
        # return channels
        return channels[0]

    # def add_channel_s_absolute(self, channel_name, trace_number, x, y,
    # channel_number=1):

    def add_channels_calibration(self, channel_name):
        """Calibration control channels.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the calibration channels.
        """
        # G/P vs sparam
        # fixture
        # correction status
        # cal type
        # coefficient array
        # port extension
        # edly time
        # ...

        # To turn ON/OFF error correction, use the following command:
        # :SENS{1-4}:CORR:STAT
        # E5061B
        # 600
        # Also, once you have calculated the calibration coefficient using the :SENS{1-
        # 4}:CORR:COLL:SAVE command, error correction is automatically turned on.
        # When you turn on the error correction, you can check the calibration type
        # actually applied to each trace. To check the calibration type, use the
        # following command:
        # :SENS{1-4}:CORR:TYPE{1-4}?
        # You must follow the steps below to write the calibration coefficient.
        # 1. Declare the calibration type to write.
        # Execute :SENS{1-4}:CORR:COEF:METH:xxxx command
        # 2. Write any calibration coefficient.
        # Execute :SENS{1-4}:CORR:COEF command as needed for the written
        # calibration coefficients
        # 3. Validate the calibration coefficients.
        # Execute :SENS{1-4}:CORR:COEF:SAVE command
        # Do not execute any other command while writing the
        # calibration coefficients. This may cause the system to function
        # incorrectly.
        # To calculate the calibration coefficients using partial overwrite, use the
        # following command:
        # :SENS{1-4}:CORR:COLL:PART:SAVE
        # Before you can calculate the calibration coefficients
        # with the partial overwrite, you must select the appropriate
        # calibration type in the same way used for normal calibration. If
        # calculation of the calibration coefficients is attempted without
        # selecting the calibration type, an error message (28: Invalid
        # Calibration Method) is displayed.


class keysight_e5061b_impedance(keysight_e5061b_base):
    """Keysight_e5061b_impedance (keysight_e5061b_base subclass)."""
    # def __init__(self, interface_visa):
    # super(keysight_e5061b, self).__init__(interface_visa)

    # :SENSe{[1]-4}:Z:METHod <string>
    # :SENSe{[1]-4}:Z:METHod?
    # Select one of the following options:
    # P1Reflection:S-Parameter Port 1 reflection measurement
    # (for simple impedance measurement)
    # P2Reflection:S-Parameter Port 2 reflection measurement
    # (for simple impedance measurement)
    # TSERies:S-Parameter series-through measurement (for
    # simple impedance measurement)
    # TSHunt:S-Parameter shunt-through measurement (for
    # PDN component characterization)
    # GSERies:Gain-Phase series-through measurement (for
    # simple impedance measurement)
    # GSHunt:Gain-Phase shunt-through measurement (for
    # PDN component characterization)

    # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine <string>
    # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine?
    # Z|Y|Cp|Cs|Lp|Ls|Rp|Rs|D|Q

    # :SENSe{[1]-4}:Z:COMPensation:COEFficient[:DATA]
    # {OPEN|SHORt|LOAD}, <numeric 1>, ... ,<numeric NOP×2>
    # :SENSe{[1]-4}:Z:COMPensation:COEFficient[:DATA]?
    # {OPEN|SHORt|LOAD}
    # Query Response
    # <numeric 1>, ... ,<numeric NOP×2><newline><^END>
    # Description
    # <numeric n×2-
    # 1>
    # Real part of data (complex number) at the n-th
    # measurement point.
    # <numeric
    # n×2>
    # Imaginary part of data (complex number) at the n-th
    # measurement point.
    # :SENSe{[1]-4}:Z:COMPensation:COEFficient:POINts? {OPEN|SHORt|LOAD}
    # Query Response
    # <numeric><newline><^END>
    # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA]
    # {OPEN|SHORt|LOAD|LOAD2},<numeric 1>, ... ,<numeric NOP×2>
    # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA]?
    # Query Response
    # <numeric 1>, ... ,<numeric NOP×2><newline><^END>
    # Description
    # <numeric n×2-
    # 1>
    # Real part of data (complex number) at the n-th
    # measurement point.
    # <numeric
    # n×2>
    # Imaginary part of data (complex number) at the n-th
    # measurement point.
    # Because the calibration coefficient array is expressed by a complex
    # number, the real part and the imaginary part of one measurement point
    # are returned and obtained as a value. Here, NOP is the number of
    # measurement points and n is an integer between 1 and NOP.
    # :SENSe{[1]-4}:Z:METHod <string>
    # :SENSe{[1]-4}:Z:METHod?
    # Query Response
    # <string><newline><^END>
    # :SENSe{[1]-4}:DC:PARameter {DCV|DCI|R|T}
    # :SENSe{[1]-4}:DC:PARameter?
    # Query Response
    # {DCV|DCI|R|T} <newline><^END>

    def add_channels(self, channel_name, channel_number=1):
        """Add a channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
            channel_number: Physical channel number.

        Returns:
            The newly created channel object.
        """
        channels = []
        channels.append(
            super(
                keysight_e5061b_impedance,
                self).add_channels(
                channel_name=channel_name,
                channel_number=channel_number))
        # TODO more channels
        return channels

    def add_channel_zmethod(self, channel_name, channel_number=1):
        """Impedance measurement method control channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the Z method channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created Z method channel.
        """
        # :SENSe{[1]-4}:Z:METHod <string>
        # :SENSe{[1]-4}:Z:METHod?
        # Select one of the following options:
        # P1Reflection:S-Parameter Port 1 reflection measurement
        # (for simple impedance measurement)
        # P2Reflection:S-Parameter Port 2 reflection measurement
        # (for simple impedance measurement)
        # TSERies:S-Parameter series-through measurement (for
        # simple impedance measurement)
        # TSHunt:S-Parameter shunt-through measurement (for
        # PDN component characterization)
        # GSERies:Gain-Phase series-through measurement (for
        # simple impedance measurement)
        # GSHunt:Gain-Phase shunt-through measurement (for
        # PDN component characterization)
        new_channel = channel(
            channel_name,
            write_function=lambda zmeth,
            channel_number=channel_number: self.get_interface().write(
                f':SENSe{channel_number}:Z:METHod {zmeth}'))
        new_channel._set_value(
            self.get_interface().ask(
                f':SENSe{channel_number}:Z:METHod?'))
        new_channel.add_preset(
            'P1Reflection',
            'S-Parameter Port 1 reflection measurement (for simple impedance measurement)')
        new_channel.add_preset(
            'P2Reflection',
            'S-Parameter Port 2 reflection measurement (for simple impedance measurement)')
        new_channel.add_preset(
            'TSERies',
            'S-Parameter series-through measurement (for simple impedance measurement)')
        new_channel.add_preset(
            'TSHunt',
            'S-Parameter shunt-through measurement (for PDN component characterization)')
        new_channel.add_preset(
            'GSERies',
            'Gain-Phase series-through measurement (for simple impedance measurement)')
        new_channel.add_preset(
            'GSHunt',
            'Gain-Phase shunt-through measurement (for PDN component characterization)')
        new_channel.set_attribute('channel_type', 'z_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zmethod.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zparameter(
            self, channel_name, trace_number=1, channel_number=1):
        """Impedance parameter selection channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELect`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the Z parameter channel.
            trace_number: Trace number on the instrument.
            channel_number: Instrument channel number.

        Returns:
            The newly created Z parameter channel.
        """
        # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine <string>
        # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine?
        # Z|Y|Cp|Cs|Lp|Ls|Rp|Rs|D|Q
        new_channel = channel(
            channel_name,
            write_function=lambda zparam,
            trace_number=trace_number,
            channel_number=channel_number: self.get_interface().write(
                f':CALCulate{channel_number}:PARameter{trace_number}:SELect; :CALCulate{channel_number}:SELected:ZPARameter:DEFine {zparam}'))
        self.get_interface().write(
            f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        new_channel._set_value(self.get_interface().ask(
            f':CALCulate{channel_number}:SELected:ZPARameter:DEFine?'))
        new_channel.add_preset('Z', 'Impedance Magnitude')
        new_channel.add_preset('Y', 'Admittance Magnitude')
        new_channel.add_preset('Cp', 'Parallel Capacitance')
        new_channel.add_preset('Cs', 'Series Capacitance')
        new_channel.add_preset('Lp', 'Parallel Inductance')
        new_channel.add_preset('Ls', 'Series Inductance')
        new_channel.add_preset('Rp', 'Parallel Resistance')
        new_channel.add_preset('Rs', 'Series Resistance')
        new_channel.add_preset('D', 'Dissipation Factor')
        new_channel.add_preset('Q', 'Quality Factor')
        # R Resistance
        # X Reactance
        # G Conductance
        # B Susceptance
        # page 342-3
        new_channel.set_attribute('channel_type', 'z_control')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zparameter.__doc__)
        return self._add_channel(new_channel)

    def _parse_complex(self, interleaved_array):
        return [complex(interleaved_array[i], interleaved_array[i + 1])
                for i in range(0, len(interleaved_array), 2)]

    def add_channel_zcorrection_open(self, channel_name, channel_number=1):
        """Open load complex correction vector.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the open correction channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created open correction channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._parse_complex(
                [
                    float(z) for z in self.get_interface().ask(
                        f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? OPEN').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zcorrection_open.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_short(self, channel_name, channel_number=1):
        """Shorted load complex correction vector.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the short correction channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created short correction channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._parse_complex(
                [
                    float(z) for z in self.get_interface().ask(
                        f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? SHORt').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zcorrection_short.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_load(self, channel_name, channel_number=1):
        """50 Ohm load complex correction vector.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the load correction channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created load correction channel.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._parse_complex(
                [
                    float(z) for z in self.get_interface().ask(
                        f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? LOAD').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zcorrection_load.__doc__)
        return self._add_channel(new_channel)

    def add_channels_impedance_setup(self, channel_name, channel_number=1):
        """Shortcut to add impedance measurement control channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the impedance setup channels.
            channel_number: Instrument channel number.

        Returns:
            List of created impedance setup channel objects.
        """
        channels = []
        channels.append(
            self.add_channel_zmethod(
                f'{channel_name}_method',
                channel_number=channel_number))
        channels.append(
            self.add_channel_zparameter(
                f'{channel_name}_parameter',
                trace_number=1,
                channel_number=channel_number))
        channels.extend(
            self.add_channels_zcorrection(
                f'{channel_name}_zcorr',
                channel_number=channel_number))
        return channels

    def add_channels_zcorrection(self, channel_name, channel_number=1):
        """Z correction channels for open, short, and load.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the Z correction channels.
            channel_number: Instrument channel number.

        Returns:
            List of created Z correction channel objects.
        """
        channels = []
        channels.append(
            self.add_channel_zcorrection_open(
                f'{channel_name}_open',
                channel_number=channel_number))
        channels.append(
            self.add_channel_zcorrection_short(
                f'{channel_name}_short',
                channel_number=channel_number))
        channels.append(
            self.add_channel_zcorrection_load(
                f'{channel_name}_load',
                channel_number=channel_number))
        # todo load two low loss C?
        return channels

    def add_channel_zcorrection_collect(self, channel_name, channel_number=1):
        """Z correction collection channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the Z correction collect channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created Z correction collect channel.
        """
        def col_and_wait(cal_type, channel_number):
            """Perform col and wait operation.
            Sends the ``:Z:CORRection:COLLect:ACQuire`` SCPI command to the
            instrument.
            Sends the ``:SENSe`` SCPI command to the instrument.

            Sends the corresponding SCPI command string to the instrument over the bus.

            Args:
                cal_type: Cal type to use.
                channel_number: Physical channel number.
            """
            old_timeout = self.get_interface().timeout
            self.get_interface().write(
                f':SENSe{channel_number}:Z:CORRection:COLLect:ACQuire {cal_type}')
            self.get_interface().timeout = 1000
            self.get_interface().ask('*OPC?')
            self.get_interface().timeout = old_timeout
            # This step seems to be necessary in order to read back the
            # calibration components.
            self.get_interface().write(
                f':SENSe{channel_number}:Z:CORRection:COLLect:SAVE')
        new_channel = channel(
            channel_name,
            write_function=lambda cal_type,
            channel_number=channel_number: col_and_wait(
                cal_type,
                channel_number))
        new_channel.add_preset('OPEN')
        new_channel.add_preset('SHORt')
        new_channel.add_preset('LOAD')
        new_channel.add_preset('LOAD2')
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zcorrection_collect.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_write(self, channel_name, channel_number=1):
        """Single channel expects dictionary of OPEN/SHORt/LOAD complex correction vectors.

        Intended usage to 3-d cal across applied bias, etc.

        Args:
            channel_name: Name for the Z correction write channel.
            channel_number: Instrument channel number.

        Returns:
            The newly created Z correction write channel.
        """
        def _write_cal_data(data_dict, channel_number):
            for cal_type in ('OPEN', 'SHORt', 'LOAD'):  # LOAD2
                vector_str = ','.join(
                    [f'{c.real},{c.imag}' for c in data_dict[cal_type]])
                # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA] {OPEN|SHORt|LOAD|LOAD2},<numeric 1>, ... ,<numeric NOP×2>
                self.get_interface().write(
                    f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA {cal_type},{vector_str}')
            self.get_interface().write(
                f':SENSe{channel_number}:Z:CORRection:COLLect:SAVE')
        new_channel = channel(
            channel_name,
            write_function=lambda cal_data,
            channel_number=channel_number: _write_cal_data(
                cal_data,
                channel_number))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_zcorrection_write.__doc__)
        return self._add_channel(new_channel)

    def add_channels_impedance_equiv_A(self, channel_name, channel_number=1):
        """Parallel RLC. Model A - Generally suited to analyze inductors with high core loss.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the equivalent circuit channels.
            channel_number: Instrument channel number.

        Returns:
            List of created equivalent circuit channel objects.
        """
        return self._add_channels_impedance_equiv(
            channel_name=channel_name, channel_number=channel_number, circuit_topology='A')

    def add_channels_impedance_equiv_B(self, channel_name, channel_number=1):
        """C parallel R+L. Model B - Generally suited to analyze general inductors and resistors.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the equivalent circuit channels.
            channel_number: Instrument channel number.

        Returns:
            List of created equivalent circuit channel objects.
        """
        return self._add_channels_impedance_equiv(
            channel_name=channel_name, channel_number=channel_number, circuit_topology='B')

    def add_channels_impedance_equiv_C(self, channel_name, channel_number=1):
        """L series C//R. Model C - Generally suited to analyze resistors with high resistance.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the equivalent circuit channels.
            channel_number: Instrument channel number.

        Returns:
            List of created equivalent circuit channel objects.
        """
        return self._add_channels_impedance_equiv(
            channel_name=channel_name, channel_number=channel_number, circuit_topology='C')

    def add_channels_impedance_equiv_D(self, channel_name, channel_number=1):
        """Series RLC. Model D - Generally suited to analyze capacitors.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the equivalent circuit channels.
            channel_number: Instrument channel number.

        Returns:
            List of created equivalent circuit channel objects.
        """
        return self._add_channels_impedance_equiv(
            channel_name=channel_name, channel_number=channel_number, circuit_topology='D')

    def add_channels_impedance_equiv_E(self, channel_name, channel_number=1):
        """C0 parallel Series RLC. Model E - Generally suited to analyze resonators and oscillators.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Base name for the equivalent circuit channels.
            channel_number: Instrument channel number.

        Returns:
            List of created equivalent circuit channel objects.
        """
        channels = self._add_channels_impedance_equiv(
            channel_name=channel_name,
            channel_number=channel_number,
            circuit_topology='E')
        channels.append(
            self._add_channel_impedance_equiv(
                f'{channel_name}_C0',
                channel_number=channel_number,
                circuit_topology='E',
                component_desig='C0'))
        return channels

    def _add_channels_impedance_equiv(
            self, channel_name, channel_number, circuit_topology):
        self.get_interface().write(
            f':CALCulate{channel_number}:EPARameters:CIRCuit:TYPE {circuit_topology}')
        self.get_interface().write(
            f':CALCulate{channel_number}:EPARameters:DISPlay:STATe ON')
        self.get_interface().write(
            f':CALCulate{channel_number}:EPARameters:SIMulate:AUTO ON')
        # :CALCulate{[1]-4}:EPARameters:SIMulate[:IMMediate]
        channels = []
        channels.append(
            self._add_channel_impedance_equiv(
                f'{channel_name}_R1',
                channel_number=channel_number,
                circuit_topology=circuit_topology,
                component_desig='R1'))
        channels.append(
            self._add_channel_impedance_equiv(
                f'{channel_name}_C1',
                channel_number=channel_number,
                circuit_topology=circuit_topology,
                component_desig='C1'))
        channels.append(
            self._add_channel_impedance_equiv(
                f'{channel_name}_L1',
                channel_number=channel_number,
                circuit_topology=circuit_topology,
                component_desig='L1'))
        return channels

    def _add_channel_impedance_equiv(
            self, channel_name, channel_number, circuit_topology, component_desig):
        """Equivalent circuit component readback channel.
        Internal helper that sends the ``:EPARameters:CIRCuit:`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Name for the equivalent circuit channel.
            channel_number: Instrument channel number.
            circuit_topology: Circuit topology model letter (A-E).
            component_desig: Component designator (R1, C1, L1, C0).

        Returns:
            The newly created equivalent circuit channel.
        """
        # :CALCulate{[1]-4}:EPARameters:CIRCuit:B:C1?
        calc_cmd = f':CALCulate{channel_number}:EPARameters:EXECute; '
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number,
            circuit_topology=circuit_topology,
            component_desig=component_desig: float(
                self.get_interface().ask(
                    f'{calc_cmd}:CALCulate{channel_number}:EPARameters:CIRCuit:{circuit_topology}:{component_desig}?')))
        new_channel.set_attribute('channel_type', 'z_equiv')
        new_channel.set_attribute('topology', 'circuit_topology')
        new_channel.set_description(
            self.get_name() + ': ' + self._add_channel_impedance_equiv.__doc__)
        return self._add_channel(new_channel)

# :SENSe1:Z:COMPensation:COEFficient:DATA? OPEN
# :SENSe1:Z:COMPensation:COEFficient:DATA? SHORt
# :SENSe1:Z:COMPensation:COEFficient:DATA? LOAD

# :SENSe1:Z:COMPensation:COEFficient:POINts? OPEN
# :SENSe1:Z:COMPensation:COEFficient:POINts? SHORt
# :SENSe1:Z:COMPensation:COEFficient:POINts? LOAD

# :SENSe1:Z:CORRection:COEFficient:DATA?
# :SENSe1:Z:CORRection:COEFficient:DATA? {OPEN|SHORt|LOAD|LOAD2}
# :SENSe1:Z:CORRection:COEFficient:DATA? LOAD
# :SENSe1:Z:CORRection:COEFficient:DATA?
# :SENSe1:CORRection:COEFficient:DATA?
# :SENSe1:CORRection:COEFficient:GPData?

    # TODO!
    # log-y control
    # attenuator control
    # GP/Sparam switch
    # GP impedance/atten switch
    # transmit power control
    # S param (not Z) calibration vectors

    # swept bias controls
    # dc bias controls

    # Marker controls page 1077

    # update sync to sweep rate

    # sore and load bias-dependent cal vectors to synthesize 2d sweep

    # :SENSe{[1]-4}:Z:CORRection:COLLect[:ACQuire]
    # {OPEN|SHORt|LOAD|LOAD2}

    # :SENSe{[1]-4}:FREQuency:DATA?
# Query response
# {numeric 1},… ,{numeric NOP}<newline><^END>
# :SENSe{[1]-4}:FREQuency[:CW|FIXed] <numeric>
# :SENSe{[1]-4}:FREQuency[:CW|FIXed]?
# Query response
# {numeric}<newline><^END>

# :SENSe{[1]-4}:DC:MEASure:DATA?
# Query Response
# {numeric} <newline><^END>
# :SENSe{[1]-4}:DC:MEASure:ENABle {ON|OFF|1|0}
# :SENSe{[1]-4}:DC:MEASure:ENABle?


# read manual page 627

# page 906
#  SCPI.CALCulate(Ch).SELected.DATA.FDATa
# :CALCulate{[1]-4}[:SELected]:DATA:FDATa <numeric1>,… ,<numeric
# NOP×2>
# :CALCulate{[1]-4}[:SELected]:DATA:FDATa?

#  SCPI.CALCulate(Ch).SELected.DATA.FMEMory
# :CALCulate{[1]-4}[:SELected]:DATA:FMEMory <numeric 1>,… ,<numeric
# NOP×2>
# :CALCulate{[1]-4}[:SELected]:DATA:FMEMory?
# Query response
# {numeric 1},… ,{numeric NOP×2}<newline><^END>

#  SCPI.CALCulate(Ch).SELected.DATA.SDATa
# :CALCulate{[1]-4}[:SELected]:DATA:SDATa <numeric 1>,… ,<numeric
# NOP×2>
# :CALCulate{[1]-4}[:SELected]:DATA:SDATa?

#  SCPI.CALCulate(Ch).SELected.DATA.SMEMory
# :CALCulate{[1]-4}[:SELected]:DATA:SMEMory <numeric 1>,… ,<numeric
# NOP×2>
# :CALCulate{[1]-4}[:SELected]:DATA:SMEMory?

# :CALCulate{[1]-4}[:SELected]:DATA:XAXis?
