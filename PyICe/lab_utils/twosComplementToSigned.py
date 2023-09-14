def twosComplementToSigned(binary, bitCount):
    '''take two's complement number with specified number of bits and convert to python int representation'''
    assert binary < 2**bitCount
    assert binary >= 0
    if binary >= 2**(bitCount-1):
        binary -= 2**bitCount
    return binary