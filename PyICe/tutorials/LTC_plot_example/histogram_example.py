from PyICe import LTC_plot
import numpy as np

mu = -0.11 # mean of distribution
sig = 0.022 # standard deviation of distribution
xdata1 = mu + sig * np.random.randn(194)
###################################################################
#   Creating a histogram                                          #
###################################################################
G18 = LTC_plot.plot(    plot_title      = "Closed Loop Servo Error",
                        plot_name       = "2975 G18",
                        xaxis_label     = "ERROR (%)",
                        yaxis_label     = "NUMBER OF PARTS",
                        xlims           = [-0.25, 0.25],
                        ylims           = [0, 80],
                        xminor          = 9,
                        xdivs           = 5,
                        yminor          = None,
                        ydivs           = 8,
                        logx            = False,
                        logy            = False)

G18.add_histogram(      axis            = 1,
                        xdata           = xdata1,
                        num_bins        = 5,
                        color           = LTC_plot.LT_BLUE_2_40PCT,
                        normed          = False,
                        legend          = "data1",
                        linewidth       = 0.5,
                        alpha           = None)
G18.add_note("194 PARTS SOLDERED DOWN", [-0.082, 74])
###################################################################
#   Creating a Solid histogram                                    #
###################################################################
mu = 32768 # mean of distribution
sig = 32.22 # standard deviation of distribution
xdata1 = mu + sig * np.random.randn(250000)

plot_name = "2905 G02"
G02 = LTC_plot.plot(             plot_title      = "DC Histogram",
                        plot_name       = plot_name,
                        xaxis_label     = "CODE",
                        yaxis_label     = "COUNTS",
                        xlims           = [mu - 2.0 * 80, mu + 2.0 * 80],
                        ylims           = [0, 10000],
                        xminor          = None,
                        xdivs           = 4,
                        yminor          = None,
                        ydivs           = 5,
                        logx            = False,
                        logy            = False)

G02.add_histogram(      axis            = 1,
                        xdata           = xdata1,
                        num_bins        = 100, 
                        color           = LTC_plot.LT_RED_1,
                        normed          = False,
                        legend          = "data1",
                        linewidth       = 0.001,
                        alpha           = 1)
                        
G02.add_note(LTC_plot.sigma + f" = {sig}", [32800, 9000])

###################################################################
#   Creating a multi-plot page                                    #
###################################################################

Page1 = LTC_plot.Page(rows_x_cols = (1, 2), page_size = None)
Page1.add_plot(G18, position = 1)
Page1.add_plot(G02, position = 2)
Page1.create_svg(file_basename = "histograms")
