from PyICe import LTC_plot
from PyICe.lab_utils.sqlite_data import sqlite_data
import numpy as np
###################################################################
#   Example creating a data sheet ready SVG file.                 #
###################################################################
xdata =     [-40, 125]
ydata1 =    [1.245, 1.275]
ydata2 =    [1.28, 1.33]
ydata3 =    [1.7, 1.69]
plot_name = "8709 G13"
G13 = LTC_plot.plot(    plot_title      = "EN/FBIN Thresholds vs\nTemperature (1.7V and 1.3V)",
                        plot_name       = plot_name,
                        xaxis_label     = "TEMPERATURE (" + LTC_plot.DEGC + ")",
                        yaxis_label     = "XXXX\nN/FBIN CHIP ENABLE (V)",
                        xlims           = (-50, 125),  # "auto" or None for auto-scale
                        ylims           = (1.2, 1.4),#(0, 14),   # "auto" or None for auto-scale
                        xminor          = 0,
                        xdivs           = 7,
                        yminor          = 0,
                        ydivs           = 10,
                        logx            = False,
                        logy            = False)

G13.add_trace(          axis            = 1,
                        data            = list(zip(xdata, ydata1)),
                        color           = LTC_plot.LT_RED_1,
                        legend          = "FALLING")
                        
G13.add_trace(          axis            = 1,
                        data            = list(zip(xdata, ydata2)),
                        color           = LTC_plot.LT_BLUE_1,
                        legend          = "RISING")
# G13.add_legend(axis = 1, location = (0.01, 0.01))
G13.make_second_y_axis( yaxis_label     = "EN/FBIN ACTIVE MODE (V)",
                        ylims           = (1.55, 1.75), # "auto" or None for auto-scale
                        yminor          = 0,
                        ydivs           = 10,
                        logy            = False)
    
G13.add_trace(          axis            = 2,
                        data            = list(zip(xdata, ydata3)),
                        color           = LTC_plot.LT_GREEN_1,
                        legend          = "RISING ONLY")
# G13.add_legend(axis = 2, location = "best")
G13.add_arrow(          text            = "FALLING",
                        text_location   = (0, 1.265),
                        arrow_tip       = (-50, 1.265))
G13.add_arrow(          text            = "RISING",
                        text_location   = (0, 1.31),
                        arrow_tip       = (-50, 1.31))
G13.add_arrow(          text            = "RISING ONLY",
                        text_location   = (25, 1.35),
                        arrow_tip       = (120, 1.35))
###################################################################
#   Example creating a data sheet ready SVG file of an FFT.       #
###################################################################
plot_name = "FFT DEMO G0"   
G0 = LTC_plot.plot(     plot_title      = "128K Point FFT, fIN = 2.2MHz,\n-1dBFS, PGA = 0",
                        plot_name       = plot_name,
                        xaxis_label     = "FREQUENCY (MHz)",
                        yaxis_label     = "AMPLITUDE (dBFS)",
                        xlims           = (0, 105), #(0, 10),    # "auto" or None for auto-scale
                        ylims           = (-140, 0), #(0, 1),   # "auto" or None for auto-scale
                        xminor          = 0,
                        xdivs           = 7,
                        yminor          = 0,
                        ydivs           = 7,
                        logx            = False,
                        logy            = False)
                                        
filename = "./data/FFT Data.txt"
G0.add_trace(           axis            = 1,
                        data            = LTC_plot.data_from_file(filename),
                        color           = LTC_plot.LT_RED_1,
                        marker          = "",
                        markersize      = 0,
                        linestyle       = "-",
                        legend          = "25" + LTC_plot.DEGC)
###################################################################
#   Creating G22                                                  #
###################################################################
xdata = [i for i in range(0, 13)]
ydata1 = [0.1083*i for i in xdata]
ydata2 = [0.083 * i for i in xdata]
ydata3 = [0.0667 * i for i in xdata]
plot_name = "2975 G22"
G22 = LTC_plot.plot(    plot_title      = r"$V_{OUT\_EN[0:3]}$" + " and AUXFAULTB VOL\nvs Load Current",
                        plot_name       = plot_name,
                        xaxis_label     = "CURRENT SOURCING (" + LTC_plot.mu + "A)",
                        yaxis_label     = r"$V_{OL} (V)$",
                        xlims           = [0, 12],
                        ylims           = [0, 1.4],
                        xminor          = 0,
                        xdivs           = 6,
                        yminor          = 0,
                        ydivs           = 7,
                        logx            = False,
                        logy            = False)
                                        
