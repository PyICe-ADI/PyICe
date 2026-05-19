"""Tests for thermostream."""
import visa
from lab import instrument
import time

# single channel temptronic_4310 thermostream
# add_channel doesnt take a name/number for the channel
# special methods: set_window(air_window), set_soak(soak_time), flow_off(), wait_settle()
# use wait_settle to wait for the soak to complete
# defaults to window = 3, soak=30
# extra data
#   _sense - the sensed temperature
#   _window - the temperature window
#   _time - the total settling time (including soak)
#   _soak - the programmed soak time


class temptronic_4310(instrument):
    """Temptronic_4310 (instrument subclass)."""
    def __init__(self, addr):
        """Initialize temptronic_4310.

        Args:
            addr: Addr.
        """
        instrument.__init__(self, addr)
        self.instrument = visa.instrument(addr)
        self.channels = []
        self.setpoint = 25
        self.soak = 30
        self.window = 3
        self.time = 0
        self.name = "temptronic_4310 @ " + str(addr)
        self.intrument.write("DUTM 1")

    def add_channel(self, name):
        """Add a channel.

        Args:
            name: Name identifier.
        """
        self.channels.append(name)

    def write_channel(self, name, value):
        """Perform write channel operation.

        Args:
            name: Name identifier.
            value: Value to set.
        """
        self.setpoint = value
        txt = "SETP " + str(self.setpoint) + ";WNDW " + \
            str(self.window) + "; SOAK " + str(self.soak)
        self.instrument.write(txt)
        self.instrumnet.write("FLOW 1")
        self.instrumnet.write("COOL 1")
        self.time = 0

    def set_window(self, value):
        """Set the window.

        Args:
            value: Value to set.
        """
        self.window = value
        txt = "WNDW " + str(self.window)
        self.instrument.write(txt)

    def set_soak(self, value):
        """Set the soak.

        Args:
            value: Value to set.
        """
        self.soak = value
        txt = "SOAK " + str(self.soak)
        self.instrument.write(txt)

    def off(self):
        """Perform off operation."""
        self.instrument.write("FLOW 0")
        self.instrument.write("HEAD 0")
        self.instrument.write("COOL 0")

    def wait_settle(self):
        """Perform wait settle operation."""
        settled = False
        while not settled:
            time.sleep(.5)
            self.time += .5
            print(("Waiting To Settle: " + str(self.time)))
            tecr = self.instrument.ask("TECR?")
            if (tecr & 1):
                settled = True

    def read_channel(self, name):
        """Return read channel result.

        Args:
            name: Name identifier.

        Returns:
            Result value.
        """
        return self.setpoint

    def read_channels(self):
        """Return read channels result.

        Returns:
            Result value.
        """
        results = {}
        for channel in self.channels:
            results[channel] = self.read_channel(channel)
            results[channel + "_sense_dut"] = self.instrument.ask("TMPD?")
            results[channel + "_sense_air"] = self.instrument.ask("TMPA?")
            results[channel + "_soak"] = self.soak
            results[channel + "_window"] = self.window
            results[channel + "_time"] = self.time
        return results


if __name__ == "__main__":
    t = temptronic_4310("GPIB0::24")
    t.add_channel("t")
    t.write_channel(0)
    t.wait_settle()
    print(t.read_channel("t"))
    print((t.read_channel("t")))
    t.off()
