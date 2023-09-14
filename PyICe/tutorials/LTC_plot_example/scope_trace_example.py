from PyICe import LTC_plot

G24 = LTC_plot.scope_plot(  plot_title      = "Burst Mode to Constant Frequency\nMode Transition Waveform",
                            plot_name       = "4040 G24",
                            xaxis_label     = "2µS/DIV",
                            xlims           = (-400, 2400),
                            ylims           = (0, 8))

colors = LTC_plot.color_gen()

G24.add_trace(          data            = LTC_plot.data_from_file("./data/load_current.csv"),
                        color           = LTC_plot.LT_BLUE_1,
                        legend          = "ILOAD")

G24.add_trace_label(    trace_label     = "VOUT\n20µV/DIV",
                        ylocation       = 4,
                        use_axes_scale  = True)
                        
G24.add_trace_label(    trace_label     = "VOUT\n20µV/DIV",
                        ylocation       = 0.25,
                        use_axes_scale  = False)
     
G24.add_horizontal_line(value=0.2, xrange=None, note="horiz", color=[1,0,0])
G24.add_vertical_line(value=0, yrange=None, note="vert", color=[1,0,0])
                        
                        
for yloc in range(9):
    G24.add_ref_marker(     ylocation       = yloc / 8.,
                            marker_color    = LTC_plot.LT_RED_1,
                            use_axes_scale  = False)
                            
G24.add_time_refmarker_open(xlocation = 280)
G24.add_time_refmarker_closed(xlocation = 560)

Page1 = LTC_plot.Page(rows_x_cols = (1, 3), page_size = None)
Page1.add_plot(G24, position = 2)
Page1.create_svg(file_basename = "Scope Trace")
Page1.create_pdf(file_basename = "Scope Trace")