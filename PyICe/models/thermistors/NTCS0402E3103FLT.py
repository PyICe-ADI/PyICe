from scipy import interpolate

class NTCS0402E3103FLT():
    def __init__(self):
        self.temps = [-40,-34,-28,-21,-14,-6,4,33,44,53,62,70,78,86,94,102,110,118,126,134,142,150]
        self.values = [214063.67,152840.30,110480.73,76798.02,54214.99,37075.65,23649.71,7400.97,5001.22,3693.55,2768.21,2167.17,1714.08,1368.87,1103.18,896.73,734.86,606.86,504.80,422.81,356.45,302.36]
        self.NTCS0402E3103FLT_func = interpolate.InterpolatedUnivariateSpline(self.temps, self.values)
        self.NTCS0402E3103FLT_reverse_func = interpolate.InterpolatedUnivariateSpline(list(reversed(self.values)), list(reversed(self.temps)))

    def r_from_tdegc_func(self):
        '''Returns a callable function that can be passed a temperature and will return the corresponding resistance.'''
        return self.NTCS0402E3103FLT_func
    
    def r_from_tdegc(self, tdegc):
        '''Returns a single resistance value for a given temperature value.'''
        return self.NTCS0402E3103FLT_func(tdegc)
        
    def tdegc_from_r_func(self):
        '''Returns a callable function that can be passed a resistance and will return the corresponding temperature.'''
        return self.NTCS0402E3103FLT_reverse_func
    
    def tdegc_from_r(self, r):
        '''Returns a single temperature value for a given resistance value.'''
        return self.NTCS0402E3103FLT_reverse_func(r)
        
    def voltage_ratio_from_tdegc(self, rbias, tdegc):
       '''Returns a single value of the voltage ratio of this thermistor grounded with a bias resistor feeding it.'''
       rthermistor = self.r_from_tdegc(tdegc)
       return rthermistor / ( rthermistor + rbias )
       
    def tdegc_from_voltage_ratio(self, rbias, ratio):
       '''Returns a single value of the temperature ratio of this thermistor grounded with a bias resistor feeding it.'''
       rthermistor = rbias * ratio / ( 1 - ratio )
       return self.tdegc_from_r(rthermistor)