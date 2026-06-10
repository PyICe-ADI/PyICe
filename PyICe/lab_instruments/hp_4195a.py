"""Hp 4195a instrument driver.

>>> from PyICe.lab_instruments.hp_4195a import hp_4195a

"""
from ..lab_core import *  # noqa: F403


class hp_4195a(scpi_instrument):
    """HP4195A Network Analyzer.

    Current Driver Only Collects Data; no configuration or measurement trigger
    """
    def __init__(self, interface_visa):
        """Interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'hp_4195a'
        scpi_instrument.__init__(self, f"h4195a @ {interface_visa}")
        self.add_interface_visa(interface_visa)

    def add_channel(self, channel_name, register):
        """Register must be.

        X - frequency
        A - A register
        B - B register
        C - C register
        D - D register

        Args:
            channel_name: Name for the new channel.
            register: Register object representing a device register.

        Returns:
            The newly created channel object.

        Raises:
            Exception: If an unexpected error occurs.
        """
        register = register.upper()
        if register.upper() not in ['X', 'A', 'B', 'C', 'D']:
            raise Exception(f'Bad register {register} for 4195a')
        new_channel = channel(
            channel_name,
            read_function=lambda: self._read_4195a_register(register))
        return self._add_channel(new_channel)

    def _read_4195a_register(self, register):
        """Read from one of the five hardware registers associated with this channel_name.  Return list of scalars representing points.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.

        Args:
            register: Register object representing a device register.

        Returns:
            The measured value.
        """
        data = self.get_interface().ask(('{register}?'))
        return list(map(float, data.split(',')))

    def config_network(self, start=0.1, stop=500e6,
                       RBW='AUTO', NOP=401, OSCA=-50):
        """Configure the 4195 for network analysis  with start, stop, sweep type and resolution.
        Configures the instrument for network measurement mode via SCPI
        commands.
        Configures the instrument for network measurement mode via SCPI
        commands.

        Applies the specified configuration to the object or hardware.

        Args:
            NOP: Nop to use.
            OSCA: Osca to use.
            RBW: Rbw to use.
            start: Start bit position.
            stop: If True, send stop condition.
        """
        self.get_interface().write(("RST"))
        self.get_interface().write((f"OSC1={OSCA}"))
        self.get_interface().write(("FNC1"))  # set Network
        self.get_interface().write((f"START={start}"))  # start freq
        self.get_interface().write((f"STOP={stop}"))  # stop freq
        if RBW == 'AUTO':
            self.get_interface().write(('CPL1'))
        else:
            self.get_interface().write((f"RBW={RBW}"))  # resolution bandwidth
        self.get_interface().write((f"NOP={NOP}"))  # number of points in sweet
        self.get_interface().write(("SWT2"))  # log sweep
        self.get_interface().write(("SWM2"))  # single trigger mode

    def config_spectrum(self, start=0.1, stop=500e6, RBW='AUTO', NOP=401):
        """Configure the 4195 for spectrum analysis (noise here) with start, stop, sweep type and resolution.
        Configures the instrument for spectrum measurement mode via SCPI
        commands.
        Configures the instrument for spectrum measurement mode via SCPI
        commands.

        Applies the specified configuration to the object or hardware.

        Args:
            NOP: Nop to use.
            RBW: Rbw to use.
            start: Start bit position.
            stop: If True, send stop condition.
        """
        self.get_interface().write(("RST"))
        self.get_interface().write(("FNC2"))  # set Spectrum
        self.get_interface().write((f"START={start}"))  # start freq
        self.get_interface().write((f"STOP={stop}"))  # stop freq
        if RBW == 'AUTO':
            self.get_interface().write(('CPL1'))
        else:
            self.get_interface().write((f"RBW={RBW}"))  # resolution bandwidth
        self.get_interface().write((f"NOP={NOP}"))  # number of points in sweet
        self.get_interface().write(("SWT2"))  # log sweep
        self.get_interface().write(("SAP6"))  # uv/rthz
        self.get_interface().write(("SWM2"))  # singletrigger mode

    def trigger(self):
        """Return the sweep time and trigger once.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The trigger result.
        """
        ttime = self.get_interface().ask(('ST?'))
        self.get_interface().write(('SWTRG'))
        return ttime
