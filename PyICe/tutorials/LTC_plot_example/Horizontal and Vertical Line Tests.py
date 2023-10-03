from PyICe import LTC_plot
from PyICe.lab_utils.sqlite_data import sqlite_data

group1 = ["charge_bat1_2015_04_15_13_01_54", "discharge_bat1_2015_04_14_20_30_40", "IBAT = 200mA"]
GX = LTC_plot.plot( plot_title      = "Energy Delivered/Received vs\nBattery Voltage",
                    plot_name       = "GX",
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

query1 = '''SELECT  bat1_voltage,
                    integratedWH
                    FROM charge_bat1_2015_04_15_13_01_54'''
                    
query2 = '''SELECT  bat1_voltage,
                    integratedWH + 11.788
                    FROM discharge_bat1_2015_04_14_20_30_40'''
                                    
database = sqlite_data(table_name = f'{group1[0]}', database_file = "./data/battery_data.sqlite")
                                    
database.query(query1)
GX.add_trace(           axis            = 1,
                        data            = database.to_list(),
                        color           = LTC_plot.LT_RED_1,
                        legend          = "Charging")

database = sqlite_data(table_name = f'{group1[1]}', database_file = "./data/battery_data.sqlite")
                                    
database.query(query2)

GX.add_trace(           axis            = 1,
                        data            = database.to_list(),
                        color           = LTC_plot.LT_BLUE_1,
                        legend          = "Discharging")

GX.add_legend(axis = 1, location = (3.025, 10), use_axes_scale = True)
GX.add_note(group1[2], [4, 0])

GX.add_horizontal_line(value=5.5, xrange=GX.xlims, note="XNote")
GX.add_vertical_line(value=3.8, yrange=GX.ylims, note="YNote")

Page1 = LTC_plot.Page(rows_x_cols = (1, 1), page_size = None)
Page1.add_plot(GX, position = 1)
Page1.create_svg("LINES_TESTER")