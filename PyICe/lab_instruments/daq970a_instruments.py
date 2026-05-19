from ..lab_core import *  # noqa: F403
from PyICe.lab_utils.banners import print_banner
from PyICe.lab_utils.eng_string import eng_string
import math


class daq970a_instrument(scpi_instrument, delegator):
    """Superclass of all Agilent DAQ 970a plugin instruments."""

    def __init__(self, name, automatic_monitor):
        scpi_instrument.__init__(self, name)
        self._base_name = 'daq970a'
        delegator.__init__(self)
        self.scan_active = False
        self._last_scan_internal_addresses = None
        self._scanlist_ordered = []
        self.monitor_channel_num = None
        # This doesn't work!!! Monitor update rate is also affected by channel
        # delay for some reason.
        self.enable_automatic_monitor(automatic_monitor)
        self._automatic_monitor = automatic_monitor  # Why twice???

    # This doesn't work!!! Monitor update rate is also affected by channel
    # delay for some reason.
    def enable_automatic_monitor(self, enable):
        """Set to True to enable monitor channel auto-switching after single-channel scanlist read.

        After first reading, front panel display will continuously update with new results and successive reads will generally be faster without mux switching.
        set False to force traditional scanlist behavior and manual monitor channel selection via set_monitor and get_monitor_data methods.

        Args:
            enable: True to enable automatic monitor switching, False to disable.
        """
        self._automatic_monitor = enable

    def read_delegated_channel_list(self, channel_list):
        # channel_list is a list of channel objects
        # returns a dictionary of read data by channel name
        """Return read delegated channel list result.

        Args:
            channel_list: Channel list.

        Returns:
            Result value.

        Raises:
            Exception: On error condition.
        """
        results = results_ord_dict()
        # special case for reading the moniotor
        # This doesn't work!!! Monitor update rate is also affected by channel
        # delay for some reason.
        if False and self._automatic_monitor \
           and len(channel_list) == 1 \
           and channel_list[0].get_attribute('internal_address') == self.monitor_channel_num \
           and channel_list[0].get_attribute('a970a_type') in ['volts_dc', 'current_dc', 'thermocouple']:
            # wait for two full measurement cycles in case first one was just
            # getting started when input changed. Then add one more below for
            # mismatched clocks.
            az_multiplier = 4 if channel_list[0].get_attribute(
                'auto_zero') else 2
            # emergency exit in the case of excessive quantization noise to
            # thermal noise ratio.
            max_time = time.time() + (az_multiplier + 1) * 0.017 * \
                max(channel_list[0].get_attribute('NPLC'), 1)
            # measurements take ~2x the expected NPLC time with autozero and ~1x the expected NPLC time with autozero disabled,
            # but don't scale well below NPLC=1
            stale_result = self.get_monitor_data()
            result = stale_result
            while result == stale_result and time.time() < max_time:
                # wait
                result = self.get_monitor_data()
            # may have changed forcing conditions during last conversion
            questionable_result = result
            while result == questionable_result and time.time() < max_time:
                # wait some more
                result = self.get_monitor_data()
            # if time.time() > max_time:
            #    print(f'WARNING: 3497x monitor channel: {channel_list[0].get_name()} read timed out without value change. This might be normal if quantization noise exceeds thermal noise.')
            results[channel_list[0].get_name()] = self.get_monitor_data()
            return results
        self.scan_active = True
        scan_internal_addresses = [channel.get_attribute(
            'internal_address') for channel in channel_list]
        if self.monitor_channel_num is not None:
            scan_internal_addresses.append(self.monitor_channel_num)
        scan_internal_addresses = list(
            set(scan_internal_addresses))  # remove duplicates
        # note cannot store last scan and avoid writing it reconfiguring
        # channels breaks it
        self._last_scan_internal_addresses = scan_internal_addresses
        cmd = "ROUTe:SCAN (@"
        for internal_address in scan_internal_addresses:
            cmd += str(internal_address) + ','
        cmd = cmd.rstrip(',') + ")"
        self.get_interface().write(cmd)
        # then get the list back to learn channel order
        txt_scanlist = self.get_interface().ask("ROUTe:SCAN?")
        try:
            txt_scanlist = txt_scanlist.split("(@")[1]
        except BaseException:
            print('Communication problem; attempting resyc.')
            self.get_interface().resync()
            raise Exception('Resync complete; better luck next time.')
        txt_scanlist = txt_scanlist.strip(")'")
        self._scanlist_ordered = list(map(int, txt_scanlist.split(",")))
        self.init()
        self.operation_complete()
        txt = self.fetch()
        vals = txt.split(",")
        self.scan_results = results_ord_dict()
        for (internal_address, val) in zip(self._scanlist_ordered, vals):
            self.scan_results[internal_address] = val
        for channel in channel_list:
            results[channel.get_name()] = channel.read_without_delegator()
        # if self._automatic_monitor and len(channel_list) == 1:
        if len(channel_list) == 1:
            self.monitor_channel_num = channel_list[0].get_attribute(
                'internal_address')
            self.get_interface().write(
                f"ROUTe:MONitor (@{self.monitor_channel_num})")
            self.get_interface().write("ROUTe:MONitor:STATe ON")
        return results

    def read_raw(self, internal_address):
        # the scan list is in the delegator, not the creating instrument
        """Return read raw result.

        Args:
            internal_address: Internal address.

        Returns:
            Result value.
        """
        assert internal_address in self.resolve_delegator().scan_results
        return self.resolve_delegator().scan_results[internal_address]

    def read_apply_function(self, internal_address, function):
        """Return read apply function result.

        Args:
            function: Function.
            internal_address: Internal address.

        Returns:
            Result value.
        """
        return function(self.read_raw(internal_address))

    def _add_bay_number(self, channel_object, bay, number):
        channel_object.set_attribute('bay', bay)
        channel_object.set_attribute('number', number)
        channel_object.set_attribute('internal_address', number + 100 * bay)

    def _get_internal_address_by_name(self, channel_name):
        channel = self.get_channel(channel_name)
        return channel.get_attribute('internal_address')

    def set_monitor(self, monitor_channel_name):
        """View named channel measurement on the front panel whenever scan is idle.

        Args:
            monitor_channel_name: Name of the channel to display on the front panel.
        """
        channel = self.get_channel(monitor_channel_name)
        channel_number = channel.get_attribute('internal_address')
        if channel_number != self.monitor_channel_num:
            cmd = f"ROUTe:SCAN (@{channel_number})"
            self.get_interface().write(cmd)
            self.monitor_channel_num = channel_number
            self.get_interface().write(f"ROUTe:MONitor (@{channel_number})")
            self.get_interface().write("ROUTe:MONitor:STATe ON")

    def get_monitor_data(self, channel_name=None):
        """Return data from last monitor reading.

        Args:
            channel_name: Optional name of channel to set as monitor before reading.

        Returns:
            The float value from the last monitor reading.
        """
        if channel_name is not None:
            self.set_monitor(channel_name)
        return float(self.get_interface().ask('ROUTe:MONitor:DATA?'))


