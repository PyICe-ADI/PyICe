"""Sign Extend utility."""
from .signedToTwosComplement import signedToTwosComplement
from .twosComplementToSigned import twosComplementToSigned


def signExtend(binary, inBitCount, outBitCount):
    """Widen a two's complement value from inBitCount to outBitCount bits.

    Preserves the signed value by decoding from the source width and
    re-encoding at the target width. Used when a narrow ADC result must be
    placed into a wider register or data field.

    >>> signExtend(5, 8, 16)
    5
    >>> signExtend(0xFF, 8, 16)
    65535
    >>> signExtend(0b1000, 4, 8)
    248
    >>> signExtend(0b0111, 4, 8)
    7

    Args:
        binary: Unsigned integer in two's complement at the source width.
        inBitCount: Number of bits in the source value.
        outBitCount: Number of bits in the target (must be >= inBitCount).
    """
    return signedToTwosComplement(
        twosComplementToSigned(binary, inBitCount), outBitCount)
