from math import log10

def IEC61967_2_uppercase(uppercase, frequency):
    '''This is the 0dB top horizontal set of lines in the IEC Emission Characterization Levels
       "uppercase" is the uppercase index of the top line we want to trace out
       "frequency" is the frequency of interest.
       the value returned is the dBV value of the emission result'''
    letters = "ABCDEFGHIKLMNO" # No J !!!
    values = {}
    top = 84
    for letter in letters:
        values[letter] = top
        top -= 6#dBV between curves
    return values[uppercase]

def IEC61967_2_digit(digit, frequency):
    '''This is the -20dB/decade set of numbered curves in the IEC Emission Characterization Levels
       "digit" is the digit number of the curve we want to trace out
       "frequency" is the frequency of interest.
       the value returned is the dBV value of the emission result'''
    digit=int(digit) # accepts string or integer
    MHZreflevels = {}
    for index_level in range(1, 20):
        MHZreflevels[digit] = (20-digit) * 6#dBV between curves
    return MHZreflevels[digit] - 20 * (log10(frequency)-log10(1e6))
    
def IEC61967_2_lowercase(lowercase, frequency):
    '''This is the -40dB/decade set of curves in the IEC Emission Characterization Levels
       "lowercase" is the lowercase index of the curve we want to trace out
       "frequency" is the frequency of interest.
       the value returned is the dBV value of the emission result'''
    letters = "abcdefghiklmnopqrstuvwyz"
    MHZreflevels = {}
    top = 150
    for letter in letters:
        MHZreflevels[letter] = top
        top -= 6#dBV between curves
    return MHZreflevels[lowercase] - 40 * (log10(frequency)-log10(1e6))