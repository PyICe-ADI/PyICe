class digital_IO_over_analog_output(object):
    """###SCHEDULED FOR DELETION###
    Use lab_instruments.digital_analog_io() virtual instrument instead.

    Wraps an analog output PyICe channel with a digital interface.
    domain_channel is the PyICe channel for the logic supply of the digital input
    we're talking to, e.g. master['vin_supply'] or master['dvcc_supply']."""
    def __init__(self, channel, domain_channel, VOL=0.0, delta_Vhook=1.5, tolerance=0.01, abs_max=None):
        from . import lab_core
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
            return min(v+self.delta_Vhook, self.abs_max)
        else:
            return v + self.delta_Vhook
    def _write_callback(self, domain_channel, voltage):
        self.VOH = voltage
        if abs(self.channel.read() - voltage) > self.tolerance:
            if self.output_state==True:
                # Output is logic high or delta_Vhook above logic high,
                # AND supply voltage is too different from the currently driven voltage,
                # so change it to equal to the new supply voltage.
                self.channel.write(voltage)
            elif isinstance(self.output_state, str) and self.output_state.lower()=="testhook":
                self.channel.write(self._add_with_abs_max(voltage))
    def digital_write(self, value):
        """Write any of (True, 1, 1.0) to set output to VOH,
        any of (False, 0, 0.0) to set output to VOL, and
        any of ("testhook", 2, 2.0) to set output to VOH+delta_Vhook.
        You can pass this method as the write_function argument
        to master.add_channel_virtual()"""
        if isinstance(value, str) and value.lower() in ("z", "hiz", "hi-z", "high-z"):
            raise NotImplementedError("Don't know how to hi-Z {}".format(self.channel.get_name()))
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
            raise NotImplementedError("Don't know how to digital_write({}{}) to {} !".format(value, type(value), self.channel.get_name()))