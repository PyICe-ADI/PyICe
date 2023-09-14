def swap_endian(word, elementCount, elementSize=8):
    '''reverse endianness of multi-byte word
    elementCount is number of bytes, or other atomic memory block if not of elementSize 8 bits

    to reverse bit order, set elementCount to the number of bits and set elementSize to 1.'''
    assert word < 2**(elementSize*elementCount)
    assert word >= 0
    reversed = 0x00
    mask = 2**elementSize-1
    while elementCount > 0:
        reversed ^= (word & mask) << (elementSize*(elementCount-1))
        word = word >> elementSize
        elementCount -= 1
    return reversed