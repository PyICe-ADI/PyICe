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

    Args:
        signed: Signed integer value within the representable range for bitCount.
        bitCount: Number of bits in the target register.
    """
    assert signed < 2**(bitCount - 1)
    assert signed >= -1 * 2**(bitCount - 1)
    if signed < 0:
        signed += 2**bitCount
        signed &= 2**bitCount - 1
    return signed
