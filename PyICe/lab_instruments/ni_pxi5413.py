"""Ni pxi5413 instrument driver.

>>> from PyICe.lab_instruments.ni_pxi5413 import ni_pxi5413

"""
from ..lab_core import *  # noqa: F403

import math
import numpy as np  # pylint: disable=E0401; numpy is an optional dependency required only when using NI PXI hardware
import nifgen  # pylint: disable=E0401; nifgen is an optional NI hardware-specific dependency
import time


class ni_pxi5413(scpi_instrument, delegator):
    """NI PXI5413 16bit 20MHz AWG."""

    def __init__(self, interface_visa, force_trigger=True):
        """interface_visa e.g. PXI1SLOT2".
        Stores configuration in ``_base_name``, ``force_trigger`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            force_trigger: If True, force an immediate trigger.
            interface_visa: VISA interface instance.
        """
        self._base_name = 'NI_PXI5413'
        delegator.__init__(self)
        scpi_instrument.__init__(self, f"NI_PXI5413 @ {interface_visa}")
        self.add_interface_visa(interface_visa, timeout=10)
        self.force_trigger = force_trigger

    # TODO - need to modify methods into PyICe fashion

    @staticmethod
    def create_trapzoid_signal(SampleN, width, slope, VOH, VOL, period):
        # function to generate custom pulse
        """Return create trapzoid signal result.
        Creates and returns a new trapzoid signal.

        Supports the ``ni_pxi5413`` workflow by performing the described operation.

        Args:
            SampleN: Number of samples.
            VOH: Voh to use.
            VOL: Vol to use.
            period: Signal period.
            slope: Trigger slope (rising or falling).
            width: Width in characters or pixels.

        Returns:
            The create trapzoid signal result.
        """
        t = np.linspace(0, period, SampleN)
        amp = VOH - VOL
        offset = VOL
        a = slope * width * signal.sawtooth(2 * math.pi * t / width, width=0.5) / 4.  # pylint: disable=E0602; signal (scipy.signal) is an optional dependency not imported at module level - this is incomplete/WIP code per the TODO above  # noqa: E501  # pyright: ignore[reportUndefinedVariable]
        a += slope * width / 4.
        # clamp the top of the waveform
        a[a > amp] = amp
        # slice the pt
        idx_endpt = math.ceil(width / period * len(t))
        a[idx_endpt:] = 0
        waveform_data = a + offset
        return waveform_data

    @staticmethod
    def main_method(resource_name, options, samples, gain, offset, gen_time):
        """Perform main method operation.

        Supports the ``ni_pxi5413`` workflow by performing the described operation.

        Args:
            resource_name: NI resource name.
            gain: Gain value.
            gen_time: Gen time to use.
            offset: Offset value.
            options: Options to use.
            samples: Number of samples to acquire.
        """
        waveform_data = create_waveform_data(samples)  # noqa: F821  # pylint: disable=E0602; create_waveform_data is undefined - this is incomplete/WIP code per the TODO above  # pyright: ignore[reportUndefinedVariable]
        # gen_time = period
        with nifgen.Session(resource_name=resource_name, options=options) as session:
            session.output_mode = nifgen.OutputMode.ARB
            waveform = session.create_waveform(
                waveform_data_array=waveform_data)
            session.configure_arb_waveform(
                waveform_handle=waveform, gain=gain, offset=offset)
            with session.initiate():
                time.sleep(gen_time)
