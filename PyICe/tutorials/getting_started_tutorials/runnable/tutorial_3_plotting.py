# ========================
# TUTORIAL 3 Plotting Data
# ========================

from PyICe import LTC_plot
from PyICe.lab_utils.sqlite_data import sqlite_data

GX = LTC_plot.plot( plot_title  = "Demonstration of Meter Readings\nVs Iteration Number",
                   plot_name    = "Tutorial 3",
                   xaxis_label  = "ITERATION ()",
                   yaxis_label  = "VOLTAGE (µV)",
                   xlims        = (1, 9),
                   ylims        = (-10, 10),
                   xminor       = 0,
                   xdivs        = 8,
                   yminor       = 0,
                   ydivs        = 10,
                   logx         = False,
                   logy         = False)

my_query = 'SELECT rowid, vmeas*1e6 FROM tutorial_2_table ORDER BY rowid'

database = sqlite_data(table_name="tutorial_2_table", database_file="data_log.sqlite")            
database.query(my_query)


GX.add_trace(axis   = 1,
            data   = database.to_list(),
            color  = LTC_plot.LT_RED_1,
            legend = "Only\nTrace")

GX.add_legend(axis=1, location=(1.02, 0), use_axes_scale=False)


GX.add_note(note="Add Your Note Here", location=(0.02, 0.02), use_axes_scale=False)

Page1 = LTC_plot.Page(rows_x_cols=(1, 1), page_size=None)
Page1.add_plot(plot=GX, position=1)
Page1.create_svg(file_basename="TUTORIAL 3")
Page1.create_pdf(file_basename="TUTORIAL 3")

print("\n\nLook in the \\results\\plots folder for the Tutorial 3 files.")