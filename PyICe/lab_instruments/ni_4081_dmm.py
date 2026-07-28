from PyICe.lab_core import *
import nidmm

class pxie_4081(instrument):
    def __init__(self, resource_name: str):
        self._base_name = "PXI-4081_DMM"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")
        self.session = nidmm.Session(resource_name=resource_name, reset_device=True)

    def config_dc_voltage(self, channel_name: str) -> None:
        self.session.configure_measurement_digits(measurement_function=nidmm.Function.DC_VOLTS, range=-1, resolution_digits=5.5)
        self.session.aperture_time = -1.0
        self.session.auto_zero = nidmm.AutoZero.ONCE
        self.setup_channel(channel_name)

    def config_dc_current(self, channel_name: str) -> None:
        self.session.configure_measurement_digits(measurement_function=nidmm.Function.DC_CURRENT, range=-1, resolution_digits=5.5)
        self.session.aperture_time = -1.0
        self.session.auto_zero = nidmm.AutoZero.ONCE
        self.setup_channel(channel_name)

    def get_measurement_function(self) -> str | None:
        if self.session.function == nidmm.Function.DC_VOLTS:
            return "DC_VOLTS"
        elif self.session.function == nidmm.Function.DC_CURRENT:
            return "DC_CURRENT"
        return None

    def get_measurement(self) -> float:
        """ Unit depends on the meter configuration."""
        return float(self.session.read())

    def set_nplc(self, value: float) -> None:
        self.session.aperture_time_units = nidmm.ApertureTimeUnits.POWER_LINE_CYCLES
        self.session.aperture_time = value

    def get_nplc(self) -> float:
        return self.session.aperture_time

    def set_digits(self, value: float) -> None:
        self.session.resolution_digits = value

    def get_digits(self) -> float:
        return self.session.resolution_digits

    def set_range(self, value: str | float) -> None:
        if value == 'AUTO':
            self.session.range = -1.0
        else:
            self.session.range = value

    def get_range(self) -> str | float:
        if self.session.range == -1.0:
            return 'AUTO'
        return self.session.auto_range_value

    """ Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # """
    def setup_channel(self, channel_name: str) -> None:
        self.add_channel(channel_name)
        self.add_channel_nplc(channel_name)
        self.add_channel_digits(channel_name)
        self.add_channel_range(channel_name)
        self.add_channel_range_readback(channel_name)

    def add_channel(self, channel_name: str) -> channel:
        new_channel = channel(channel_name, read_function=lambda: self.get_measurement())
        self._add_channel(new_channel)
        return new_channel

    def add_channel_nplc(self, channel_name: str) -> channel:
        new_channel = channel(f"{channel_name}_nplc", write_function = lambda value: self.set_nplc(value))
        new_channel.set_min_write_limit(0.000033)
        new_channel.set_max_write_limit(600)
        new_channel._set_value(self.get_nplc())
        self._add_channel(new_channel)
        return new_channel

    def add_channel_digits(self, channel_name: str) -> channel:
        new_channel = channel(f"{channel_name}_digits", write_function=lambda value: self.set_digits(value))
        new_channel.add_preset(3.5, "")
        new_channel.add_preset(4.5, "")
        new_channel.add_preset(5.5, "")
        new_channel.add_preset(6.5, "")
        new_channel.add_preset(7.5, "")
        new_channel._set_value(self.get_digits())
        self._add_channel(new_channel)
        return new_channel

    def add_channel_range(self, channel_name: str) -> channel:
        new_channel = channel(f"{channel_name}_range", write_function=lambda value: self.set_range(value))
        new_channel.add_preset("AUTO", "")
        meas_function: str = self.get_measurement_function()
        if meas_function =='DC_VOLTS':
            dc_volts_ranges: tuple[float, ...]  = (0.1, 1.0, 10.0, 100.0, 1000.0)
            for dc_volts_range in dc_volts_ranges:
                new_channel.add_preset(dc_volts_range, "")
        elif meas_function =='DC_CURRENT':
            dc_current_ranges: tuple[float, ...]  = (0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1.0, 3.0)
            for dc_current_range in dc_current_ranges:
                new_channel.add_preset(dc_current_range, "")
        new_channel._set_value(self.get_range())
        self._add_channel(new_channel)
        return new_channel

    def add_channel_range_readback(self, channel_name: str) -> channel:
        new_channel = channel(f"{channel_name}_range_readback", read_function=lambda: self.get_range())
        self._add_channel(new_channel)
        return new_channel

    def __del__(self):
        """ This ensures your class cleans up explicitly.
            Prevents the driver’s background cleanup from firing at exit."""
        try:
            self.session.close()
        except Exception:
            pass

if __name__ == "__main__":
    channels = master()
    dmm = pxie_4081(resource_name="PXI1Slot6")
    print(f"Model: {dmm.session.instrument_model}")
    channels.add(dmm)
    dmm.config_dc_voltage("v_meas")
    # dmm.config_dc_current("i_meas")
    breakpoint()
    dmm.__del__()




