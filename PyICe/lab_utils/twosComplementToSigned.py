"""Twos Complement To Signed utility."""
def twosComplementToSigned(binary, bitCount):
    """Take two's complement number with specified number of bits and convert to python int representation.

    >>> twosComplementToSigned(5, 8)
    5
    >>> twosComplementToSigned(255, 8)
    -1
    >>> twosComplementToSigned(128, 8)
    -128

    Args:
        binary: Binary/integer data.
        bitCount: Bitcount.

    Returns:
        Result value.

    Raises:
        ValueError: On error condition.
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
