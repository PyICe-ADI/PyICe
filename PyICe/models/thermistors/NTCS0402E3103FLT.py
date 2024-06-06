from scipy import interpolate

class NTCS0402E3103FLT():
    def __init__(self):
        self.temps = [-40,-34,-28,-21,-14,-6 ,4  ,33 ,44 ,53 ,62 ,70 ,78 ,86 ,94 ,102,110,118,126,134,142,150]
        self.values = [214063.67,152840.30,110480.73,76798.02,54214.99,37075.65,23649.71,7400.97,5001.22,3693.55,2768.21,2167.17,1714.08,1368.87,1103.18,896.73,734.86,606.86,504.80,422.81,356.45,302.36]
        self.NTCS0402E3103FLT_func = interpolate.UnivariateSpline(self.temps, self.values)

    def R_from_Tc_func(self):
        '''Returns a callable function that can be passed a temperature and will return the corresponding resistance.'''
        return self.NTCS0402E3103FLT_func
    
    def R_from_Tc(self, Tc):
        '''Returns a single resistance value for a given temperature value.'''
        return self.NTCS0402E3103FLT_func(Tc)
        
    def voltage_ratio_from_Tc(self, Rbias, Tc):
       '''Returns a single value of the voltage ratio of this thermistor grounded with a bias resistor feeding it.'''
       rthermistor = R_from_Tc(Tc)
       return rthermistor / ( rthermistor + Rbias )