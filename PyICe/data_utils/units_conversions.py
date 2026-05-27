"""Units conversions utilities.

>>> from PyICe.data_utils.units_conversions import dBV

"""
import numpy


def dBV(voltageRMS):
    """Convert RMS voltage to dBV.

    Transforms the input data into the required output form.

    >>> float(dBV(1.0))
    0.0
    >>> float(round(dBV(0.1), 1))
    -20.0
    >>> float(dBV(0.0))
    -inf

    Args:
        voltageRMS: Voltagerms to use.

    Returns:
        The result of the operation.
    """
    with numpy.errstate(divide='ignore'):
        return 20 * numpy.log10(voltageRMS)


def dBm(voltageRMS):
    """Convert RMS voltage to decibel-milliwatts (50 ohm reference).

    Transforms the input data into the required output form.

    >>> float(round(dBm(1.0), 2))
    13.01
    >>> float(round(dBm(0.1), 2))
    -6.99

    Args:
        voltageRMS: Voltagerms to use.

    Returns:
        The result of the operation.
    """
    return 10 * numpy.log10(voltageRMS**2 / 50 / 0.001)


def Vpp_to_VRMS(Vpp):
    """Convert peak-to-peak voltage to RMS (sinusoidal).

    Transforms the input data into the required output form.

    >>> round(Vpp_to_VRMS(2.0), 4)
    0.7071
    >>> round(Vpp_to_VRMS(1.0), 4)
    0.3536

    Args:
        Vpp: Vpp to use.

    Returns:
        The result of the operation.
    """
    return Vpp / 2 / 2**0.5


def VRMS_to_Vpp(VRMS):
    """Convert RMS voltage to peak-to-peak (sinusoidal).

    Transforms the input data into the required output form.

    >>> round(VRMS_to_Vpp(0.7071), 3)
    2.0
    >>> round(VRMS_to_Vpp(1.0), 4)
    2.8284

    Args:
        VRMS: Vrms to use.

    Returns:
        The result of the operation.
    """
    return VRMS * 2 * 2**0.5
