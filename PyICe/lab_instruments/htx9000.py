"""Htx9000 instrument driver.

>>> from PyICe.lab_instruments.htx9000 import htx9000

"""
from ..lab_core import *  # noqa: F403


class htx9000(scpi_instrument):
    """Single Channel Hypertronix (Steve Martin) HTX9000.

    400nA < IL < 2.5A, up to 60V, 20W Max on fanless version.
    """
    def __init__(self, interface_visa):
        """Initialize htx9000.
        Stores configuration in ``_base_name``, ``_forced_range`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'htx9000'
        scpi_instrument.__init__(self, f"HTX9000 {interface_visa}")
        self.add_interface_visa(interface_visa, timeout=0.5)
        self._write_swipepad_lock(True)
        # atexit.register(lambda: self._write_swipepad_lock(False))
        self._forced_range = None

    def __del__(self):
        """Close interface (serial) port on exit.

        Performs cleanup when the object is garbage-collected.
        """
        self.get_interface().close()

    def add_channel(self, channel_name, add_extended_channels=True):
        """Helper function adds current forcing channel of channel_name.

        optionally also adds _dropout and _readback channels.

        Args:
            add_extended_channels: If True, add sense and mode channels.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        if add_extended_channels:
            self.add_channel_current_readback(channel_name + "_readback")
            self.add_channel_dropout(channel_name + "_dropout")
            # self.add_channel_swipepad_lock(channel_name + "_swipepad_lock")
            self.add_channel_manual_range(f'{channel_name}_range_setting')
            self.add_channel_range_readback(f'{channel_name}_range')
        return self.add_channel_current(channel_name)

    def add_channel_current(self, channel_name):
        """Add a channel current.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self._write_current)
        # new_channel.set_min_write_warning(0.0) # set_min_write_limit too draconian. Crashes scripts that could have otherwise cleaned up. Caveat Emptor.
        # new_channel.set_max_write_warning(2.5) # set_max_write_limit too
        # draconian. Crashes scripts that could have otherwise cleaned up.
        # Caveat Emptor.
        new_channel.set_min_write_limit(0.0)
        new_channel.set_max_write_limit(2.5)
        new_channel.set_write_resolution(decimal_digits=7)  # 100nA low range
        new_channel.add_write_callback(
            write_callback=self._wait_settle_callback)
        new_channel.write(0)
        return self._add_channel(new_channel)

    def _wait_settle_callback(self, channel, data):
        pass
        # print("Current: ", data, "Sleeping for: ", (2e-6/data + 0.025) if data > 0 else 0.025)
        # time.sleep((20e-6/data + 0.025) if data > 0 else 0.025)

    def add_channel_current_readback(self, channel_name):
        """Add a channel current readback.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=self._readback_current)
        return self._add_channel(new_channel)

    def add_channel_dropout(self, channel_name):
        """Add a channel dropout.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = integer_channel(
            name=channel_name,
            size=1,
            read_function=self._read_dropout)
        return self._add_channel(new_channel)

    def add_channel_temp_heatsink(self, channel_name):
        """Add a channel temp heatsink.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=self._read_heatsink_temp)
        return self._add_channel(new_channel)

    def add_channel_temp_board(self, channel_name):
        """Add a channel temp board.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=self._read_board_temp)
        return self._add_channel(new_channel)

    def add_channel_swipepad_lock(self, channel_name):
        """Add a channel swipepad lock.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = integer_channel(
            name=channel_name,
            size=1,
            write_function=self._write_swipepad_lock)
        new_channel.write(0)
        return self._add_channel(new_channel)

    def add_channel_manual_range(self, channel_name):
        """Add a channel manual range.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name, write_function=lambda rng: setattr(
                self, '_forced_range', rng))
        new_channel.add_preset(None, 'Autorange')
        new_channel.add_preset('HIGH', 'High (2.5A) range')
        new_channel.add_preset('LOW', 'Low (25mA) range')
        return self._add_channel(new_channel)

    def add_channel_range_readback(self, channel_name):
        """Add a channel range readback.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SOURce:CURRent:RANGe`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self.get_interface().ask(':SOURce:CURRent:RANGe?'))
        # TODO: Enumerations?
        # This query returns the range of the load box setting as either 0(low)
        # or 1(high).
        return self._add_channel(new_channel)

    def _write_current(self, value, range=None):
        """Write channel to value.
        Internal helper that sends the ``SOURce:CURRent:RANGe:LOw`` SCPI
        command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            range: Measurement or output range.
            value: Value to set.

        Raises:
            Exception: If an unexpected error occurs.
        """
        # TODO: instrument currently broken - sets range to low if under-range
        # on input Steve to fix.
        if value < 0:  # ooops need to fix instrument, does bad things when asked to make negative SM.
            value = 0
        if (range is not None):
            if (range.upper() == "HIGH" or range.upper() == "HI"):
                cmd = f"SOURce:CURRent:RANGe:HIgh {value:7.5e}"
            elif (range.upper() == "LOW" or range.upper() == "LO"):
                cmd = f"SOURce:CURRent:RANGe:LOw {value:7.5e}"
            else:
                raise Exception('Valid ranges are "HIGH" and "LOW"')
        elif self._forced_range is not None:
            if self._forced_range == "HIGH":
                cmd = f"SOURce:CURRent:RANGe:HIgh {value:7.5e}"
            elif self._forced_range == "LOW":
                cmd = f"SOURce:CURRent:RANGe:LOw {value:7.5e}"
            else:
                raise Exception('Valid ranges are "HIGH" and "LOW"')
        else:
            cmd = f"SOURce:CURRent {float(value):7.5e}"
        self.get_interface().write(cmd)
        try:
            response = self.get_interface().ask("SYSTem:ERRor?")
            # print f"HTX9000 err {response}"
            err = int(response.split(",")[0])
            if (err != 0):
                raise Exception(f"WARNING, SCPI Error: {response}")
        except Exception as e:
            print(f"{e} from inside HTX9000 {self._name} write_channel ")
            flush_chars = self.get_interface().resync()
            print(f"saw {len(flush_chars)} extra characters: {flush_chars}")

    def _read_dropout(self):
        """Return False if in regulation, True if in dropout.
        Internal helper that sends the ```` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        while True:
            data = self.get_interface().ask("DROPout?")
            try:
                data = int(data)
                if (data == 0 or data == 1):
                    return bool(data)
                else:
                    raise Exception(f"WARNING, Bad Response: {data}")
            except Exception as e:
                flush_chars = self.get_interface().resync()
                print(
                    f"{e} from inside HTX9000 {self._name} read_dropout. SCPI Error: {self.get_interface().ask('SYSTem:ERRor?')}")
                print(
                    f"saw {len(flush_chars)} extra characters: {flush_chars}")
                flush_chars = self.get_interface().resync()

    def _readback_current(self):
        """Return current setting from instrument.  Steve verify that this is just a rounded version of what.

        was previously written.

        Returns:
            The measured value.
        """
        while True:
            data = self.get_interface().ask("SOURce:CURRent?")
            try:
                return float(data)
            except Exception as e:
                flush_chars = self.get_interface().resync()
                print(
                    f"{e} from inside HTX9000 {self._name} read_current. SCPI Error: {self.get_interface().ask('SYSTem:ERRor?')}")
                print(
                    f"saw {len(flush_chars)} extra characters: {flush_chars}")
                flush_chars = self.get_interface().resync()

    def _read_heatsink_temp(self):
        return float(self.get_interface().ask("TEMP:HEATsink?"))

    def _read_board_temp(self):
        return float(self.get_interface().ask("TEMP:BOARD?"))

    def _write_swipepad_lock(self, value):
        """Turn on or off the swipe pad lock so incidental contact doesn't change the value.
        Internal helper that sends the ``SYSTem:LOCK`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            value: Value to set.
        """
        self.get_interface().write("SYSTem:LOCK" if value else "SYSTem:LOCK:RELease")
        try:
            response = self.get_interface().ask("SYSTem:ERRor?")
            err = int(response.split(",")[0])
            if (err != 0):
                raise Exception(f"WARNING, SCPI Error: {response}")
        except Exception as e:
            print(f"{e} from inside HTX9000 {self._name} write_channel ")
            flush_chars = self.get_interface().resync()
            print(
                f"saw {len(flush_chars)} extra characters: {flush_chars} during SYSTem:LOCK or SYSTem:LOCK:RELease")

    def get_serial_number(self):
        """Return the serial number.
        Queries the instrument for its current serial number and returns the
        parsed response.
        Queries the instrument for its current serial number and returns the
        parsed response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The current serial number.
        """
        ident = self.get_interface().ask("*IDN?")
        return ident.split(",")[2].strip()


class htx9000SE_5A(htx9000):
    """Modified Single Channel Hypertronix (Steve Martin) HTX9000SE.

    400nA < IL < 5A, up to 60V.
    """
    def __init__(self, interface_visa):
        """Initialize htx9000 s e_5 a.
        Stores configuration in ``_base_name``, ``_forced_range`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'HTX9000_SE5A'
        scpi_instrument.__init__(self, f"HTX9000SE5A {interface_visa}")
        self.add_interface_visa(interface_visa, timeout=0.5)
        self._write_swipepad_lock(True)
        # atexit.register(lambda: self._write_swipepad_lock(False))
        self._forced_range = None

    def add_channel_current(self, channel_name):
        """Add a channel current.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self._write_current)
        new_channel.set_min_write_limit(0.0)
        new_channel.set_max_write_limit(5)
        new_channel.set_write_resolution(decimal_digits=7)  # 100nA low range
        new_channel.add_write_callback(
            write_callback=self._wait_settle_callback)
        new_channel.write(0)
        return self._add_channel(new_channel)
