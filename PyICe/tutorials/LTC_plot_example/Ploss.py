from PyICe import LTC_plot, lab_utils

Pdie = []
Pres = []
Ploss = []
Peth = []
R = 1
VETH = 1.1
VIN = 1.8

traces = {  "Pdie"  :{"DATA": Pdie,     "LABEL": r"P$_{DIE}$",    "COLOR": LTC_plot.LT_RED_1},
            "Pres"  :{"DATA": Pres,     "LABEL": r"P$_{RES}$",    "COLOR": LTC_plot.LT_BLUE_1},
            "Plost" :{"DATA": Ploss,    "LABEL": r"P$_{LOST}$",   "COLOR": LTC_plot.LT_GREEN_1},
            "Peth"  :{"DATA": Peth,     "LABEL": r"P$_{ETH}$", "COLOR": LTC_plot.LT_BLACK},
         }

currents = lab_utils.floatRangeInc(start=0, stop=0.5, step=0.01)

for current in currents:
    vres = current * R
    vdie = VIN - vres - VETH
    Pdie.append(current * vdie)
    Pres.append(current * vres)
    Ploss.append(current * vdie + current * vres)
    Peth.append(current * VETH)
    
G0 = LTC_plot.plot( plot_title      = f"Ethernet Power Losses vs\nLoad Current\nVETH = {VETH}V, VIN = {VIN}V",
                    plot_name       = "",
                    xaxis_label     = "CURRENT (A)",
                    yaxis_label     = "POWER DISS (W)",
                    xlims           = (0, 0.5),
                    ylims           = (0, 0.6),
                    xminor          = 2,
                    xdivs           = 5,
                    yminor          = 2,
                    ydivs           = 6,
                    logx            = False,
                    logy            = False)

for trace in traces:
    G0.add_trace(   axis            = 1,
                    data            = list(zip(currents, traces[trace]["DATA"])),
                    color           = traces[trace]["COLOR"],
                    marker          = "",
                    markersize      = 0,
                    linestyle       = "-",
                    legend          = traces[trace]["LABEL"])

G0.add_legend(axis=1, location = (1,0), justification='lower left', use_axes_scale=False, fontsize=7)
G0.add_vertical_line(value=0.3, yrange=None, note=None, color=[1,0,0])

Page1 = LTC_plot.Page(rows_x_cols=(1, 1), page_size=None)
Page1.add_plot(G0, position = 1)
Page1.create_svg(file_basename = "Ethernet Power Losses")
Page1.create_pdf(file_basename = "Ethernet Power Losses")