G22.add_trace(          axis            = 1,
                        data            = list(zip(xdata, ydata1)),
                        color           = LTC_plot.LT_RED_1,
                        legend          = "105" + LTC_plot.DEGC)

G22.add_trace(          axis            = 1,
                        data            = list(zip(xdata, ydata2)),
                        color           = LTC_plot.LT_GREEN_1,
                        legend          = "25" + LTC_plot.DEGC)
                        
G22.add_trace(          axis            = 1,
                        data            = list(zip(xdata, ydata3)),
                        color           = LTC_plot.LT_BLUE_1,
                        legend          = "-40" + LTC_plot.DEGC)
                        
G22.add_arrow(          text            = "25" + LTC_plot.DEGC,
                        text_location   = (4.2, 0.77),
                        arrow_tip       = (7.25, 0.6),
                        use_axes_scale  = True)

G22.add_note("105" + LTC_plot.DEGC, [7, 1])
G22.add_note(LTC_plot.minus + "40" + LTC_plot.DEGC, [9, 0.5])
###################################################################
#   Creating a histogram                                          #
###################################################################
mu = -0.11 # mean of distribution
sig = 0.022 # standard deviation of distribution
xdata1 = mu + sig * np.random.randn(194)
plot_name = "2975 G18"
G18 = LTC_plot.plot(plot_title      = "Closed Loop Servo Error",
                    plot_name       = plot_name,
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

G18.add_histogram(  axis            = 1,
                    xdata           = xdata1,
                    num_bins        = 5,
                    color           = LTC_plot.LT_BLUE_2_40PCT,
                    normed          = False,
                    legend          = "data1",
                    # edgecolor       = None,
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
G02 = LTC_plot.plot(plot_title      = "DC Histogram",
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

G02.add_histogram(  axis            = 1,
                    xdata           = xdata1,
                    num_bins        = 100,
                    color           = LTC_plot.LT_RED_1,
                    normed          = False,
                    legend          = "data1",
                    linewidth       = 0.001,
                    alpha           = 1)
                        
G02.add_note(LTC_plot.sigma + f" = {sig}", [32800, 9000])
###################################################################
#   Entering a scope trace                                        #
###################################################################
plot_name = "4040 G24"
G24 = LTC_plot.scope_plot(  plot_title  = "Burst Mode to Constant Frequency\nMode Transition Waveform",
                            plot_name   = plot_name,
                            xaxis_label = "10µs/DIV",
                            xlims       = [0, 3200],
                            ylims       = [4.6, 5.2])

G24.add_trace(data   = LTC_plot.data_from_file("./data/SYS_voltage.csv"),
              color  = LTC_plot.LT_RED_1,
              legend = "VSYS")
                        
G24.add_trace_label(trace_label     = "VOUT\n20µV/DIV",
                    ylocation       = 0.25,
                    use_axes_scale  = False)

G24.add_note(r"$V_{BAT}$" + " = 3.7V\n" + r"$C_{SYS} = 200$" + LTC_plot.mu + "F\nL = 2.2" + LTC_plot.mu + "H", [1600, 5.07])
G24.add_note(r"$V_{SYS}$", [600, 5])
G24.add_note(r"$I_{SYS}$", [600, 4.7])
###################################################################
#   Dave's Battery Data                                           #
###################################################################
charge_tables = []
discharge_tables = []
charge_tables.append("charge_bat1_2015_04_14_17_00_26") # 2A

charge_tables.append("charge_bat1_2015_04_15_13_01_54") # 200mA
charge_tables.append("charge_bat1_2015_04_16_15_06_55") # 400mA
charge_tables.append("charge_bat1_2015_04_17_06_38_13") # 600mA
charge_tables.append("charge_bat1_2015_04_17_18_08_48") # 800mA
charge_tables.append("charge_bat1_2015_04_18_03_41_03") # 1A
charge_tables.append("charge_bat1_2015_04_18_11_16_37") # 1.5A
charge_tables.append("charge_bat1_2015_04_18_17_27_00") # 2A

discharge_tables.append("discharge_bat1_2015_04_14_20_30_40") # 200mA
discharge_tables.append("discharge_bat1_2015_04_16_06_57_34") # 400mA
discharge_tables.append("discharge_bat1_2015_04_17_01_12_42") # 600mA
discharge_tables.append("discharge_bat1_2015_04_17_14_06_28") # 800mA
discharge_tables.append("discharge_bat1_2015_04_18_00_25_22") # 1A
discharge_tables.append("discharge_bat1_2015_04_18_09_06_37") # 1.5A
discharge_tables.append("discharge_bat1_2015_04_18_15_48_00") # 2A

group1 = ["charge_bat1_2015_04_15_13_01_54", "discharge_bat1_2015_04_14_20_30_40", "IBAT = 200mA"]
group2 = ["charge_bat1_2015_04_16_15_06_55", "discharge_bat1_2015_04_16_06_57_34", "IBAT = 400mA"]
group3 = ["charge_bat1_2015_04_17_06_38_13", "discharge_bat1_2015_04_17_01_12_42", "IBAT = 600mA"]
group4 = ["charge_bat1_2015_04_17_18_08_48", "discharge_bat1_2015_04_17_14_06_28", "IBAT = 800mA"]
group5 = ["charge_bat1_2015_04_18_03_41_03", "discharge_bat1_2015_04_18_00_25_22", "IBAT = 1A"]
group6 = ["charge_bat1_2015_04_18_11_16_37", "discharge_bat1_2015_04_18_09_06_37", "IBAT = 1.5A"]
group7 = ["charge_bat1_2015_04_18_17_27_00", "discharge_bat1_2015_04_18_15_48_00", "IBAT = 2A"]

groups = []
groups.append(group1)
groups.append(group2)
groups.append(group3)
groups.append(group4)
groups.append(group5)
groups.append(group6)
groups.append(group7)

Page1 = LTC_plot.Page(rows_x_cols = (3, 3), page_size = (8.5, 11))
position = 1
daves_plots = []
for group in groups:
    plot_name = f"{group[0]}_{group[1]}"
    GX = LTC_plot.plot( plot_title      = "Energy Delivered & Received vs\nBattery Voltage",
                        plot_name       = plot_name,
                        xaxis_label     = "VOLTAGE (V)",
                        yaxis_label     = "ENERGY (WH)",
                        xlims           = (3, 4.5),
                        ylims           = (-1, 13),
                        xminor          = 2,
                        xdivs           = 5,
                        yminor          = 1,
                        ydivs           = 14,
                        logx            = False,
                        logy            = False)
                            
    daves_plots.append(GX)
    database_charging = sqlite_data(table_name = f'{group[0]}', database_file="./data/battery_data.sqlite")
    database_discharging = sqlite_data(table_name = f'{group[1]}', database_file="./data/battery_data.sqlite")
    query_charging = f'''SELECT  bat1_voltage,
                        integratedWH
                        FROM {group[0]}'''
    query_discharging = f'''SELECT  bat1_voltage,
                        integratedWH + 11.788
                        FROM {group[1]}'''
    database_charging.query(query_charging)
    database_discharging.query(query_discharging)
    GX.add_trace(axis   = 1,
                 data   = database_charging.to_list(),
                 color  = LTC_plot.LT_RED_1,
                 legend = "Charging")

    GX.add_trace(axis   = 1,
                 data   = database_discharging.to_list(),
                 color  = LTC_plot.LT_BLUE_1,
                 legend = "Discharging")
    GX.add_legend(axis = 1, location = (3.025, 10), use_axes_scale = True)
    GX.add_note(group[2], [4, 0])
    position += 1
###################################################################
#   Creating a multi-plot page                                    #
###################################################################
rows_x_cols = (3, 3)
Page1 = LTC_plot.Page(rows_x_cols, page_size = (8.5, 11))
Page1.add_plot(G0, position = 1)
Page1.add_plot(G13, position = 2)
Page1.add_plot(G22, position = 3)
Page1.add_plot(G18, position = 4)
Page1.add_plot(G02, position = 5)

Page2 = LTC_plot.Page(rows_x_cols, page_size = (8.5, 11))
position = 1
for plot in daves_plots:
    Page2.add_plot(plot, position = position)
    position += 1

Page3 = LTC_plot.Page((3,3), page_size = (8.5, 11))
Page3.add_plot(G24, position = 1)

Multipagefile = LTC_plot.Multipage_pdf()
Multipagefile.add_page(Page1)
Multipagefile.add_page(Page2)
Multipagefile.add_page(Page3)
Multipagefile.create_pdf("Extensive Example")
Multipagefile.kit_datasheet(file_basename="Extensive Example")