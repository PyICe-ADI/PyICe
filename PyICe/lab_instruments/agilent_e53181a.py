"""Agilent e53181a instrument driver.

>>> from PyICe.lab_instruments.agilent_e53181a import agilent_e53181a

"""
from PyICe.lab_core import *  # noqa: F403


class agilent_e53181a(scpi_instrument):
    """Agilent e53181a frequency counter.

    single channel, only uses channel 1 (front)
    you may need to set an expected value for autotriggering
    not recommended below 20hz
    defaults to 1Meg input R, 10x attenuation
    """
    def __init__(self, interface_visa):
        """Initialize agilent_e53181a.
        Calls the parent class constructor and initializes instance-specific
        attributes for agilent_e53181a.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'agilent_e53181a'
        # instrument.__init__(self,f"agilent_e53181a @ {interface_visa}")
        super(agilent_e53181a, self).__init__(
            f"agilent_e53181a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.config_expect(1e6)
        self.get_interface().write(("*CLS"))
        self.get_interface().write(("*RST"))
        self.config_input_attenuation_1x()
        self.config_input_impedance_1Meg()

    def config_input_attenuation_1x(self):
        """Set input attenuator to 1x.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write((":INPut1:ATTenuation 1"))

    def config_input_attenuation_10x(self):
        """Set input attenuator to 10x (divide by 10).

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write((":INPut1:ATTenuation 10"))

    def config_input_impedance_50(self):
        """Set input impedance to 50 Ohm.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write((":INPut1:IMPedance 50"))

    def config_input_impedance_1Meg(self):
        """Set input impedance to 1 MegOhm.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write((":INPut1:IMPedance 1e6"))

    def config_expect(self, expected_frequency):
        """Specify expected frequency to help with counting very low frequencies.
        Configures the expect operating parameters.

        Applies the specified configuration to the object or hardware.

        Args:
            expected_frequency: Expected frequency to use.
        """
        t = 1000 * 1 / float(expected_frequency)
        if t > 30:
            self.get_interface().timeout = int(t)
        else:
            self.get_interface().timeout = 30
        self.expect = expected_frequency

    def add_channel(self, channel_name):
        """Add named channels to instrument.
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
        self.add_channel_dutycycle(channel_name + "_dutycycle")
        return self.add_channel_freq(channel_name)

    def add_channel_freq(self, channel_name):
        """Add named frequency channel to instrument.
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
        freq_channel = channel(channel_name, read_function=self.read_frequency)
        return self._add_channel(freq_channel)

    def add_channel_dutycycle(self, channel_name):
        """Add named dutycycle channel to instrument.
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
        dutycycle_channel = channel(
            channel_name, read_function=self.read_dutycycle)
        return self._add_channel(dutycycle_channel)

    def read_frequency(self, channel_name):
        """Return float representing measured frequency of named channel.
        Sends the ``:MEASure:FREQuency`` SCPI command to the instrument.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The value read from the device or channel.
        """
        txt = ":MEASure:FREQuency? %3.0f, 1, (@1)" % self.expect
        while True:
            try:
                return (self.get_interface().ask(txt))
                break
            except Exception as e:
                print("Waiting on frequency meter")
                print(e)

    def read_dutycycle(self, channel_name):
        """Return float representing measured duty cycle of named channel.
        Sends the ``:MEASure:DCYCle`` SCPI command to the instrument.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The value read from the device or channel.
        """
        txt = ":MEASure:DCYCle? %3.0f, 1, (@1)" % self.expect
        while True:
            try:
                return (self.get_interface().ask(txt))
                break
            except Exception as e:
                print("Waiting on frequency meter")
                print(e)
