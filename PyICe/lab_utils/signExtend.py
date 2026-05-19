from .signedToTwosComplement import signedToTwosComplement
from .twosComplementToSigned import twosComplementToSigned


def signExtend(binary, inBitCount, outBitCount):
    """Change width of two's complement binary number.

    >>> signExtend(5, 8, 16)
    5
    >>> signExtend(0xFF, 8, 16)
    65535
    >>> signExtend(0b1000, 4, 8)
    248

    Args:
        binary: Binary/integer data.
        inBitCount: Inbitcount.
        outBitCount: Outbitcount.

    Returns:
        Result value.
    """
    return signedToTwosComplement(
        twosComplementToSigned(binary, inBitCount), outBitCount)
