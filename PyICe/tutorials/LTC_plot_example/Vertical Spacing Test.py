from PyICe import LTC_plot

ROWS = 2

Page1 = LTC_plot.Page(rows_x_cols = (ROWS, 1))#, page_size = (8.5,11))
row = 1
title_rows = 10
for plot in range(ROWS):
    title = ""
    for line in range(title_rows):
        title += f"Line {line + 1}\n"
    G0 = LTC_plot.plot( plot_title      = title[:-1],
                        plot_name       = "Test",
                        xaxis_label     = "NOTHING ()",
                        yaxis_label     = "NOTHING ()",
                        xlims           = (0, 100),
                        ylims           = (0, 100),
                        xminor          = 0,
                        xdivs           = 5,
                        yminor          = 0,
                        ydivs           = 5,
                        logx            = False,
                        logy            = False)

    Page1.add_plot(G0, position=row, y_gap=3, top_border=2, bottom_border=1)
    # print("added chart")
    row += 1
# Page1.create_svg(file_basename="Vertical Test")
Page1.create_pdf(file_basename="Vertical Test")