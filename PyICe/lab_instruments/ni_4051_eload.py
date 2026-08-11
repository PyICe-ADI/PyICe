""" NI PXIe-4051 60 V, 40 A PXI Electronic Load Module instrument driver.

>>> from PyICe.lab_instruments.ni_4051_eload import pxie_4051

"""
import nidcpower
from nidcpower.errors import DriverError
from colorama import Fore
from PyICe.lab_core import instrument, channel


class pxie_4051(instrument):  # pylint: disable=too-many-public-methods
    def __init__(self, resource_name):
        self._base_name = "PXIe-4051_ELOAD"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")
        self.session = nidcpower.Session(resource_name=resource_name, reset=True)

    def setup_channels(self, channel_name):
        self.session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.output_function = nidcpower.OutputFunction.DC_CURRENT
        self.session.initiate()
        self.add_channel_enable(channel_name)
        self.add_channel_current_level(channel_name)
        self.add_channel_current_level_range(channel_name)
        self.add_channel_voltage_level_range(channel_name)
        self.add_channel_sensing(channel_name)
        self.add_channel_nplc(channel_name)
        self.add_channel_source_delay(channel_name)
        self.add_channel_current_rise_slew_rate(channel_name)
        self.add_channel_current_fall_slew_rate(channel_name)
        self.add_channel_isense(channel_name)
        self.add_channel_vsense(channel_name)
        self.write_channel(f'{channel_name}_current_level_range', 'AUTO')
        self.write_channel(f'{channel_name}_voltage_level_range', 'AUTO')
        self.write_channel(f'{channel_name}_nplc', 10)

    def init_session(self):
        try:
            self.session.initiate()
        except DriverError as e:
            if e.code == -1074118652:  # The session is already running
                pass
            else:
                raise RuntimeError(
                    f"{Fore.LIGHTRED_EX}Error initiating the session: {e}{Fore.RESET}"
                ) from e

    def set_output_status(self, state='OFF'):
        if state == 'ON':
            self.session.output_enabled = True
        else:
            self.session.output_enabled = False

    def get_output_status(self):
        return 'ON' if self.session.output_enabled else 'OFF'

    def set_current_level(self, value):
        self.session.current_level = value
        self.init_session()

    def get_current_level(self):
        return float(self.session.current_level)

    def set_current_level_range(self, value):
        if value not in ['AUTO', 4, 40]:
            raise ValueError(
                f'{Fore.CYAN}Not a valid current range setting, valid settings are 4, 40, AUTO{Fore.RESET}'
            )

        self.session.abort()
        if isinstance(value, str):
            value = value.upper()
        if value == "AUTO":
            self.session.current_level_autorange = True
        else:
            self.session.current_level_autorange = False
            self.session.current_level_range = value
        self.session.initiate()

    def get_current_level_range(self):
        return float(self.session.current_level_range)

    def set_voltage_level_range(self, value):
        if value not in ['AUTO', 6, 60]:
            raise ValueError(
                f'{Fore.CYAN}Not a valid voltage range setting, valid settings are 6, 60, AUTO{Fore.RESET}'
            )

        self.session.abort()
        if isinstance(value, str):
            value = value.upper()
        if value == "AUTO":
            self.session.voltage_level_autorange = True
        else:
            try:
                self.session.voltage_level_autorange = False
                self.session.voltage_level_range = value
                self.session.initiate()
            except DriverError as e:
                if e.code == -1074097882:  # Requested value is not a supported
                    self.session.abort()
                    self.session.voltage_level_autorange = False
                    self.session.voltage_level_range = 60.0  # Set to the max supported range
                    self.session.initiate()
                else:
                    raise RuntimeError(
                        f"{Fore.LIGHTRED_EX}Error setting voltage level range: {e}{Fore.RESET}"
                    ) from e
        self.init_session()

    def get_voltage_level_range(self):
        return float(self.session.voltage_level_range)

    def set_source_delay(self, value):  # In seconds
        self.session.abort()
        self.session.source_delay = value
        self.init_session()

    def get_source_delay(self):
        time_delta = self.session.source_delay
        return time_delta.total_seconds()  # Convert to seconds

    def set_current_level_rise_slew_rate(self, value):
        # Default is 2.4A/microsecond
        self.session.abort()
        self.session.current_level_rising_slew_rate = value
        self.init_session()

    def get_current_level_rise_slew_rate(self):
        return self.session.current_level_rising_slew_rate

    def set_current_level_fall_slew_rate(self, value):
        # Default is 2.4A/microsecond
        self.session.abort()
        self.session.current_level_falling_slew_rate = value
        self.init_session()

    def get_current_level_fall_slew_rate(self):
        return self.session.current_level_falling_slew_rate

    def set_nplc(self, value):
        self.session.abort()
        self.session.aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
        self.session.aperture_time = value
        self.init_session()

    def get_nplc(self):
        return self.session.aperture_time

    def set_sensing(self, value):
        if value not in ['LOCAL', 'REMOTE']:
            raise ValueError(
                f'{Fore.CYAN}Not a valid sensing setting, valid settings are LOCAL or REMOTE{Fore.RESET}'
            )

        self.session.abort()
        if value == "REMOTE":
            self.session.sense = nidcpower.Sense.REMOTE
        else:
            self.session.sense = nidcpower.Sense.LOCAL
        self.init_session()

    def get_sensing(self):
        return "LOCAL" if self.session.sense == nidcpower.Sense.LOCAL else "REMOTE"

    def get_current_sense(self):
        if self.get_compliance():
            raise RuntimeError(
                f"{Fore.LIGHTRED_EX}"
                "Reporting a fault condition — CURRENT measurement data is invalid."
                f"{Fore.RESET}"
            )
        return float(self.session.measure(nidcpower.MeasurementTypes.CURRENT))

    def get_voltage_sense(self):
        if self.get_compliance():
            raise RuntimeError(
                f"{Fore.LIGHTRED_EX}"
                "Reporting a fault condition — VOLTAGE measurement data is invalid."
                f"{Fore.RESET}"
            )
        return float(self.session.measure(nidcpower.MeasurementTypes.VOLTAGE))

    def get_compliance(self):
        return self.session.query_in_compliance()

    def add_channel_enable(self, channel_name):
        new_channel = channel(
            channel_name + "_enable",
            write_function=lambda state: self.set_output_status(state)  # pylint: disable=W0108
        )
        new_channel.add_preset('ON', "")
        new_channel.add_preset('OFF', "")
        new_channel._set_value(self.get_output_status())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current_level(self, channel_name):
        new_channel = channel(
            channel_name + "_current",
            write_function=lambda value: self.set_current_level(value)  # pylint: disable=W0108
        )
        new_channel._write_max = 40.0  # pylint: disable=protected-access
        new_channel._set_value(self.get_current_level())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current_level_range(self, channel_name):
        new_channel = channel(
            channel_name + "_current_level_range",
            write_function=lambda value: self.set_current_level_range(value)  # pylint: disable=W0108
        )
        new_channel.add_preset("AUTO", "")
        new_channel.add_preset(4.0, "")
        new_channel.add_preset(40.0, "")
        new_channel._set_value(self.get_current_level_range())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_voltage_level_range(self, channel_name):
        new_channel = channel(
            channel_name + "_voltage_level_range",
            write_function=lambda value: self.set_voltage_level_range(value)  # pylint: disable=W0108
        )
        new_channel.add_preset("AUTO", "")
        # new_channel.add_preset(6.0, "")
        # Disabled the 6V range, is not supported on PXIe-4051, but showing on InstrumentStudio GUI.
        new_channel.add_preset(60.0, "")
        new_channel._set_value(self.get_voltage_level_range())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_sensing(self, channel_name):
        new_channel = channel(
            channel_name + "_sensing",
            write_function=lambda value: self.set_sensing(value)  # pylint: disable=W0108
        )
        new_channel.add_preset("LOCAL", "")
        new_channel.add_preset("REMOTE", "")
        new_channel._set_value(self.get_sensing())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_nplc(self, channel_name):
        new_channel = channel(
            channel_name + "_nplc",
            write_function=lambda value: self.set_nplc(value)  # pylint: disable=W0108
        )
        new_channel._write_min = 0.000033  # pylint: disable=protected-access
        new_channel._write_max = 60.0  # pylint: disable=protected-access
        new_channel._set_value(self.get_nplc())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_source_delay(self, channel_name):
        new_channel = channel(
            channel_name + "_source_delay",
            write_function=lambda value: self.set_source_delay(value)  # pylint: disable=W0108
        )
        new_channel._set_value(self.get_source_delay())  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current_rise_slew_rate(self, channel_name):
        new_channel = channel(
            channel_name + "_current_rise_slew_rate",
            write_function=lambda value: self.set_current_level_rise_slew_rate(value)  # pylint: disable=W0108
        )
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current_fall_slew_rate(self, channel_name):
        new_channel = channel(
            channel_name + "_current_fall_slew_rate",
            write_function=lambda value: self.set_current_level_fall_slew_rate(value)  # pylint: disable=W0108
        )
        self._add_channel(new_channel)
        return new_channel

    def add_channel_isense(self, channel_name):
        new_channel = channel(
            channel_name + "_isense",
            read_function=lambda: self.get_current_sense()  # pylint: disable=W0108
        )
        self._add_channel(new_channel)
        return new_channel

    def add_channel_vsense(self, channel_name):
        new_channel = channel(
            channel_name + "_vsense",
            read_function=lambda: self.get_voltage_sense()  # pylint: disable=W0108
        )
        self._add_channel(new_channel)
        return new_channel

    def __del__(self):
        """ This ensures your class cleans up explicitly.
            Prevents the driver’s background cleanup from firing at exit."""
        try:
            self.session.close()
        except (DriverError, AttributeError):
            pass
