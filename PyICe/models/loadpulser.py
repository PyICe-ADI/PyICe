try:
    import scipy
except ImportError as e:
    print("Warning: NumPy,SciPy import failed.")
    print(e)

def loadpulser():
    '''This returns a function which can be called with any input voltage from 0 to 3V and will put out 0 to 3.2A.
    There is a dead zoe up to about 1.3V which may make this difficult for a servo instrument to deal with.
    It's based on an LTSPICE simulation of an FMMT617 NPN and 100m Ohm resistor.
    The base is loaded with 50 Ohms and the source voltage is assumed to be on the upstream of 50 Ohms of source impedance or in other words the open circuit voltage.
    The schematic can be found in the Kicad repo for the Stowe base Board under Docs.'''
    
    xpoints= [0.000000000000000e+00,5.000000000000000e-02,1.000000000000000e-01,1.500000000000000e-01,2.000000000000000e-01,2.500000000000000e-01,3.000000000000000e-01,3.500000000000000e-01,4.000000000000000e-01,4.500000000000000e-01,4.999999999999999e-01,5.499999999999999e-01,6.000000000000000e-01,6.500000000000000e-01,7.000000000000001e-01,7.500000000000001e-01,8.000000000000002e-01,8.500000000000002e-01,9.000000000000002e-01,9.500000000000003e-01,1.000000000000000e+00,1.050000000000000e+00,1.100000000000000e+00,1.150000000000000e+00,1.200000000000000e+00,1.250000000000000e+00,1.300000000000000e+00,1.350000000000001e+00,1.400000000000001e+00,1.450000000000001e+00,1.500000000000001e+00,1.550000000000001e+00,1.600000000000001e+00,1.650000000000001e+00,1.700000000000001e+00,1.750000000000001e+00,1.800000000000001e+00,1.850000000000001e+00,1.900000000000001e+00,1.950000000000001e+00,2.000000000000001e+00,2.050000000000001e+00,2.100000000000001e+00,2.150000000000000e+00,2.200000000000000e+00,2.250000000000000e+00,2.300000000000000e+00,2.350000000000000e+00,2.399999999999999e+00,2.449999999999999e+00,2.499999999999999e+00,2.549999999999999e+00,2.599999999999999e+00,2.649999999999999e+00,2.699999999999998e+00,2.749999999999998e+00,2.799999999999998e+00,2.849999999999998e+00,2.899999999999998e+00,2.949999999999998e+00,3.000000000000000e+00]

    ypoints=[1.733724e-12,2.131628e-12,4.305889e-12,9.364953e-12,2.272316e-11,5.796608e-11,1.509619e-10,3.962271e-10,1.043020e-09,2.748649e-09,7.246271e-09,1.910604e-08,5.037829e-08,1.328367e-07,3.502583e-07,9.235309e-07,2.435028e-06,6.420080e-06,1.692571e-05,4.461575e-05,1.175637e-04,3.095035e-04,8.129312e-04,2.122621e-03,5.460783e-03,1.356676e-02,3.143824e-02,6.498056e-02,1.171613e-01,1.862191e-01,2.680880e-01,3.586993e-01,4.555995e-01,5.564765e-01,6.599367e-01,7.650474e-01,8.711467e-01,9.777599e-01,1.084542e+00,1.191240e+00,1.297666e+00,1.403678e+00,1.509170e+00,1.614062e+00,1.718296e+00,1.821825e+00,1.924619e+00,2.026652e+00,2.127910e+00,2.228382e+00,2.328061e+00,2.426947e+00,2.525038e+00,2.622339e+00,2.718854e+00,2.814590e+00,2.909552e+00,3.003750e+00,3.097192e+00,3.189886e+00,3.281839e+00]
    
    rms_error = 1e-6
    point_count = len(xpoints)
    rss = rms_error * point_count**0.5
    return scipy.interpolate.UnivariateSpline(x=xpoints, y=ypoints, s=rss)

if __name__=='__main__':
    from PyICe import lab_utils, LTC_plot
    pulser = loadpulser()
    data = []
    for x in lab_utils.floatRangeInc(0,3, 0.005):
        data.append([x, pulser(x)])
    
    G0 = LTC_plot.plot( plot_title ="DC Transfer Function of\nLoad Pulser",
                    plot_name   = "",
                    xaxis_label = "INPUT VOLTAGE (V)",
                    yaxis_label = "PULSE CURRENT (A)",
                    xlims       = (0, 3),
                    ylims       = (0, 3.2),
                    xminor      = 0,
                    xdivs       = 6,
                    yminor      = 0,
                    ydivs       = 8,
                    logx        = False,
                    logy        = False)
                    
    G0.add_trace(   axis        = 1,
                    data        = data,
                    color       = LTC_plot.LT_RED_1,
                    marker      = '.',
                    markersize  = 0,
                    legend      = "")

    Page = LTC_plot.Page(plot_count=1)
    Page.add_plot(G0)
    Page.create_svg(file_basename="load_pulser")