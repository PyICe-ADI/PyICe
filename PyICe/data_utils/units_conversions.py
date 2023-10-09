import numpy

def dBV(voltageRMS):
    return 20 * numpy.log10(voltageRMS)

def dBm(voltageRMS):
    return 10 * numpy.log10(voltageRMS**2/50/0.001)

def Vpp_to_VRMS(Vpp):
    return Vpp/2/2**0.5

def VRMS_to_Vpp(VRMS):
    return VRMS*2*2**0.5