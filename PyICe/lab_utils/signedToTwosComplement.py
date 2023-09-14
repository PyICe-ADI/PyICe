def signedToTwosComplement(signed, bitCount):
    '''take python int and convert to two's complement representation using specified number of bits'''
    assert signed < 2**(bitCount-1)
    assert signed >= -1 * 2**(bitCount-1)
    if signed < 0:
        signed += 2**bitCount
        signed &= 2**bitCount-1
    return signed