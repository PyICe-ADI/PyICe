"""Fluke 8845 instrument driver.

>>> from PyICe.lab_instruments.fluke_8845 import fluke_8845

"""
from ..lab_core import *  # noqa: F403


class fluke_8845(scpi_instrument):
    """Single channel fluke 8845 meter.

    defaults to dc voltage, note this instrument currently does not support using multiple measurement types at the same time
    """
    def __init__(self, interface_visa):
        """Interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'fluke_8845'
        scpi_instrument.__init__(self, f"fluke_8845 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        if isinstance(self.get_interface(),
                      lab_interfaces.interface_visa_serial):
            self._set_remote_mode()
            time.sleep(0.2)  # add delay for 34401 remote mode setting error
            self.get_interface().ser.dsrdtr = True
        self.config_dc_voltage()

    def config_dc_voltage(self):
        """Set meter to measure DC volts with default settings.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write('FUNCtion "VOLT:DC"')

    # def config_dc_voltage(self, NPLC=1, range="AUTO", BW=20):
        # '''Set meter to measure DC volts.  Optionally set number of powerline cycles for integration to
        # [.02,.2,1,10,100] and set range to [0.1, 1, 10, 100, 1000]'''
        # #DJS Todo: Move this stuff to channel wrappers like 34970
        # if NPLC not in [.02,.2,1,10,100]:
        # raise Exception("Error: Not a valid NPLC setting, valid settings are 0.02, 0.2, 1, 10, 100")
        # if BW not in [3, 20, 200]:
        # raise Exception("Error: Not a valid BW setting, valid settings are 3, 20, 200")
        # self.get_interface().write("FUNCtion \"VOLT:DC\"")
        # #range is optional string value that is the manual range the meter should operate in.
        # #valid values are in volts: [0.01, 0.1, 1, 3]
        # self.get_interface().write("CONFigure:VOLTage:DC " + str(range))
        # self.get_interface().write("VOLTage:DC:NPLC " + str(NPLC))
        # self.get_interface().write("SENSe:DETector:BANDwidth " + str(BW))
        # self.get_interface().write("INPut:IMPedance:AUTO ON")

    def set_autozero_mode(self, mode):
        """[SENSe:]ZERO:AUTO {OFF|ONCE|ON}.
        Sends the ``SENSe:ZERO:AUTO`` SCPI command to the instrument.
        Sends the appropriate SCPI command to configure the instrument's
        autozero mode.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            mode: Operating mode.
        """
        if mode.upper() not in ["ON", "OFF", "AUTO"]:
            print(
                f"\n\nAgilent 33401a - Sorry don't know how to set_autozero_mode to {mode}, must be one of [ON|OFF|AUTO]")
            exit()
        self.get_interface().write(f'SENSe:ZERO:AUTO {mode.upper()}')

    def config_dc_current(self, NPLC=1, range=None, BW=20):
        """Configure meter for DC current measurement.

        NPLC is an optional number of integration powerline cycles
        Valid values are: [.02,.2,1,10,100]
        range is optional string value that is the manual range the meter should operate in.
        Valid values are in amps: [0.01, 0.1, 1, 3]

        Args:
            BW: Bandwidth limit setting.
            NPLC: Number of power line cycles for integration.
            range: Measurement or output range.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if NPLC not in [.02, .2, 1, 10, 100]:
            raise Exception(
                "Error: Not a valid NPLC setting, valid settings are 0.02, 0.2, 1, 10, 100")
        self.get_interface().write('FUNCtion "CURRent:DC"')
        if (range is not None):
            self.get_interface().write("CONFigure:CURRent:DC " + str(range))
        self.get_interface().write("CURRent:DC:NPLC " + str(NPLC))
        self.get_interface().write("SENSe:DETector:BANDwidth " + str(BW))
    # def config_ac_voltage(self, BW=200):
        # '''Configure meter for AC voltage measurement'''
        # if BW not in [3, 20, 200]:
        # raise Exception("Error: Not a valid BW setting, valid settings are 3, 20, 200")
        # self.get_interface().write("SENSe:DETector:BANDwidth " + str(BW))
        # self.get_interface().write("INPut:IMPedance:AUTO ON")
        # self.get_interface().write('FUNCtion "VOLT:AC"')
    # def config_ac_current(self):
        # '''Configure meter for AC current measurement'''
        # self.get_interface().write('FUNCtion "CURRent:AC"')

    def add_channel(self, channel_name):
        """Add named channel to instrument without configuring measurement type.
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
        meter_channel = channel(channel_name, read_function=self.read_meter)
        return self._add_channel(meter_channel)

    def read_meter(self):
        """Return float representing meter measurement.  Units are V,A,Ohm, etc depending on meter configuration.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The value read from the device or channel.
        """
        return float(self.get_interface().ask("READ?"))

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
