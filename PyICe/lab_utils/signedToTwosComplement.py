"""Signed To Twos Complement utility."""
def signedToTwosComplement(signed, bitCount):
    """Take python int and convert to two's complement representation using specified number of bits.

    >>> signedToTwosComplement(5, 8)
    5
    >>> signedToTwosComplement(-1, 8)
    255
    >>> signedToTwosComplement(-128, 8)
    128

    Args:
        bitCount: Bitcount.
        signed: If True, interpret as signed value.

    Returns:
        Result value.
    """
    assert signed < 2**(bitCount - 1)
    assert signed >= -1 * 2**(bitCount - 1)
    if signed < 0:
        signed += 2**bitCount
        signed &= 2**bitCount - 1
    return signed
