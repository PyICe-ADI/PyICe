def signExtend(binary, inBitCount, outBitCount):
    '''change width of two's complement binary number'''
    return signedToTwosComplement(twosComplementToSigned(binary, inBitCount), outBitCount)