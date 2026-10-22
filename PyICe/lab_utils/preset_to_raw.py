"""Preset To Raw utility.

>>> from PyICe.lab_utils.preset_to_raw import preset_to_raw

"""
import numbers
from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement

# REVISIT #252: signedness is not yet an intrinsic integer_channel property, so
# callers pass `signed` and non-negative values on signed fields are accepted
# as raw bit patterns.  Re-check this contract when #252 lands.


def preset_to_raw(value, bitCount, signed=False):
    """Convert a preset or enumerated value to the raw bit pattern a channel writes.

    ``integer_channel`` presets bypass formats, so a preset must already be the
    raw unsigned bit pattern of the field.  If ``signed`` is true and ``value``
    is negative, it is encoded in two's complement.  The result must fit in
    ``0..2**bitCount - 1`` (the ``twi_interface.check_size`` rule).

    >>> preset_to_raw(0, 4)
    0
    >>> preset_to_raw(15, 4)
    15
    >>> preset_to_raw(16, 4)
    Traceback (most recent call last):
        ...
    ValueError: Data value 0x10 exceeds 4-bit range (max 0xF)
    >>> preset_to_raw(-1, 4)
    Traceback (most recent call last):
        ...
    ValueError: Data value -1 is negative (must be 0..15)
    >>> preset_to_raw(-1, 4, signed=True)
    15
    >>> preset_to_raw(-8, 4, signed=True)
    8
    >>> preset_to_raw(-9, 4, signed=True)
    Traceback (most recent call last):
        ...
    ValueError: signed value -9 is below 4-bit signed range (min -8)
    >>> preset_to_raw(15, 4, signed=True)
    15
    >>> preset_to_raw(True, 1)
    1
    >>> preset_to_raw(None, 4)
    Traceback (most recent call last):
        ...
    TypeError: Preset value must be an integer, got NoneType

    Args:
        value: Integer preset or enumerated value.
        bitCount: Bit width of the channel.
        signed: If True, a negative value is encoded in two's complement.
            Non-negative values are treated as raw bit patterns either way.

    Returns:
        int: Raw bit pattern in ``0..2**bitCount - 1``.

    Raises:
        TypeError: If value or bitCount is not an integer.
        ValueError: If bitCount is less than 1, or value does not fit in
            bitCount bits.
    """
    if not isinstance(value, numbers.Integral):
        raise TypeError(
            f'Preset value must be an integer, got {type(value).__name__}')
    if not isinstance(bitCount, numbers.Integral):
        raise TypeError(
            f'bitCount must be an integer, got {type(bitCount).__name__}')
    if bitCount < 1:
        raise ValueError(
            f'bitCount {bitCount} is below minimum (min 1)')
    raw = int(value)
    if signed and raw < 0:
        raw = signedToTwosComplement(raw, bitCount)
    if raw < 0:
        raise ValueError(f'Data value {raw} is negative (must be 0..{2**bitCount - 1})')
    if raw >= 2**bitCount:
        raise ValueError(
            f'Data value 0x{raw:X} exceeds {bitCount}-bit range '
            f'(max 0x{2**bitCount - 1:X})')
    return raw
