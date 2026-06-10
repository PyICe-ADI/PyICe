"""Smu instrument driver.

>>> from PyICe.lab_instruments.smu import smu

"""
# pylint: disable=E1101; this module defines abstract base classes (smu, scpi_smu) whose members
# (_configured_channels, _vforce, _iforce, _vsense, _isense, _vcompl, _vcomplq, _icompl, _icomplq,
# _remote_sense, _remote_senseq, _high_capacitance, _high_capacitanceq, _terminal_select,
# _terminal_selectq, _parse_float) are implemented/initialized by concrete subclasses
# (keithley_2400, keithley_smu, etc.) that combine these bases via multiple inheritance
from ..lab_core import *  # noqa: F403

# todo measure autorange
# todo range control channels???


class smu(instrument):
    """Smu (instrument subclass)."""
    def _fix_exclusive(self, ch, value):
        """Fix write cache of exclusive channel pair sibling.

        Internal implementation detail; see the public API for usage.

        Args:
            ch: Channel number or channel object.
            value: Value to set.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if ch.get_attribute('channel_type') == 'vforce':
            pair_ch = self._configured_channels[ch.get_attribute(
                'channel_number')]['i_force']
            if pair_ch is not None:
                pair_ch._set_value(None)
        elif ch.get_attribute('channel_type') == 'iforce':
            pair_ch = self._configured_channels[ch.get_attribute(
                'channel_number')]['v_force']
            if pair_ch is not None:
                pair_ch._set_value(None)
        else:
            raise Exception('How did I get here?')

    def _init_channel(self, channel_number):
        # todo remote sense, high c?
        if channel_number in self._configured_channels:
            assert 'v_force' in self._configured_channels[channel_number]
            assert 'i_force' in self._configured_channels[channel_number]
            assert 'v_sense' in self._configured_channels[channel_number]
            assert 'i_sense' in self._configured_channels[channel_number]
            assert 'v_compl' in self._configured_channels[channel_number]
            assert 'i_compl' in self._configured_channels[channel_number]
        else:
            self._configured_channels[channel_number] = {'v_force': None,
                                                         'i_force': None,
                                                         'v_sense': None,
                                                         'i_sense': None,
                                                         'v_compl': None,
                                                         'i_compl': None,
                                                         }

    def add_channels(self, channel_name, channel_number=1):
        """Shortcut.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
            channel_number: Physical channel number.

        Returns:
            The newly created channel object.
        """
        # todo remote sense, high c?
        return (self.add_channel_voltage_force(f'{channel_name}_vforce', channel_number),
                self.add_channel_current_force(
            f'{channel_name}_iforce', channel_number),
            self.add_channel_voltage_sense(
            f'{channel_name}_vsense', channel_number),
            self.add_channel_current_sense(
            f'{channel_name}_isense', channel_number),
            self.add_channel_voltage_compliance(
            f'{channel_name}_vcompl', channel_number),
            self.add_channel_current_compliance(
            f'{channel_name}_icompl', channel_number),
        )

    def add_channel_voltage_force(self, channel_name, channel_number=1):
        """Voltage force. Mutually exclusive at any moment with current force.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda v,
            channel_number=channel_number: self._vforce(
                channel_number,
                v))
        self._configured_channels[channel_number]['v_force'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_voltage_force.__doc__)
        self._add_channel_voltage_force(new_channel)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        return self._add_channel(new_channel)

    def add_channel_current_force(self, channel_name, channel_number=1):
        """Current force. Mutually exclusive at any moment with voltage force.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda i,
            channel_number=channel_number: self._iforce(
                channel_number,
                i))
        self._configured_channels[channel_number]['i_force'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'iforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_current_force.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_current_force(new_channel)
        return self._add_channel(new_channel)

    def add_channel_voltage_sense(self, channel_name, channel_number=1):
        """Voltage readback.
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
        # range, nplc?
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._vsense(channel_number))
        self._configured_channels[channel_number]['v_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vsense')
        # new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_voltage_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_voltage_sense(new_channel)
        return self._add_channel(new_channel)

    def add_channel_current_sense(self, channel_name, channel_number=1):
        """Current readback.
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
        # range, nplc?
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            read_function=lambda channel_number=channel_number: self._isense(channel_number))
        self._configured_channels[channel_number]['i_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'isense')
        # new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_current_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_current_sense(new_channel)
        return self._add_channel(new_channel)

    def add_channel_voltage_compliance(self, channel_name, channel_number=1):
        """Max voltage in current forcing modes.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda v,
            channel_number=channel_number: self._vcompl(
                channel_number,
                v))
        new_channel._read = lambda channel_number=channel_number: self._vcomplq(
            channel_number)
        self._configured_channels[channel_number]['v_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vcompl')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_voltage_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        self._add_channel_voltage_compliance(new_channel)
        return self._add_channel(new_channel)

    def add_channel_current_compliance(self, channel_name, channel_number=1):
        """Max current in voltage forcing modes.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda i,
            channel_number=channel_number: self._icompl(
                channel_number,
                i))
        new_channel._read = lambda channel_number=channel_number: self._icomplq(
            channel_number)
        self._configured_channels[channel_number]['i_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'icompl')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_current_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        self._add_channel_current_compliance(new_channel)
        return self._add_channel(new_channel)

    def add_channel_remote_sense(self, channel_name, channel_number=1):
        """Remote (4-wire) sense enable control.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda i,
            channel_number=channel_number: self._remote_sense(
                channel_number,
                i))
        new_channel._read = lambda channel_number=channel_number: self._remote_senseq(
            channel_number)
        self._configured_channels[channel_number]['remote_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'remote_sense')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_remote_sense.__doc__)
        new_channel.add_preset('True')
        new_channel.add_preset('False')
        self._add_channel_remote_sense(new_channel)
        return self._add_channel(new_channel)
        # todo initial value?

    def add_channel_high_capacitance(self, channel_name, channel_number):
        """Stabilize forcing source for higher DUT capacitance, typically tens of uF.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda i,
            channel_number=channel_number: self._high_capacitance(
                channel_number,
                i))
        new_channel._read = lambda channel_number=channel_number: self._high_capacitanceq(
            channel_number)
        self._configured_channels[channel_number]['high_capacitance'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'high_capacitance')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_high_capacitance.__doc__)
        new_channel.add_preset('True')
        new_channel.add_preset('False')
        self._add_channel_high_capacitance(new_channel)
        return self._add_channel(new_channel)
        # todo initial value?

    def add_channel_terminal_select(self, channel_name, channel_number):
        """Select between front and rear panel terminals.
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
        self._init_channel(channel_number)
        new_channel = channel(
            channel_name,
            write_function=lambda i,
            channel_number=channel_number: self._terminal_select(
                channel_number,
                i))
        new_channel._read = lambda channel_number=channel_number: self._terminal_selectq(
            channel_number)
        self._configured_channels[channel_number]['terminal_select'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'terminal_select')
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_terminal_select.__doc__)
        new_channel.add_preset('Front')
        new_channel.add_preset('Rear')
        self._add_channel_terminal_select(new_channel)
        return self._add_channel(new_channel)

    def _add_channel_voltage_force(self, channel):
        """Voltage force. Mutually exclusive at any moment with current force.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_current_force(self, channel):
        """Current force. Mutually exclusive at any moment with voltage force.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_voltage_sense(self, channel):
        """Voltage readback.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_current_sense(self, channel):
        """Current readback.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_voltage_compliance(self, channel):
        """Max voltage in current forcing modes.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_current_compliance(self, channel):
        """Max current in voltage forcing modes.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_remote_sense(self, channel):
        """Remote (4-wire) sense enable control.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_high_capacitance(self, channel):
        """Stabilize forcing source for higher DUT capacitance, typically tens of uF.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
    def _add_channel_terminal_select(self, channel):
        """Select front vs rear panel connection mux.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
class keithley_smu(smu):
    """Keithley_smu."""
    def _parse_float(self, val):
        f = float(val)
        if f == 9.91E37:  # Keithley NaN
            f = float('nan')
        return f


class scpi_smu(scpi_instrument, smu):
    """TODO: Add docstring."""
    # todo abstract methods?

    def _output_off(self, channel_number):
        self.get_interface().write(
            f':SOURce{channel_number}:CURRent:LEVel:IMMediate:AMPLitude 0')
        # dangerous, because it turns back on from reading!
        self.get_interface().write(f':SOURce{channel_number}:CLEar:IMMediate')

    def _vforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(
                f':SOURce{channel_number}:VOLTage:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(
                f':SOURce{channel_number}:FUNCtion:MODE VOLTage')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['i_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)

    def _iforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(
                f':SOURce{channel_number}:CURRent:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(
                f':SOURce{channel_number}:FUNCtion:MODE CURRent')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['v_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)

    def _vsense(self, channel_number):
        # what about channel number parsing?!?!?!?
        # :FORMat:ELEMents [SENSe[1]] <item list> Specify data elements for data string
        # Parameters <item list> = VOLTageIncludes voltage reading
        # CURRentIncludes current reading
        # RESistance Includes resistance reading
        # TIMEIncludes timestamp
        # STATusIncludes status information
        # todo better message parsing
        # todo explicitly set format of response included elements
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(
            ':MEASure:VOLTage:DC?').split(',')
        return self._parse_float(voltage)

    def _isense(self, channel_number):
        # what about channel number parsing?!?!?!?
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(
            ':MEASure:CURRent:DC?').split(',')
        return self._parse_float(current)

    def _vcompl(self, channel_number, value):
        self.get_interface().write(
            f':SENSe{channel_number}:VOLTage:DC:PROTection:LEVel {value}')

    def _vcomplq(self, channel_number):
        return self.get_interface().ask(
            f':SENSe{channel_number}:VOLTage:DC:PROTection:LEVel?')

    def _icompl(self, channel_number, value):
        self.get_interface().write(
            f':SENSe{channel_number}:CURRent:DC:PROTection:LEVel {value}')

    def _icomplq(self, channel_number):
        return self.get_interface().ask(
            f':SENSe{channel_number}:CURRent:DC:PROTection:LEVel?')

    def _remote_sense(self, channel_number, value):
        """Ignores channel number!!!!!!!!!!!!!!!!!!!
        Internal helper that sends the ``:SYSTem:RSENse`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_number: Physical channel number.
            value: Value to set.
        """
        # print(f'{value}, {type(value)}')
        self.get_interface().write(
            f':SYSTem:RSENse {"OFF" if not value or value == "False" else "ON"}')

    def _remote_senseq(self, channel_number):
        """Ignores channel number!!!!!!!!!!!!!!!!!!!
        Internal helper that sends the ``:SYSTem:RSENse`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_number: Physical channel number.

        Returns:
            The remote senseq result.
        """
        # print(f'{value}, {type(value)}')
        return self.get_interface().ask(':SYSTem:RSENse?')

    def _high_capacitance(self, channel_number, value):
        raise Exception('Unimplemented. Contact PyICe developers.')

    def _terminal_select(self, channel_number, value):
        """Select between front and rear panel terminals.
        Internal helper that sends the ``:ROUTe:TERMinals`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_number: Physical channel number.
            value: Value to set.
        """
        self.get_interface().write(f':ROUTe:TERMinals {value}')

    def _terminal_selectq(self, channel_number):
        """Query front vs rear panel terminals.
        Internal helper that sends the ``:ROUTe:TERMinals`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_number: Physical channel number.

        Returns:
            The terminal selectq result.
        """
        resp_subst = {"FRON": "Front",
                      "REAR": "Rear",
                      }
        return resp_subst[self.get_interface().ask(':ROUTe:TERMinals?')]


class keithley_2400(scpi_smu, keithley_smu):
    """TODO: Add docstring."""
    # todo NPLC config?
    # todo trigger source, pulse, sweep? Other instrument driver?
    # todo atexit cleanup?
    # todo V/I init to zero?, source off?

    def __init__(self, interface_visa):
        """Interface_visa.
        Calls the parent class constructor and initializes instance-specific
        attributes for keithley_2400.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'Keithley 2400'
        super(scpi_smu, self).__init__(f"Keithley 2400 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._configured_channels = {}
        self._output_off(channel_number=1)
        self.get_interface().write(':SOURce1:VOLTage:PROTection:LEVel 20')  # todo Dave fix
        # atexit.register(self._output_off, channel_number=1) #TODO debug

    def _add_channel_voltage_force(self, channel):
        """Voltage force. Mutually exclusive at any moment with current force.
        Internal helper that sends the ``:SOURce`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel: Channel object.
        """
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:VOLTage:RANGe:AUTO ON')
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:VOLTage:MODE FIXed')
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:CLEar:AUTO OFF')
        channel.set_min_write_limit(-200)
        channel.set_max_write_limit(200)
        # self.get_interface().write(f':SOURce{channel.get_attribute("channel_number")}:FUNCtion:SHAPe
        # DC') #2430 only

    def _add_channel_current_force(self, channel):
        """Current force. Mutually exclusive at any moment with voltage force.
        Internal helper that sends the ``:SOURce`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel: Channel object.
        """
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:CURRent:RANGe:AUTO ON')
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:CURRent:MODE FIXed')
        self.get_interface().write(
            f':SOURce{channel.get_attribute("channel_number")}:CLEar:AUTO OFF')
        channel.set_min_write_limit(-1)
        channel.set_max_write_limit(1)
        # self.get_interface().write(f':SOURce{channel.get_attribute("channel_number")}:FUNCtion:SHAPe
        # DC') #2430 only

    def _add_channel_voltage_sense(self, channel):
        """Voltage readback.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
        # [:SENSe[1]]:VOLTage[:DC]:NPLCycles <n> Set speed (PLC)

    def _add_channel_current_sense(self, channel):
        """Current readback.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
        # range, nplc?
        # [:SENSe[1]]:CURRent[:DC]:NPLCycles <n> Set speed (PLC)

    def _add_channel_voltage_compliance(self, channel):
        """Max voltage in current forcing modes.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
        # there are two thresholds. Source compliance (OVP) and Sense compliance (true compliance). Ignoring the former for now....
        # these are very coarse. ie
        # <n> = -210 to 210 Specify V-Source limit
        # 20 Set limit to 20V
        # 40 Set limit to 40V
        # 60 Set limit to 60V
        # 18-80 SCPI Command Reference 2400 Series SourceMeter® User’s Manual
        # 80 Set limit to 80V
        # 100 Set limit to 100V
        # 120 Set limit to 120V
        # 160 Set limit to 160V
        # 161 to 210 Set limit to 210V (NONE)
        # DEFault Set limit to 210V (NONE)
        # MINimum Set limit to 20V
        # MAXimum Set limit to 210V (NONE)'''
        # :SOURce[1]:VOLTage:PROTection[:LEVel]
        # TODO if this is useful

    def _add_channel_current_compliance(self, channel):
        """Max current in voltage forcing modes.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
class keithley_2400_front_rear(keithley_2400):
    """Make single 2400 instrument behave like muxed instrument via front and rear panel selection."""
    # WIP


class keithley_2600(keithley_smu):
    """Https://download.tek.com/manual/2600BS-901-01_C_Aug_2016_2.pdf."""

    def __init__(self, interface_visa):
        """Initialize keithley_2600.
        Calls the parent class constructor and initializes instance-specific
        attributes for keithley_2600.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'Keithley 2600'
        super(keithley_2600, self).__init__(
            f"{self._base_name} @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        try:
            self.get_interface().read()  # First time powerup loads a string loaded in the buffer 'Keithley Instruments Inc., Model 2604B, 4607450, 3.4.0', needs to be flushed to sync measurement to forced value
        # pyvisa.errors.VisaIOError: VI_ERROR_TMO (-1073807339)
        except BaseException:
            pass
        self._configured_channels = {}
        self._output_off(channel_number=1)
        self._output_off(channel_number=2)
        self._high_capacitance(1, True)
        self._high_capacitance(2, True)
        self._remote_sense(1, True)
        self._remote_sense(2, True)
        # self.get_interface().write(':SOURce1:VOLTage:PROTection:LEVel 20') ##todo Dave fix
        # atexit.register(self._output_off, channel_number=1)
        # atexit.register(self._output_off, channel_number=2)

    def _channel_id(self, channel_number):
        if channel_number == 1:
            return 'a'
        elif channel_number == 2:
            return 'b'
        else:
            raise Exception(f'Unknown SMU channel number {channel_number}.')

    def _high_capacitance(self, channel_number, is_high_c):
        self.get_interface().write(
            f'smu{self._channel_id(channel_number)}.source.highc = smu{self._channel_id(channel_number)}.{"ENABLE" if is_high_c else "DISABLE"}')

    def _high_capacitanceq(self, channel_number):
        return self.get_interface().ask(
            f'smu{self._channel_id(channel_number)}.source.highc')

    def _remote_sense(self, channel_number, is_remote_sense):
        self.get_interface().write(
            f'smu{self._channel_id(channel_number)}.sense = smu{self._channel_id(channel_number)}.{"SENSE_REMOTE" if is_remote_sense else "SENSE_LOCAL"}')

    def _remote_senseq(self, channel_number):
        return self.get_interface().ask(
            f'smu{self._channel_id(channel_number)}.sense')

    def _output_off(self, channel_number):
        self.get_interface().write(
            f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_HIGH_Z')

    def _vforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.levelv = {value}')
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.func = smu{self._channel_id(channel_number)}.OUTPUT_DCVOLTS')
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_ON')
        else:
            pair_ch = self._configured_channels[channel_number]['i_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)

    def _iforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.leveli = {value}')
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.func = smu{self._channel_id(channel_number)}.OUTPUT_DCAMPS')
            self.get_interface().write(
                f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_ON')
        else:
            pair_ch = self._configured_channels[channel_number]['v_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)

    def _vsense(self, channel_number):
        # smuX.measure.autorangeY
        return self._parse_float(self.get_interface().ask(
            f'print(smu{self._channel_id(channel_number)}.measure.v())'))

    def _isense(self, channel_number):
        # what about channel number parsing?!?!?!?
        return self._parse_float(self.get_interface().ask(
            f'print(smu{self._channel_id(channel_number)}.measure.i())'))

    def _vcompl(self, channel_number, value):
        self.get_interface().write(
            f'smu{self._channel_id(channel_number)}.source.limitv = {value}')

    def _vcomplq(self, channel_number):
        return self.get_interface().ask(
            f'print(smu{self._channel_id(channel_number)}.source.limitv)')

    def _icompl(self, channel_number, value):
        self.get_interface().write(
            f'smu{self._channel_id(channel_number)}.source.limiti = {value}')

    def _icomplq(self, channel_number):
        return self.get_interface().ask(
            f'print(smu{self._channel_id(channel_number)}.source.limiti)')

    def _add_channel_voltage_force(self, channel):
        """Voltage force. Mutually exclusive at any moment with current force.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
        self.get_interface().write(
            f'smu{self._channel_id(channel.get_attribute("channel_number"))}.source.autorangev =  smu{self._channel_id(channel.get_attribute("channel_number"))}.AUTORANGE_ON')
        channel.set_min_write_limit(-200)
        channel.set_max_write_limit(200)

    def _add_channel_current_force(self, channel):
        """Current force. Mutually exclusive at any moment with voltage force.

        Internal implementation detail; see the public API for usage.

        Args:
            channel: Channel object.
        """
        self.get_interface().write(
            f'smu{self._channel_id(channel.get_attribute("channel_number"))}.source.autorangei =  smu{self._channel_id(channel.get_attribute("channel_number"))}.AUTORANGE_ON')
        channel.set_min_write_limit(-3)
        channel.set_max_write_limit(3)
