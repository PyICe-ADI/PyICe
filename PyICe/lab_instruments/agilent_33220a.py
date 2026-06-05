"""Agilent 33220a instrument driver.

>>> from PyICe.lab_instruments.agilent_33220a import agilent_33220a

"""
from ..lab_core import *  # noqa: F403
import time


class agilent_33220a(scpi_instrument):
    """Function/Arbitrary Waveform Generator.

    intrument will default to pulse generation - this driver does not support other functions yet
    main channel controls sending of the trigger (write value = 1)to generate the pulse
    extended channels will control othe pulse paramters (low voltage, high voltage, pulse width, period and slew rate
    """
    def __init__(self, interface_visa):
        """Interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'agilent_33220a'
        scpi_instrument.__init__(self, f"33220a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        if isinstance(self.get_interface(),
                      lab_interfaces.interface_visa_serial):
            self._set_remote_mode()
            time.sleep(0.2)
            self.get_interface().ser.dsrdtr = True
        self.get_interface().write("*RST")
        self._config_pulse_func()

    def _config_pulse_func(self, high_voltage=3.3, low_voltage=0,
                           period=1e-3, pulse_width=100e-6, cycle_count=1):
        """Set to instrument to output pulse.
        Internal helper that sends the ``TRIGger:SOURce`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            cycle_count: Cycle count to use.
            high_voltage: High voltage to use.
            low_voltage: Low voltage to use.
            period: Signal period.
            pulse_width: Pulse width to use.
        """
        self.get_interface().write("FUNCtion PULSe")
        self.get_interface().write("OUTPut:LOAD 50")
        self._write_high_voltage(high_voltage)
        self._write_low_voltage(low_voltage)
        self._write_pulse_period(period)
        self._write_pulse_width(pulse_width)
        self._write_cycle_count(cycle_count)
        self.get_interface().write("BURSt:MODE TRIGgered")
        self.get_interface().write("BURSt:PHASe 0")
        self.get_interface().write("TRIGger:SOURce bus")
        self.get_interface().write("BURSt:STATe on")
        self.get_interface().write("OUTPut on")

    def config_sinusoid_func(self):
        """Perform config sinusoid func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def config_square_func(self):
        """Perform config square func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def config_ramp_func(self):
        """Perform config ramp func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def config_noise_func(self):
        """Perform config noise func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def config_dc_func(self):
        """Perform config dc func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def config_user_func(self):
        """Perform config user func operation.

        Applies the specified configuration to the object or hardware.
        """
        pass

    def add_channel(self, channel_name, add_extended_channels=True):
        """Add a channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            add_extended_channels: If True, add sense and mode channels.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        trigger_channel = self.add_channel_trigger(channel_name)
        # self.write_channel(channel_name,0)
        if add_extended_channels:
            self.add_channel_low_voltage(channel_name + "_low_voltage")
            self.add_channel_high_voltage(channel_name + "_high_voltage")
            self.add_channel_pulse_width(channel_name + "_pulse_width")
            self.add_channel_pulse_period(channel_name + "_period")
            self.add_channel_slew_rate(channel_name + "_slew_rate")
            self.add_channel_cycle_count(channel_name + "_cycle_count")
        else:
            print(
                'Manually add channels for high_voltage, low_voltage, pulse_width, period, and/or slew_rate')
        return trigger_channel

    def add_channel_low_voltage(self, channel_name):
        """Add a channel low voltage.
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
            write_function=lambda low_voltage: self._write_low_voltage(low_voltage))
        new_channel.add_preset('0', 'Default Value')
        return self._add_channel(new_channel)

    def add_channel_high_voltage(self, channel_name):
        """Add a channel high voltage.
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
            write_function=lambda high_voltage: self._write_high_voltage(high_voltage))
        new_channel.add_preset('3.3', 'Default Value')
        return self._add_channel(new_channel)

    def add_channel_pulse_width(self, channel_name):
        """Add a channel pulse width.
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
            write_function=lambda pulse_width: self._write_pulse_width(pulse_width))
        new_channel.add_preset('100e-6', 'Default Value')
        new_channel.set_max_write_limit(1999.99)
        new_channel.set_min_write_limit(20e-9)
        return self._add_channel(new_channel)

    def add_channel_pulse_period(self, channel_name):
        """Add a channel pulse period.
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
            write_function=lambda period: self._write_pulse_period(period))
        new_channel.add_preset('1e-3', 'Default Value')
        new_channel.set_max_write_limit(2000)
        new_channel.set_min_write_limit(200e-9)
        return self._add_channel(new_channel)

    def add_channel_slew_rate(self, channel_name):
        """Add a channel slew rate.
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
            write_function=lambda slew_rate: self._write_pulse_slew_rate(slew_rate))
        new_channel.add_preset('5e-9', 'Default Value')
        new_channel.set_max_write_limit(100e-9)
        new_channel.set_min_write_limit(5e-9)
        return self._add_channel(new_channel)

    def add_channel_trigger(self, channel_name):
        """Add a channel trigger.
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
        self.trigger_channel = channel(
            channel_name, write_function=lambda trigger: self._send_trigger(trigger))
        self.trigger_channel.add_preset('TRIGGER', 'Send Trigger')
        self.trigger_channel.add_preset('STANDBY', 'Waiting for Trigger')
        return self._add_channel(self.trigger_channel)

    def add_channel_cycle_count(self, channel_name):
        """Add a channel cycle count.
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
            The count.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda cycle_count: self._write_cycle_count(cycle_count))
        new_channel.add_preset('1', 'Default Value')
        new_channel.set_max_write_limit(50000)
        new_channel.set_min_write_limit(1)
        return self._add_channel(new_channel)

    def _write_low_voltage(self, low_voltage):
        self.get_interface().write(f"VOLTage:LOW {low_voltage}")

    def _write_high_voltage(self, high_voltage):
        self.get_interface().write(f"VOLTage:HIGH {high_voltage}")

    def _write_pulse_width(self, pulse_width):
        self.get_interface().write(f"FUNCtion:PULSe:WIDTh {pulse_width}")

    def _write_pulse_period(self, period):
        self.get_interface().write(f"PULSe:PERiod {period}")

    def _write_pulse_slew_rate(self, slew_rate):
        self.get_interface().write(f"FUNCtion:PULSe:TRANsition {slew_rate}")

    def _write_cycle_count(self, cycle_count):
        self.get_interface().write(f"BURSt:NCYCles {cycle_count}")

    def _send_trigger(self, trigger):
        if trigger == "TRIGGER":
            self.trigger()
            self.operation_complete()
            # sets the trigger channel back to STANDBY when OPeration Complete
            self.trigger_channel.write("STANDBY")

    def _set_remote_mode(self, remote=True):
        """Required for RS-232 control.  Not allowed for GPIB control.
        Internal helper that sends the ``SYSTem:LOCal`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            remote: Remote to use.
        """
        if remote:
            self.get_interface().write("SYSTem:REMote")
        else:
            self.get_interface().write("SYSTem:LOCal")
