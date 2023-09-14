#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyICe import lab_utils

db = lab_utils.sqlite_data(database_file='temp_sensor.sqlite', table_name='temp_sensor')
# db = lab_utils.sqlite_data(table_name='die_temp_2017_01_30_15_57')
#db = lab_utils.sqlite_data(database_file='LTC6363_bandwidth_vs_freq00.sqlite', table_name='LTC6363_1_bandwidth_vs_freq00')
#db = lab_utils.sqlite_data(database_file='LTC6363_bandwidth_vs_freq00.sqlite', table_name='LTC6363_2_bandwidth_vs_freq00')

#Option 1 - let CSV method do elapsed time calculation in Python
csv = db.csv(output_file='die_temp.csv', elapsed_time_columns=True, append=False)

#Option 2 - use time_delta_query to construct SQL statement and have SQLite make the elapsed time calculation.
db.query("SELECT {}, * FROM temp_sensor".format(db.time_delta_query(time_div=60))) #output scaled from seconds to minutes
csv2 = db.csv(output_file='die_temp2.csv')

#shouldn't change anything if all logged data is scalar. In this case, expands Hameg fuse linking list (len 3).
csv3 = db.expand_vector_data(csv_filename='die_temp3.csv')


db.xlsx('die_temp.xlsx',elapsed_time_columns=True)

wb = lab_utils.sqlite_to_xlsx('temp_sensor.xlsx')

sheets = wb.add_database(db_file_name='temp_sensor.sqlite', elapsed_time_columns=True)
# x_axis = 'elapsed_seconds'
x_axis = 'board_temp'
for ws_name, ws in list(sheets.items()):
    if ws_name.startswith('temp_sensor'):
        if ws_name.endswith('_formatted') or ws_name.endswith('_all'): 
            y_axis = 'die_temp__DEG_C'
        else:
            y_axis = 'die_temp'
    #elif ws_name.startswith('die_temp'):
    #    y_axis = 'die_temp_meas'
    else:
        continue
    chart_setup = {'name': '{} vs {}'.format(y_axis, x_axis),
                   'categories': '={}!{}'.format(ws_name,x_axis), #x-axis using named range
                   'values': '={}!{}'.format(ws_name,y_axis),     #y-axis using named range
                   #'categories': [ws_name, 1, 3, 20, 3],         #x-axis, [sheet_name, top_row, left_column, bottom_row, bottom_column]
                   #'values': [ws_name, 1, 49, 20, 49],           #y-axis, [sheet_name, top_row, left_column, bottom_row, bottom_column]
                  }
    print("Adding chart {name} to sheet {ws_name}.".format(ws_name=ws_name, **chart_setup))
    chart = wb.add_xy_chart()
    chart.add_series(chart_setup)
    chart.set_legend({'none': True})
    chart.set_x_axis({'name': x_axis, 'major_gridlines': {'visible': True,}})
    chart.set_y_axis({'name': y_axis})
    ws.insert_chart('I23', chart)
wb.close()


# # Quick interactive plotting
# import pandas
# import matplotlib.pyplot as plt
# pandas_df = db.pandas_dataframe()
# pandas_dfi = pandas_df.set_index('datetime')
# ax = pandas_dfi['die_temp_fmt'].plot.line(title='Die Temp vs Time')
# ax.set_ylabel(u'Die Temp °C')
# ax.grid(True, which='both')
# plt.show()
