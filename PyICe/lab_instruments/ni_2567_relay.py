""" NI PXI-2567 64-Channel PXI Relay Driver Module instrument driver.

>>> from PyICe.lab_instruments.ni_2567_relay import pxi_2567

"""
import niswitch
from PyICe.lab_core import instrument, channel


class pxi_2567(instrument):
    def __init__(self, resource_name):
        self._base_name = "PXI-2567_RELAY"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")
        self.session = niswitch.Session(
            resource_name=resource_name,
            topology="2567/Independent",
            reset_device=True
        )

    def set_relay_status(self, channel_num, value):
        if value in ('CLOSED', 1):
            self.session.relay_control(
                relay_name=f"k{channel_num}",
                relay_action=niswitch.RelayAction.CLOSE
            )
        else:
            self.session.relay_control(
                relay_name=f"k{channel_num}",
                relay_action=niswitch.RelayAction.OPEN
            )

    def get_relay_status(self, channel_num):
        position = self.session.get_relay_position(f"k{channel_num}")
        return position.name

    def add_channel_relay(self, channel_name, channel_number):
        new_channel = channel(
            channel_name,
            write_function=lambda value: self.set_relay_status(
                channel_number,
                value
            )
        )
        new_channel.add_preset("OPEN", "")
        new_channel.add_preset("CLOSED", "")
        new_channel._set_value(self.get_relay_status(channel_number))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_relay_readback(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_readback",
            read_function=lambda: self.get_relay_status(channel_number)
        )
        self._add_channel(new_channel)
        return new_channel