from PyICe import LTC_plot, lab_utils
from numpy import e, pi

u = 0
s = 1
pdf = []
xvalues = lab_utils.floatRangeInc(-6, 6, 0.001)

for x in xvalues:
    # pdf.append(1/s/(2*pi)**0.5 * e**(-0.5*((x-u)/s)**2))
    pdf.append(e**(-0.5*((x-u)/s)**2)) # Normailzed to 1
    
G0 = LTC_plot.plot(     plot_title      = "",
                        plot_name       = "",
                        xaxis_label     = "X",
                        yaxis_label     = "PDF",
                        xlims           = (-6, 6),
                        ylims           = (0, 1),
                        xminor          = 1,
                        xdivs           = 12,
                        yminor          = 2,
                        ydivs           = 5,
                        logx            = False,
                        logy            = False)

G0.add_trace(           axis            = 1,
                        data            = list(zip(xvalues, pdf)),
                        color           = LTC_plot.LT_RED_1,
                        marker          = "",
                        markersize      = 0,
                        linestyle       = "-",
                        legend          = "")
                        
G1 = LTC_plot.plot(     plot_title      = "",
                        plot_name       = "",
                        xaxis_label     = "X",
                        yaxis_label     = "PDF",
                        xlims           = (-6, 6),
                        ylims           = (1e-7, 1),
                        xminor          = 1,
                        xdivs           = 12,
                        yminor          = 1,
                        ydivs           = 5,
                        logx            = False,
                        logy            = True)

G1.add_trace(           axis            = 1,
                        data            = list(zip(xvalues, pdf)),
                        color           = LTC_plot.LT_RED_1,
                        marker          = "",
                        markersize      = 0,
                        linestyle       = "-",
                        legend          = "")

Page1 = LTC_plot.Page(rows_x_cols=(1, 2), page_size=None)
Page1.add_plot(G0, position = 1)
Page1.add_plot(G1, position = 2)
Page1.create_svg(file_basename = "Gaussian")
Page1.create_pdf(file_basename = "Gaussian")
