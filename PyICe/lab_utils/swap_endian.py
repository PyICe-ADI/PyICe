"""Swap endian utility.

>>> from PyICe.lab_utils.swap_endian import swap_endian

"""
def swap_endian(word, elementCount, elementSize=8):
    """Reverse the order of fixed-size elements within an integer word.

    Typically used to byte-swap register values read from I2C/SPI devices that
    use big-endian format when the host is little-endian (or vice versa). Can
    also reverse bit order by setting elementSize=1.

    >>> hex(swap_endian(0xABCD, 2))
    '0xcdab'
    >>> hex(swap_endian(0x123456, 3))
    '0x563412'
    >>> bin(swap_endian(0b1100, 4, elementSize=1))
    '0b11'
    >>> hex(swap_endian(0xDEADBEEF, 4))
    '0xefbeadde'

    Args:
        word: Integer value to rearrange.
        elementCount: Number of elements (e.g., 2 for a 16-bit word of bytes).
        elementSize: Bits per element (default 8 for byte-swap; use 1 for
            bit-reversal).
    """
    assert word < 2**(elementSize * elementCount)
    assert word >= 0
    reversed = 0x00
    mask = 2**elementSize - 1
    while elementCount > 0:
        reversed ^= (word & mask) << (elementSize * (elementCount - 1))
        word = word >> elementSize
        elementCount -= 1
    return reversed
