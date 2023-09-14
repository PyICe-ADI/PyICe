from PyICe import LTC_plot
import os
###################################################################
#   Example creating a large plot for lab viewing only.           #
###################################################################
G01 = LTC_plot.plot(    plot_title      = "Burst Mode to Constant Frequency Mode Transition Waveform\nVSYS",
                        plot_name       = "4040 G01",
                        xaxis_label     = "TIME (" + LTC_plot.mu + "s)",
                        yaxis_label     = "VOLTAGE (V)",
                        xlims           = [0, 3200],
                        ylims           = [4.6, 5.2],
                        xminor          = None,
                        xdivs           = 4,
                        yminor          = None,
                        ydivs           = 6,
                        logx            = False,
                        logy            = False)

G01.add_trace(          axis            = 1,
                        data            = LTC_plot.data_from_file("./data/SYS_voltage.csv"),
                        color           = LTC_plot.LT_RED_1,
                        marker          = None,
                        markersize      = 0,
                        legend          = "VSYS")

G01.add_note(r"$V_{BAT}$" + " = 3.7V\n" + r"$C_{SYS} = 200$" + LTC_plot.mu + "F\nL = 2.2" + LTC_plot.mu + "H", [1600, 5.07])

G02 = LTC_plot.plot(    plot_title      = "Burst Mode to Constant Frequency Mode Transition Waveform\nILOAD",
                        plot_name       = "4040 G02",
                        xaxis_label     = "TIME (" + LTC_plot.mu + "s)",
                        yaxis_label     = "CURRENT (A)",
                        xlims           = [0, 3200],
                        ylims           = [0, 3],
                        xminor          = None,
                        xdivs           = 4,
                        yminor          = None,
                        ydivs           = 6,
                        logx            = False,
                        logy            = False)
                        
G02.add_trace(          axis            = 1,
                        data            = LTC_plot.data_from_file("./data/load_current.csv"),
                        color           = LTC_plot.LT_BLUE_1,
                        marker          = None,
                        markersize      = 0,
                        legend          = "ILOAD")

G02.add_note(r"$V_{BAT}$" + " = 3.7V\n" + r"$C_{SYS} = 200$" + LTC_plot.mu + "F\nL = 2.2" + LTC_plot.mu + "H", location = [1600, 2.5])

###################################################################
#   Creating a multi-plot page                                    #
###################################################################
Page1 = LTC_plot.Page(rows_x_cols = (1, 1), page_size = (11, 8.5))
Page2 = LTC_plot.Page(rows_x_cols = (1, 1), page_size = (11, 8.5))
Page1.add_plot(G01, position = 1, plot_sizex = 9, plot_sizey = 7)
Page2.add_plot(G02, position = 1, plot_sizex = 9, plot_sizey = 7)

Multipagefile = LTC_plot.Multipage_pdf()
Multipagefile.add_page(Page1)
Multipagefile.add_page(Page2)
Multipagefile.create_pdf(file_basename = "lab_plot_example")
os.startfile(os.path.dirname(os.path.abspath(__file__)) + "/plots/lab_plot_example.pdf")




