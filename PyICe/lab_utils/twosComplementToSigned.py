"""Twos Complement To Signed utility."""
def twosComplementToSigned(binary, bitCount):
    """Decode an unsigned two's complement register value into a signed Python int.

    The inverse of signedToTwosComplement. Used when reading hardware registers
    that store signed quantities (e.g., ADC output codes, temperature readings).

    >>> twosComplementToSigned(5, 8)
    5
    >>> twosComplementToSigned(255, 8)
    -1
    >>> twosComplementToSigned(128, 8)
    -128
    >>> twosComplementToSigned(0, 16)
    0
    >>> twosComplementToSigned(0xFFFF, 16)
    -1

    Args:
        binary: Unsigned integer read from hardware (0 to 2**bitCount - 1).
        bitCount: Number of bits in the source register.

    Raises:
        ValueError: If binary is negative or exceeds the bitCount range.
    """
    if binary >= 2**bitCount:
        raise ValueError(
            f'binary value {binary} exceeds {bitCount}-bit range (max {2**bitCount - 1})')
    if binary < 0:
        raise ValueError(
            f'binary value {binary} is negative; twos complement input must be unsigned')
    if binary >= 2**(bitCount - 1):
        binary -= 2**bitCount
    return binary
