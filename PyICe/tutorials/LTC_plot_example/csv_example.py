from PyICe import LTC_plot

G0 = LTC_plot.plot(     plot_title      = "128K Point FFT, fIN = 2.2MHz,\n-1dBFS, PGA = 0",
                        plot_name       = "FFT DEMO G0",
                        xaxis_label     = "FREQUENCY (MHz)",
                        yaxis_label     = "AMPLITUDE (dBFS)",
                        xlims           = (0, 105),     # "auto" or None for auto-scale
                        ylims           = (-140, 0),    # "auto" or None for auto-scale
                        xminor          = 0,
                        xdivs           = 7,
                        yminor          = 0,
                        ydivs           = 7,
                        logx            = False,
                        logy            = False)

G0.add_trace(           axis            = 1,
                        data            = LTC_plot.data_from_file("./data/FFT Data.txt"),
                        color           = LTC_plot.LT_RED_1,
                        marker          = "",
                        markersize      = 0,
                        linestyle       = "-",
                        legend          = "")
                        
Page1 = LTC_plot.Page(rows_x_cols = (1, 1), page_size = None)
Page1.add_plot(G0, position = 1)
Page1.create_svg(file_basename = "CSV Example")