class agilent_a970a_chassis(daq970a_instrument):
    """A lab_bench-like container object to speed up operation of the 34970 instrument.

    If each plugin from the three expansion bays is added individually to the lab_bench,
    the scanlist must be modified for each plugin to run separate scans on each individual plugin.
    This object will construct a composite scanlist, then appropriately parse the results back to the individual instruments.
    """
    def __init__(self, interface_visa, automatic_monitor=True):
        """Agilent a970a collection object.

        Args:
            interface_visa: VISA interface string for the instrument.
            automatic_monitor: Enable automatic monitor channel switching.
        """
        self._base_name = 'daq970a_chasis'
        daq970a_instrument.__init__(self,
                                    f'daq970a_chasis @ {interface_visa}',
                                    automatic_monitor=automatic_monitor)
        self.add_interface_visa(interface_visa)

    def add(self, new_instrument):
        """Only appropriate to add instantiated daq970a plugin instrument objects to this class (20ch, 40ch, dacs, dig-in, dig-out, etc).

        Args:
            new_instrument: A daq970a_instrument instance to add to the chassis.

        Raises:
            Exception: If new_instrument is not a daq970a_instrument instance.
        """
        if not isinstance(new_instrument, daq970a_instrument):
            raise Exception(
                f"{instrument} doesn't fit inside daq970a expansion bay.  If you push too hard, you might break something")
        channel_group.add(self, new_instrument)
        new_instrument.set_delegator(self)


