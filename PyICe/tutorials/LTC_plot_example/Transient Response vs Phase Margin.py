from PyICe import LTC_plot
from numpy import e, sin, arctan, pi, tan
phase_margins = [76, 45, 34, 27, 22, 18, 14, 11, 5.7]
Page1 = LTC_plot.Page(rows_x_cols = (3, 3), page_size = (8.5,11))
position = 1
Wn = 0.075
for phase_margin in phase_margins:
    time = list(range(1000))
    phase_margin_rads = pi / 180 * phase_margin
    zeta = (4*((2*(tan(pi/2-phase_margin_rads))**2+1)**2-1))**-0.25
    print(f'phase margin = {phase_margin}°, zeta = {zeta}')
    Wd = Wn * (1 - zeta**2)**0.5
    data = [1 - e**(-zeta * Wn * t) / (1 - zeta**2)**-0.5 * sin( Wd * t + arctan((1 - zeta**2)**0.5 / zeta)) for t in time]
    G0 = LTC_plot.plot(     plot_title      = f"Phase margin = {phase_margin}°",
                            plot_name       = f"ζ = {zeta:0.3}",
                            xaxis_label     = "TIME (S)",
                            yaxis_label     = "AMPLITUDE (V)",
                            xlims           = (0, 1000),
                            ylims           = 'auto',
                            xminor          = 0,
                            xdivs           = 5,
                            yminor          = 0,
                            ydivs           = 6,
                            logx            = False,
                            logy            = False)

    G0.add_trace(           axis            = 1,
                            data            = list(zip(time,data)),
                            color           = LTC_plot.LT_RED_1,
                            marker          = "",
                            markersize      = 0,
                            linestyle       = "-",
                            legend          = "")

    Page1.add_plot(G0, position = position)
    position += 1

Page1.create_svg(file_basename = "PhaseMargin")
Page1.create_pdf(file_basename = "PhaseMargin")