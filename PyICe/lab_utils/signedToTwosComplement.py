"""Signed To Twos Complement utility.

>>> from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement

"""
def signedToTwosComplement(signed, bitCount):
    """Encode a signed Python int as an unsigned two's complement integer.

    Used when writing signed values to hardware registers that store them in
    two's complement format (e.g., DAC offset codes, temperature sensor readings).

    >>> signedToTwosComplement(5, 8)
    5
    >>> signedToTwosComplement(-1, 8)
    255
    >>> signedToTwosComplement(-128, 8)
    128
    >>> signedToTwosComplement(0, 16)
    0
    >>> signedToTwosComplement(-1, 16)
    65535
    >>> signedToTwosComplement(127, 8)
    127
    >>> signedToTwosComplement(128, 8)
    Traceback (most recent call last):
        ...
    ValueError: signed value 128 exceeds 8-bit signed range (max 127)
    >>> signedToTwosComplement(-129, 8)
    Traceback (most recent call last):
        ...
    ValueError: signed value -129 is below 8-bit signed range (min -128)

    Args:
        signed: Signed integer value within the representable range for bitCount.
        bitCount: Number of bits in the target register.

    Raises:
        ValueError: If signed is outside the bitCount signed range.
    """
    if signed >= 2**(bitCount - 1):
        raise ValueError(
            f'signed value {signed} exceeds {bitCount}-bit signed range (max {2**(bitCount - 1) - 1})')
    if signed < -2**(bitCount - 1):
        raise ValueError(
            f'signed value {signed} is below {bitCount}-bit signed range (min {-2**(bitCount - 1)})')
    if signed < 0:
        signed += 2**bitCount
        signed &= 2**bitCount - 1
    return signed
