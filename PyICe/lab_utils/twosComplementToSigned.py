def twosComplementToSigned(binary, bitCount):
    '''take two's complement number with specified number of bits and convert to python int representation

    >>> twosComplementToSigned(5, 8)
    5
    >>> twosComplementToSigned(255, 8)
    -1
    >>> twosComplementToSigned(128, 8)
    -128
    '''
    assert binary < 2**bitCount
    assert binary >= 0
    if binary >= 2**(bitCount-1):
        binary -= 2**bitCount
    return binary