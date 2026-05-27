"""Digital  I O over analog output utility.

>>> from PyICe.lab_utils.digital_IO_over_analog_output import digital_IO_over_analog_output

"""
class digital_IO_over_analog_output(object):
    """Wrap an analog output channel with a digital logic interface.

    **DEPRECATED — SCHEDULED FOR DELETION.**
    Use ``lab_instruments.digital_analog_io()`` virtual instrument instead.

    This adapter lets you drive a physical analog output as if it were a
    digital signal by mapping logical high, low, and testhook states to
    configurable voltage levels. It tracks the logic-supply voltage via a
    write callback on *domain_channel* (e.g. ``master['vin_supply']``) and
    automatically updates the driven voltage when the supply changes.

    >>> from PyICe.lab_utils.digital_IO_over_analog_output import digital_IO_over_analog_output
    >>> digital_IO_over_analog_output is not None
    True

    """
    def __init__(self, channel, domain_channel, VOL=0.0,
                 delta_Vhook=1.5, tolerance=0.01, abs_max=None):
        """Initialize the digital-over-analog output wrapper.

        Configure the voltage levels used to represent logic states and
        register a write callback on *domain_channel* so that changes to
        the logic supply are automatically tracked.


        >>> from PyICe.lab_utils.digital_IO_over_analog_output import digital_IO_over_analog_output
        >>> hasattr(digital_IO_over_analog_output, '__init__')
        True

        Args:
            channel: The analog-output PyICe channel that will be driven
                with the computed voltage levels.
            domain_channel: The PyICe channel representing the logic-supply
                voltage (e.g. ``master['dvcc_supply']``). Its current value
                sets the initial VOH, and a write callback keeps VOH in
                sync whenever the supply is changed.
            VOL: Voltage driven for a logic-low output, in volts.
            delta_Vhook: Voltage added above VOH when the output is set to
                the "testhook" state, in volts.
            tolerance: Maximum allowable difference (volts) between the
                currently driven voltage and the new supply voltage before
                the callback will update the output.
            abs_max: Optional absolute maximum voltage (volts) that the
                output is allowed to reach; clamps the testhook voltage
                to this ceiling when set.
        """
        from PyICe import lab_core
        assert isinstance(channel, lab_core.channel)
        assert isinstance(domain_channel, lab_core.channel)
        self.channel = channel
        self.output_state = None  # True, False, "testhook", or None (unknown)
        self.domain_channel = domain_channel
        self.tolerance = tolerance
        self.abs_max = abs_max
        self.VOH = domain_channel.read()
        self.VOL = VOL
        self.delta_Vhook = delta_Vhook
        if self.VOH is None:
            self.VOH = 0.0  # A temporary, hopefully non-damaging value.
        domain_channel.add_write_callback(self._write_callback)

    def _add_with_abs_max(self, v):
        if self.abs_max is not None:
            return min(v + self.delta_Vhook, self.abs_max)
        else:
            return v + self.delta_Vhook

    def _write_callback(self, domain_channel, voltage):
        self.VOH = voltage
        if abs(self.channel.read() - voltage) > self.tolerance:
            if self.output_state is True:
                # Output is logic high or delta_Vhook above logic high,
                # AND supply voltage is too different from the currently driven voltage,
                # so change it to equal to the new supply voltage.
                self.channel.write(voltage)
            elif isinstance(self.output_state, str) and self.output_state.lower() == "testhook":
                self.channel.write(self._add_with_abs_max(voltage))

    def digital_write(self, value):
        """Set the output to a logic-high, logic-low, or testhook voltage.

        Translate a logical value into the corresponding analog voltage and
        drive it on the underlying channel. Accepts boolean-like values
        (True/1/1.0 → VOH), (False/0/0.0 → VOL), or a testhook designator
        (``"testhook"``/2/2.0 → VOH + delta_Vhook). String aliases such as
        ``"high"``, ``"low"``, ``"h"``, ``"l"`` are also supported. This
        method can be passed as the *write_function* argument to
        ``master.add_channel_virtual()``.


        >>> from PyICe.lab_utils.digital_IO_over_analog_output import digital_IO_over_analog_output
        >>> hasattr(digital_IO_over_analog_output, 'digital_write')
        True

        Args:
            value: The desired logic state. Use True / 1 / ``"high"`` for
                logic high (VOH), False / 0 / ``"low"`` for logic low
                (VOL), or ``"testhook"`` / 2 for VOH + delta_Vhook.

        Raises:
            NotImplementedError: If *value* requests a high-impedance state
                (e.g. ``"hi-z"``) or is otherwise unrecognised.
        """
        if isinstance(value, str) and value.lower() in (
                "z", "hiz", "hi-z", "high-z"):
            raise NotImplementedError(
                "Don't know how to hi-Z {}".format(self.channel.get_name()))
        elif value in (2, 2.0) or (isinstance(value, str) and value.lower() in ("testhook", "2", "2.0")):
            self.channel.write(self._add_with_abs_max(self.VOH))
            self.output_state = "testhook"
        elif value in (True, 1, 1.0) or (isinstance(value, str) and value.lower() in ("true", "1", "1.0", "h", "hi", "high")):
            self.channel.write(self.VOH)
            self.output_state = True
        elif value in (False, 0, 0.0) or (isinstance(value, str) and value.lower() in ("false", "0", "0.0", "l", "lo", "low")):
            self.channel.write(self.VOL)
            self.output_state = False
        else:
            raise NotImplementedError(
                "Don't know how to digital_write({}{}) to {} !".format(
                    value, type(value), self.channel.get_name()))
