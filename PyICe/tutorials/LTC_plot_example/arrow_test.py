from PyICe import LTC_plot
from PyICe.lab_utils.ranges import floatRangeInc
from numpy import pi, sin, cos

points = []
for t in floatRangeInc(0, 2*pi, 0.01):
    x = 16*(sin(t))**3
    y = 13*cos(t)-5*cos(2*t)-2*cos(3*t)-cos(4*t)
    points.append([x,y])

G0 = LTC_plot.plot( plot_title      = "I♥U",
                    plot_name       = "I♥U",
                    xaxis_label     = "I♥U",
                    yaxis_label     = "I♥U",
                    xlims           = (-18,18),
                    ylims           = (-18,14),
                    xminor          = 0,
                    xdivs           = 9,
                    yminor          = 0,
                    ydivs           = 8,
                    logx            = False,
                    logy            = False)

G0.add_trace(   axis            = 1,
                data            = points,
                color           = LTC_plot.LT_RED_1,
                marker          = "",
                markersize      = 0,
                linestyle       = "-",
                legend          = "")
              
for arrow in points:
    G0.add_arrow(text="I♥U", text_location=(0,-2.54), arrow_tip=(arrow), use_axes_scale=True, fontsize=7)

Page1 = LTC_plot.Page(rows_x_cols=(1, 1), page_size=None)
Page1.add_plot(G0, position = 1)
Page1.create_svg(file_basename = "Arrow Test")
Page1.create_pdf(file_basename = "Arrow Test")
