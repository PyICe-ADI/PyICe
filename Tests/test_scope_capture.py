import datetime
from PyICe import lab_core, lab_utils, lab_instruments, LTC_plot

database_name = "scope_shots.sqlite"

##############
# Collection #
##############
table_name = input("What's the name of this scope capture [skip capture]:")
if table_name != '':
    master = lab_core.master()
    # interface = master.get_visa_interface("USB0::0x0957::0x17a4::MY52160757::0::INSTR")
    interface = master.get_visa_interface("USB0::0x0957::0x17a4::MY52012651::0::INSTR")
    scope = lab_instruments.agilent_3034a(interface)
    scope.add_channel_time('scope_time')
    scope.set_points(5000) #    [100,250,500] or [1000,2000,5000]*10^[0-4] or [8000000]
    for channel in range(1,5):
        if scope.get_channel_enable_status(channel):
            scope.add_channel('scope_channel_{}'.format(channel), channel)
    master.add(scope)
    master.add_channel_dummy("plot_title")
    logger = lab_core.logger(channel_master_or_group=master, database=database_name, use_threads=True)
    table_name = input("What's the name of this scope shot (database table name):") if table_name is None else table_name
    plot_title = input("What's the scope shot title [{}]:".format(table_name))
    if plot_title == '':
        plot_title = table_name
    master.write("plot_title", plot_title)
    logger.new_table(table_name, replace_table = True)
    logger.log()
    logger.stop()

##############
#  Plotting  #
##############
if table_name == '':
    db = lab_utils.sqlite_data(table_name=None, database_file=database_name)
    tables = db.query("""SELECT name FROM SQLITE_MASTER WHERE type=='table'""")
    table_name = lab_utils.present_menu(intro_msg="Found the following tables: ",
                           prompt_msg="Which table do you want to plot: ",
                           item_list=[row[0] for row in db.to_list()]
                           )
database = lab_utils.sqlite_data(table_name=table_name, database_file=database_name)
query = '''SELECT plot_title, scope_time_info from {}'''.format(table_name)
database.query(query)
x_units_per_div = database[0]['scope_time_info']['scale']
x_origin = database[0]['scope_time_info']['origin']
ch_enable_status = database[0]['scope_time_info']['enable_status']
plot_title = database[0]['plot_title']

GX = LTC_plot.scope_plot(   plot_title      = plot_title,
                            plot_name       = "G0X",
                            xaxis_label     = 'TIME {}s/DIV'.format(lab_utils.eng_string(x_units_per_div, fmt = ':.3g', si = True)),
                            xlims           = (x_origin, 10 * x_units_per_div + x_origin),
                            ylims           = (-4, 4) # Should this be removed from LTC_plot?
                            )

scope_colors =  {1: LTC_plot.LT_COPPER_2,
                 2: LTC_plot.LT_GREEN_2,
                 3: LTC_plot.LT_BLUE_2,
                 4: LTC_plot.LT_RED_2,
                }
                
scope_legend =  {1: "VBUS",
                 2: "VOUT",
                 3: "VBAT",
                 4: "ISW",
                }
                
smooth_factor = {1: None,
                 2: None,
                 3: None,
                 4: None,
                }
                
poles =         {1: 0,
                 2: 0,
                 3: 0,
                 4: 0,
                }

for channel in range(1,5):
    if ch_enable_status[channel]:
        query = '''SELECT scope_time, scope_channel_{} FROM {}'''.format(channel, table_name)
        database.query(query)
        data = lab_utils.oscilloscope_channel(*database[0])
        query = '''SELECT scope_channel_{}_info FROM {}'''.format(channel, table_name)
        database.query(query)
        channel_info = database[0][0]
        yscale  = channel_info['scale']**-1
        yoffset = -channel_info['offset']
        yunits  = channel_info['units']
        data.yoffset(yoffset)
        data.yscale(yscale)
        if smooth_factor[channel] is not None:
            data.smooth_y(window = smooth_factor[channel], extrapolation_window = None, iterations = poles[channel])

        GX.add_trace(           data            = data,
                                color           = scope_colors[channel],
                                legend          = "{}: {}{}/DIV".format(scope_legend[channel], yscale**-1, yunits)
                    )
        GX.add_ref_marker(ylocation=yoffset*yscale, marker_color=scope_colors[channel], use_axes_scale=True)
GX.add_legend(location =(1,0), use_axes_scale = False)
Page1 = LTC_plot.Page(rows_x_cols = (1, 1), page_size = (4,3))
Page1.add_plot(GX,
               position    = None,
               plot_sizex  = None,
               plot_sizey  = None,
               trace_width = None
              )
Page1.create_svg(table_name + "-" + datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"))
Page1.create_svg(table_name)
# Page1.create_pdf(table_name)