class agilent_a970a_20ch_40ch(daq970a_instrument):
    """Superclass for the DAQM901A, DAQM902A and DAQM908A input measurement multiplexers.

    All functionality common to the 20Ch and 40Ch is implemented here and inherited
    by the appropriate subclasses.
    """
    def __init__(self, interface_visa, bay, automatic_monitor=True):
        """Initialize instrument.

        bay is 1-3.  1 is top slot, 3 is bottom slot.

        Args:
            interface_visa: VISA interface string for the instrument.
            bay: Plugin bay number (1-3). 1 is top slot, 3 is bottom slot.
            automatic_monitor: Enable automatic monitor channel switching.
        """
        self._base_name = 'daq970a_mux'
        self.bay = bay
        daq970a_instrument.__init__(
            self,
            f'adq970a_mux bay: {bay} @ {interface_visa}',
            automatic_monitor=automatic_monitor)
        self.add_interface_visa(interface_visa)
        # breakpoint()
        plugin_type = self.get_interface().ask(
            f"SYSTem:CTYPe? {bay * 100}").split(",")[1]
        counts = self._get_all_relay_cycles(
            channel_count=40 if plugin_type == "DAQM908A" else 20)
        if any(count > 10e6 for count in counts):
            print_banner(
                f"Some relays in the 3497xa bay {bay} plugin have more than 10 million cycles.",
                "Consider replacing plugin.")
            print(f"Counts: {counts}")

    def add_channel(self, channel_name, channel_num):
        """Register a named channel.  No configuration takes place.  When the channel is read directly,.

        or through read_channels(), an appropriate scanlist will be written to the 34970.
        channel_num is 1-22 for the 20Ch mux (1-20 no current, 21-22 current only)
        channel_num is 1-40 for the 40Ch mux.

        Args:
            channel_name: Name for the new channel.
            channel_num: Physical channel number on the mux.

        Returns:
            The newly created channel object.
        """
        internal_address = self.bay * 100 + channel_num
        new_channel = channel(
            channel_name,
            read_function=lambda: self.read_apply_function(
                internal_address,
                float))
        new_channel.set_delegator(self)
        self._add_bay_number(new_channel, self.bay, channel_num)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return self._add_channel(new_channel)

    def add_channel_dc_voltage(self, channel_name, channel_num, NPLC=1, range="AUTO",
                               high_z=True, delay=None, disable_autozero=True, Rsource=None):
        """Shortcut method to add voltage channel and configure in one step.

        Args:
            channel_name: Name for the new voltage channel.
            channel_num: Physical channel number on the mux.
            NPLC: Number of power line cycles for integration.
            range: Measurement range or "AUTO".
            high_z: True for >10G ohm input impedance, False for 10M ohm.
            delay: Delay in seconds between relay close and measurement start.
            disable_autozero: True to disable autozero, False to enable.
            Rsource: Source resistance in ohms for automatic delay calculation.

        Returns:
            The configured voltage channel object.
        """
        # TODO: add_extended_channels argument to add nplc, delay, etc all at
        # once???
        channel = self.add_channel(channel_name, channel_num)
        channel.set_attribute('a970a_type', 'volts_dc')
        channel.set_display_format_function(
            function=lambda float_data: eng_string(
                float_data, fmt=':3.6g', si=True) + 'V')
        if Rsource is not None:
            if delay is not None:
                print(f"WARNING: Rsource({Rsource:.3g} ohms) and Delay({delay:.3g} s) "
                      "BOTH specified in add_channel_dc_voltage('{channel_name}')\n"
                      "  hence I'm IGNORING Rsource and setting Delay to {delay:g} s")
            else:
                # 13.8 tau for PPM settling.
                source_delay_ms = math.ceil(
                    math.log(1e6) * Rsource * 1390e-12 * 1e3)
                # per Steve's memo SM87, 2ms minimum. Delay resolution = 1ms
                # per Agilent manual.
                delay = max(source_delay_ms * 1e-3, 0.002)
                channel.set_attribute("Rsource", Rsource)
        self._config_dc_voltage(
            channel,
            NPLC,
            range,
            high_z,
            delay,
            disable_autozero)
        channel.set_attribute("delay", delay)
        channel.set_description(
            self.get_name() + ': ' + self.add_channel_dc_voltage.__doc__)
        return channel

    def add_channel_thermocouple(
            self, channel_name, channel_num, tcouple_type, NPLC=1, disable_autozero=True):
        """Shortcut method to add thermistor measurement channel and configure in one step.

        Args:
            channel_name: Name for the new thermocouple channel.
            channel_num: Physical channel number on the mux.
            tcouple_type: Thermocouple type (J, K, or T).
            NPLC: Number of power line cycles for integration.
            disable_autozero: True to disable autozero, False to enable.

        Returns:
            The configured thermocouple channel object.
        """
        new_channel = self.add_channel(channel_name, channel_num)
        new_channel.set_attribute('a970a_type', 'thermocouple')
        new_channel.set_display_format_function(
            function=lambda float_data: eng_string(
                float_data, fmt=':3.6g', si=True) + '°C')
        internal_address = new_channel.get_attribute('internal_address')
        self._config_thermocouple(internal_address, tcouple_type)
        self._configure_channel_nplc(new_channel, NPLC)
        self._configure_channel_autozero(new_channel, disable_autozero)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_thermocouple.__doc__)
        return new_channel

    def _set_impedance_10GOhm(self, channel, high_z=True):
        """Set channel impedance to >1GOhm if high_z is True and voltage range allows, otherwise 10M.

        impedance always 10M if argument is false.

        Args:
            channel: Channel object to configure impedance for.
            high_z: True for >10G ohm input impedance, False for 10M ohm.
        """
        internal_address = channel.get_attribute('internal_address')
        channel.set_attribute('input_impedance_hiz', high_z)
        if (high_z is True):
            self.get_interface().write(
                f"INPut:IMPedance:AUTO ON , (@{internal_address})")
        else:
            self.get_interface().write(
                f"INPut:IMPedance:AUTO OFF , (@{internal_address})")

    def _config_dc_voltage(self, channel, NPLC, range,
                           high_z, delay, disable_autozero):
        """Reconfigure channel to measure DC voltage, with input impedance >10G if range allows.

        Optionally specify number of powerline cycles integration period and attenuator range.

        Args:
            channel: Channel object to configure.
            NPLC: Number of power line cycles for integration.
            range: Measurement range or "AUTO".
            high_z: True for >10G ohm input impedance, False for 10M ohm.
            delay: Delay in seconds between relay close and measurement start.
            disable_autozero: True to disable autozero, False to enable.
        """
        internal_address = channel.get_attribute('internal_address')
        self.get_interface().write(
            f"CONFigure:VOLTage:DC {range} , (@{internal_address})")
        self._configure_channel_nplc(channel, NPLC)
        self._set_impedance_10GOhm(channel, high_z)
        self._configure_channel_autozero(channel, disable_autozero)
        if delay is not None:
            self._config_channel_delay(channel, delay)

    def _config_thermocouple(self, internal_address, thermocouple_type):
        if thermocouple_type.upper() not in ['J', 'K', 'T']:
            raise Exception('Invalid thermocouple type, valid types are J,K,T')
        self.get_interface().write(
            f"CONFigure:TEMPerature TCouple,{thermocouple_type.upper()},(@{internal_address})")

    def _config_channel_delay(self, channel, delay):
        """Delay specified number of seconds between closing relay and starting DMM measurement for channel.

        Args:
            channel: Channel object to configure delay for.
            delay: Delay time in seconds.
        """
        internal_address = channel.get_attribute('internal_address')
        channel.set_attribute('delay', delay)
        self.get_interface().write(
            f"ROUT:CHAN:DELAY {delay},(@{internal_address})")

    def _configure_channel_autozero(self, channel, disable_autozero):
        """Disable or enable (default) the autozero mode. The OFF and ONCE.

        parameters have a similar effect. Autozero OFF does not issue a new
        zero measurement until the next time the instrument goes to the
        "wait-for-trigger" state. Autozero ONCE issues an immediate zero
        measurement. The :AUTO? query the autozero mode. Returns "0"
        (OFF or ONCE) or "1" (ON).

        Autozero OFF Operation
        Following instrument warm-up at calibration temperature ±1 °C
        and < 10 minutes, add 0.0002% range additional error + 5 μV.

        Args:
            channel: Channel object to configure autozero for.
            disable_autozero: True to disable autozero (ONCE mode), False to enable (ON mode).
        """
        internal_address = channel.get_attribute('internal_address')
        self.get_interface().write(
            f"SENSe:ZERO:AUTO {'ONCE' if disable_autozero else 'ON'},(@{internal_address})")
        channel.set_attribute('auto_zero', not (disable_autozero))

    def _config_channel_scaling(self, channel, gain=1, offset=0, unit=None):
        """Perform y=mx+b scaling to channel inside instrument and change displayed units.

        Args:
            channel: Channel object to configure scaling for.
            gain: Multiplier (m) for scaling equation y=mx+b.
            offset: Offset (b) for scaling equation y=mx+b.
            unit: Display unit string (e.g. "V", "A").
        """
        internal_address = channel.get_attribute('internal_address')
        if gain is not None:
            self.get_interface().write(
                f"CALCulate:SCALe:GAIN {gain}, (@{internal_address})")
            channel.set_attribute('gain', gain)
        if offset is not None:
            self.get_interface().write(
                f"CALCulate:SCALe:OFFSet {offset}, (@{internal_address})")
            channel.set_attribute('offset', offset)
        if unit is not None:
            self.get_interface().write(
                f'CALCulate:SCALe:UNIT "{unit}", (@{internal_address})')
            channel.set_attribute('unit', unit)
            channel.set_display_format_function(
                function=lambda float_data: eng_string(
                    float_data, fmt=':3.6g', si=True) + unit)
        self.get_interface().write(
            f"CALCulate:SCALe:STATe ON ,(@{internal_address})")

    def _configure_channel_nplc(self, channel, nplc):
        try:
            channel_type = channel.get_attribute('a970a_type')
            internal_address = channel.get_attribute('internal_address')
            channel.set_attribute('NPLC', nplc)
        except ChannelAttributeException:
            raise Exception(f'Cannot configure nplc for channel {channel}')
        if channel_type == 'volts_dc':
            self.get_interface().write(
                f"VOLTage:DC:NPLC {nplc}, (@{internal_address})")
        elif channel_type == 'current_dc':
            self.get_interface().write(
                f"CURRent:DC:NPLC {nplc},(@{internal_address})")
        elif channel_type == 'thermocouple':
            self.get_interface().write(
                f"SENSe:TEMPerature:NPLC {nplc},(@{internal_address})")
        else:
            raise Exception(
                'Unkown a970a_type, cannot set NPLC for this type of channel')

    def add_channel_nplc(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the nplc setting of an existing channel.

        Args:
            channel_name: Name for the new NPLC control channel.
            base_channel: The measurement channel whose NPLC to modify.

        Returns:
            The newly created NPLC control channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda nplc: self._configure_channel_nplc(
                base_channel,
                nplc))
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_nplc.__doc__)
        new_channel.write(base_channel.get_attribute('NPLC'))
        return self._add_channel(new_channel)

    def add_channel_delay(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the delay of an existing channel.

        Args:
            channel_name: Name for the new delay control channel.
            base_channel: The measurement channel whose delay to modify.

        Returns:
            The newly created delay control channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda delay: self._config_channel_delay(
                base_channel,
                delay))
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delay.__doc__)
        try:
            new_channel.write(base_channel.get_attribute('delay'))
        except ChannelAttributeException:
            pass
        return self._add_channel(new_channel)

    def add_channel_input_hiz(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the input impedance of an existing channel.

        Write channel to True for >10G mode (<~10V), False for 10Meg mode.

        Args:
            channel_name: Name for the new impedance control channel.
            base_channel: The measurement channel whose input impedance to modify.

        Returns:
            The newly created impedance control channel.
        """
        new_channel = integer_channel(
            channel_name,
            size=1,
            write_function=lambda hiz: self._set_impedance_10GOhm(
                base_channel,
                hiz))
        self._add_channel(new_channel)
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_input_hiz.__doc__)
        new_channel.write(base_channel.get_attribute('input_impedance_hiz'))
        return new_channel

    def add_channel_autozero(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the auto-zero mode of an existing channel.

        Write channel to True autozero every measurement (doubling measurement time), False for one-time autozero.

        Args:
            channel_name: Name for the new autozero control channel.
            base_channel: The measurement channel whose autozero mode to modify.

        Returns:
            The newly created autozero control channel.
        """
        new_channel = integer_channel(
            channel_name,
            size=1,
            write_function=lambda enable_autozero: self._configure_channel_autozero(
                base_channel,
                disable_autozero=not (enable_autozero)))
        self._add_channel(new_channel)
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_autozero.__doc__)
        new_channel.write(base_channel.get_attribute('auto_zero'))
        return new_channel

    def add_channel_range_readback(self, channel_name, base_channel):
        """Add a channel that reads back the current voltage range setting.

        Args:
            channel_name: Name for the new range readback channel.
            base_channel: The measurement channel to read range from.

        Returns:
            The newly created range readback channel.
        """
        new_channel = channel(channel_name, read_function=lambda bc=base_channel: float(
            self.get_interface().ask(f"SENSe:VOLTage:DC:RANGe? (@{bc.get_attribute('internal_address')})")))
        return self._add_channel(new_channel)

    def add_channel_gain(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the gain (span multiplier) of an existing channel.

        Args:
            channel_name: Name for the new gain control channel.
            base_channel: The measurement channel whose gain to modify.

        Returns:
            The newly created gain control channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda gain: self._config_channel_scaling(
                base_channel,
                gain=gain,
                offset=None,
                unit=None))
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_gain.__doc__)
        try:
            new_channel.write(base_channel.get_attribute('gain'))
        except KeyError:
            new_channel.write(1)
        return self._add_channel(new_channel)

    def add_channel_offset(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the offset of an existing channel.

        Args:
            channel_name: Name for the new offset control channel.
            base_channel: The measurement channel whose offset to modify.

        Returns:
            The newly created offset control channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda offset: self._config_channel_scaling(
                base_channel,
                gain=None,
                offset=offset,
                unit=None))
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_offset.__doc__)
        try:
            new_channel.write(base_channel.get_attribute('offset'))
        except KeyError:
            new_channel.write(0)
        return self._add_channel(new_channel)

    def add_channel_unit(self, channel_name, base_channel):
        """Adds a secondary channel that can modify the displayed unit (V/A/etc) of an existing channel.

        Args:
            channel_name: Name for the new unit control channel.
            base_channel: The measurement channel whose display unit to modify.

        Returns:
            The newly created unit control channel.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda unit: self._config_channel_scaling(
                base_channel,
                gain=None,
                offset=None,
                unit=unit))
        new_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_offset.__doc__)
        try:
            new_channel.write(base_channel.get_attribute('unit'))
        except KeyError:
            new_channel.write('V')
        return self._add_channel(new_channel)

    def _get_all_relay_cycles(self, channel_count):
        channel_list = "@ "
        for channel in range(1, channel_count + 1):
            channel_list += f"{self.bay * 100 + channel},"
        channel_list = channel_list[:-1]
        counts = [
            int(count) for count in (
                self.get_interface().ask(
                    f"SYSTem:RELay:CYCLes? ({channel_list})")).split(",")]
        return counts


class agilent_a970a_20ch(agilent_a970a_20ch_40ch):
    """Extends base class to add methods specific to the 20-channel mux that are.

    not appropriate for the 40-channel mux such as frequency, current measurement (internal shunt),
    and current measurement (external sense resistor).
    """
    def __init__(self, *args, **kwargs):
        agilent_a970a_20ch_40ch.__init__(self, *args, **kwargs)
        self.plugin_type = "34901A"

    def add_channel_dc_current(self, channel_name, channel_num,
                               NPLC=1, range='AUTO', delay=None, disable_autozero=True):
        """DC current measurement only allowed on 34901A channels 21 and 22.

        Args:
            channel_name: Name for the new current channel.
            channel_num: Physical channel number (must be 21 or 22).
            NPLC: Number of power line cycles for integration.
            range: Measurement range or "AUTO".
            delay: Delay in seconds between relay close and measurement start.
            disable_autozero: True to disable autozero, False to enable.

        Returns:
            The configured current measurement channel.

        Raises:
            Exception: If channel_num is not 21 or 22.
        """
        if channel_num not in [21, 22]:
            raise Exception(
                'Invalid channel number, channel cannot be used for current')
        channel = self.add_channel(channel_name, channel_num)
        channel.set_attribute('a970a_type', 'current_dc')
        channel.set_display_format_function(
            function=lambda float_data: eng_string(
                float_data, fmt=':3.6g', si=True) + 'A')
        self._config_dc_current(channel, range)
        self._configure_channel_nplc(channel, NPLC)
        self._configure_channel_autozero(channel, disable_autozero)
        if delay is not None:
            self._config_channel_delay(channel, delay)
        channel.set_description(
            self.get_name() + ': ' + self.add_channel_dc_current.__doc__)
        return channel

    def _config_dc_current(self, channel, range="AUTO"):
        """DC current measurement only allowed on 34901A channels 21 and 22.

        Args:
            channel: Channel object to configure for DC current measurement.
            range: Measurement range or "AUTO".
        """
        internal_address = channel.get_attribute('internal_address')
        channel.set_attribute('range', range)
        self.get_interface().write(
            f"CONFigure:CURRent:DC {range},(@{internal_address})")

    def add_channel_ammeter_range(self, channel_name, base_channel):
        """Modify ammeter current range shunt.

        Args:
            channel_name: Name for the new range control channel.
            base_channel: The current measurement channel whose range to modify.

        Returns:
            The newly created range control channel.
        """
        assert base_channel.get_attribute(
            'number') == 21 or base_channel.get_attribute('number') == 22
        range_channel = channel(
            channel_name,
            write_function=lambda range: self._config_dc_current(
                base_channel,
                range))
        range_channel.set_description(
            self.get_name() + ': ' + self.add_channel_ammeter_range.__doc__)
        range_channel.set_attribute(
            'measurement_channel',
            base_channel.get_name())
        range_channel.write(base_channel.get_attribute('range'))
        return self._add_channel(range_channel)

    def config_freq(self, channel_name):
        """Configure a channel to measure frequency.

        Args:
            channel_name: Name of the channel to configure for frequency measurement.
        """
        print('config_freq expect this to change and become an add_channel')
        internal_address = self._get_internal_address_by_name(channel_name)
        self.get_interface().write(
            f"CONFigure:FREQuency (@{internal_address})")

    def config_res(self, channel_name):
        """DC resistance measurement.

        Args:
            channel_name: Name of the channel to configure for resistance measurement.
        """
        print('config_res expect this to change and become an add_channel')
        ch_list = f"(@{self._get_internal_address_by_name(channel_name)})"
        self.get_interface().write("CONFigure:RESistance " + ch_list)

    def add_channel_current_sense(self, channel_name, channel_num, gain=1, NPLC=10,
                                  range="AUTO", resistance=None, delay=None, disable_autozero=True, Rsource=None):
        """Configure channel to return current measurement by scaling voltage measured across.

        user-supplied sense resistor.  Specify either gain or its reciprocal resistance.

        Args:
            channel_name: Name for the new current sense channel.
            channel_num: Physical channel number on the mux.
            gain: Scaling gain factor (reciprocal of resistance).
            NPLC: Number of power line cycles for integration.
            range: Measurement range or "AUTO".
            resistance: Sense resistor value in ohms (alternative to gain).
            delay: Delay in seconds between relay close and measurement start.
            disable_autozero: True to disable autozero, False to enable.
            Rsource: Source resistance in ohms for automatic delay calculation.

        Returns:
            The configured current sense channel.

        Raises:
            Exception: If both resistance and gain are specified.
        """
        if Rsource is None:
            Rsource = resistance
        channel = self.add_channel_dc_voltage(channel_name=channel_name,
                                              channel_num=channel_num,
                                              NPLC=NPLC,
                                              range=range,
                                              disable_autozero=disable_autozero,
                                              Rsource=Rsource
                                              )
        if resistance is not None and gain != 1:
            raise Exception('Resistance and Gain cannot both be specified')
        if (resistance is not None):
            gain = 1.0 / resistance
            channel.set_attribute("shunt_resistance", resistance)
        channel.set_attribute("gain", gain)
        self._config_channel_scaling(channel, gain, 0, "A")
        if delay is not None:
            self._config_channel_delay(channel, delay)
        channel.set_description(
            self.get_name() + ': ' + self.add_channel_current_sense.__doc__)
        channel.set_display_format_function(
            function=lambda float_data: eng_string(
                float_data, fmt=':3.6g', si=True) + 'A')
        return channel


class agilent_a970a_20ch(agilent_a970a_20ch):
    pass


class agilent_a970a_40ch(agilent_a970a_20ch_40ch):
    """Implement any methods specific to the 40-channel mux here."""

    def __init__(self, *args, **kwargs):
        agilent_a970a_20ch_40ch.__init__(self, *args, **kwargs)
        self.plugin_type = "DAQM908A"


class agilent_a970a_40ch(agilent_a970a_40ch):
    pass


class agilent_a970a_40ch(agilent_a970a_40ch):
    pass


class agilent_a970a_908A_40ch(agilent_a970a_40ch):
    """Extend base class to add module name to class name for compatibility."""


class agilent_a970a_901A_20ch(agilent_a970a_20ch):
    """Extend base class to add module name to class name for compatibility."""


class agilent_a970a_dacs(daq970a_instrument):
    """Control of the two dacs in the multifunction module."""

    def __init__(self, interface_visa, bay):
        """Bay is numbered (1,2,3).  1 is the upper bay.  3 is the lower bay.

        Args:
            interface_visa: VISA interface string for the instrument.
            bay: Plugin bay number (1-3). 1 is upper, 3 is lower.
        """
        self._base_name = 'agilent_a970a_dacs'
        self.bay = bay
        self.plugin_type = "DAQM907A"
        daq970a_instrument.__init__(
            self, f'a970a_dacs bay: {bay} @ {interface_visa} ', False)
        self.add_interface_visa(interface_visa)

    def add_channel(self, channel_name, channel_num):
        """Add named DAC channel to instrument.  num is 1-2, mapping to physical channel 4-5.

        Args:
            channel_name: Name for the new DAC channel.
            channel_num: DAC number (1 or 2), mapping to physical channel 4-5.

        Returns:
            The newly created DAC channel object.
        """
        if ((channel_num != 1) & (channel_num != 2)):
            print(("ERROR invalid dac " + self.get_name() + ", " + channel_num))
        channel_num += 3
        internal_address = channel_num + self.bay * 100
        new_channel = channel(
            channel_name,
            write_function=lambda voltage: self.write_voltage(
                internal_address,
                voltage))
        new_channel.set_attribute('a970a_type', 'DAC')
        self._add_bay_number(new_channel, self.bay, channel_num)
        self._add_channel(new_channel)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return new_channel

    def write_voltage(self, internal_address, voltage):
        """Set named DAC to voltage.  Range is +/-12V with 16bit (366uV) resolution.

        Args:
            internal_address: Internal address of the DAC channel.
            voltage: Voltage to set in the range +/-12V.
        """
        txt = "SOURCE:VOLT " + str(voltage) + \
            ", (@" + str(internal_address) + ")"
        self.get_interface().write(txt)


class agilent_a970a_dacs(agilent_a970a_dacs):
    pass


class agilent_a970a_actuator(daq970a_instrument):
    """Agilent_a34970a_actuator 20 channel general purpose actuator plugin module.

    each channel is a relay which can be toggled from open to closed.
    note that the physical open button on the unit switches the relay to the NC position.
    """
    def __init__(self, interface_visa, bay):
        """Interface_visa is a interface_visa.

        bay is 970 plugin bay 1-3.

        Args:
            interface_visa: VISA interface string for the instrument.
            bay: Plugin bay number (1-3).
        """
        self._base_name = 'agilent_a970a_actuator'
        self.bay = bay
        self.plugin_type = "DAQM903A"
        daq970a_instrument.__init__(
            self,
            f'a970a_actuator: {bay} @ {interface_visa} ',
            automatic_monitor=False)
        self.add_interface_visa(interface_visa)

    def add_channel(self, channel_name, channel_num):
        """Channel_num is 1-20.

        Args:
            channel_name: Name for the new relay channel.
            channel_num: Physical channel number (1-20).

        Returns:
            The newly created relay channel object.
        """
        internal_address = channel_num + self.bay * 100
        new_channel = channel(
            channel_name,
            write_function=lambda state: self._write_relay(
                internal_address,
                state))
        new_channel.set_attribute('a970a_type', 'actuator')
        self._add_bay_number(new_channel, self.bay, channel_num)
        self._add_channel(new_channel)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return new_channel

    def _close(self, internal_address):
        self.get_interface().write(f"ROUTe:CLOSe (@{internal_address})")

    def _open(self, internal_address):
        self.get_interface().write(f"ROUTe:OPEN (@{internal_address})")

    def _write_relay(self, internal_address, state):
        """Boolean True closes relay channel_name, boolean False opens relay channel_name.

        Args:
            internal_address: Internal address of the relay channel.
            state: True to close relay, False to open relay.
        """
        if state:
            self._close(internal_address)
        else:
            self._open(internal_address)

    # NB #CB fixed to use self.bay intead of hard coded base address = 200
    def open_all_relays(self):
        """Perform open all relays operation."""
        base = self.bay * 100
        for internal_address in range(base + 1, base + 21):
            self._open(internal_address)


class agilent_a970a_dig_out8(daq970a_instrument):
    """Agilent_a34970a_dig_out8 8 bit digital output of the 34907A plugin module.

    each multifunction module has 2 8 bit digital ports or 1 16 bit port
    each 8 bit port may be input or output but not both.
    """
    def __init__(self, interface_visa, bay, ch):
        """Interface_visa.

        bay is 34970 plugin bay 1-3.  ch is digital bank 1-2.

        Args:
            interface_visa: VISA interface string for the instrument.
            bay: Plugin bay number (1-3).
            ch: Digital bank number (1-2).
        """
        self._base_name = 'agilent_3497xa_dig_out8'
        self.bay = bay
        self.plugin_type = "DAQM907A"
        daq970a_instrument.__init__(
            self,
            f'34970a_digital bay: {bay} @ {interface_visa} ',
            automatic_monitor=False)
        self.add_interface_visa(interface_visa)
        self.channel_number = ch
        self.internal_address = bay * 100 + ch
        self.data = 0
        self._defined_bit_mask = 0

    def add_channel(self, channel_name, start=0, size=8):
        """Add channel by channel_name, shifted left by start bits and masked to size bits.

        ie to create a 3 bit digital channel on bits 1,2,3 add_channel("channel_name",1,3).

        Args:
            channel_name: Name for the new digital output channel.
            start: Starting bit position within the 8-bit word.
            size: Number of bits for this channel.

        Returns:
            The newly created digital output channel.

        Raises:
            Exception: If bits overlap with previously defined channels or exceed 8 bits.
        """
        mask = pow(2, size) - 1 << start
        if mask & self._defined_bit_mask:
            raise Exception(
                f"{self.get_name()} {channel_name}: bit defined in multiple channels. Prev Mask: {self._defined_bit_mask}, Channel Mask: {mask} ")
        self._defined_bit_mask |= mask
        if (start + size) > 8 or start < 0 or size < 1:
            raise Exception(f"{self.get_name()}: only 8 bits allowed")
        new_channel = integer_channel(
            channel_name,
            size=size,
            write_function=lambda value: self._write_bits(
                start,
                size,
                value))
        new_channel.set_attribute('a970a_type', 'digital_output')
        self._add_bay_number(new_channel, self.bay, self.channel_number)
        self._add_channel(new_channel)
        new_channel.write(0)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return new_channel

    def _write_bits(self, start, size, value):
        """Write named channel to value.  Value is an integer which counts by "1".

        The value is automatically truncated and shifted according to the location information
        provided to add_channel().  The remainder of the digital word not included in the channel remains unchanged.

        Args:
            start: Starting bit position within the 8-bit word.
            size: Number of bits for this channel.
            value: Integer value to write to the channel.
        """
        # construct mask
        mask = pow(2, size) - 1 << start
        self.data = self.data & ~mask
        self.data |= (value << start) & mask
        self.get_interface().write(
            f"SOURce:DIGital:DATA {self.data},(@{self.internal_address})")


class agilent_a970a_dig_out8(agilent_a970a_dig_out8):
    pass


class agilent_a970a_dig_in8(daq970a_instrument):
    """Agilent_a34970a_dig_in8  8 bit digital input of the 34907A plugin module.

    each multifunction module has 2 8 bit digital ports or 1 16 bit port
    each 8 bit port may be input or output but not both
    """
    def __init__(self, interface_visa, bay, ch):
        """Interface_visa.

        bay is 34970 plugin bay 1-3.  ch is digital bank 1-2.

        Args:
            interface_visa: VISA interface string for the instrument.
            bay: Plugin bay number (1-3).
            ch: Digital bank number (1-2).
        """
        self._base_name = 'agilent_3497xa_dig_in8'
        self.bay = bay
        self.plugin_type = "DAQM907A"
        self.channel_number = ch
        self.internal_address = self.bay * 100 + self.channel_number
        daq970a_instrument.__init__(
            self, f'34970a_digital bay: {self.bay},{self.channel_number} @ {interface_visa}', automatic_monitor=False)
        self.add_interface_visa(interface_visa)
        self.get_interface().write(
            f'CONFigure:DIGital:BYTE (@{self.internal_address})')

    def add_channel(self, channel_name, start=0, size=8):
        """Add channel by name, shifted left by start bits and masked to size bits.

        ie to create a 3 bit digital channel on bits 1,2,3 add_channel("channel_name",1,3).

        Args:
            channel_name: Name for the new digital input channel.
            start: Starting bit position within the 8-bit word.
            size: Number of bits for this channel.

        Returns:
            The newly created digital input channel.

        Raises:
            Exception: If start + size exceeds 8 bits.
        """
        if (start + size) > 8:
            raise Exception(f"{self.get_name()}: only 8 bits allowed")

        def conversion_function(data):
            """Return conversion function result.

            Args:
                data: Data to write.

            Returns:
                Result value.
            """
            return self._read_bits(start, size, data)

        def read_function():
            """Return read function result.

            Returns:
                Result value.
            """
            return self.read_apply_function(
                self.internal_address, conversion_function)
        new_channel = integer_channel(
            channel_name, size=size, read_function=read_function)
        new_channel.set_delegator(self)
        new_channel.set_attribute('a970a_type', 'digital_input')
        self._add_bay_number(new_channel, self.bay, self.channel_number)
        self._add_channel(new_channel)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return new_channel

    def _read_bits(self, start, size, data):
        """Return the measured value for the named channel.  Value is shifted right to count by "1" independent of.

        the actual location of the channel within the physical byte.

        Args:
            start: Starting bit position within the 8-bit word.
            size: Number of bits for this channel.
            data: Raw data string from the instrument.

        Returns:
            The extracted integer value for the channel bits.
        """
        mask = pow(2, size) - 1 << start
        # data string from instrument is f.p. (ex '+2.55E+02')
        data = (int(float(data)) & mask) >> start
        return data


class agilent_a970a_totalizer(daq970a_instrument):
    """Implement this if you need it.

    26-bit totalizer on physical channel s03 of the 34907A plugin module
    """
    # self.plugin_type = "34907A"
