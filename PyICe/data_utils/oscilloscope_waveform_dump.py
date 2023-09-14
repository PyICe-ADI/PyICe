from PyICe.instruments.oscilloscope import oscilloscope
from PyICe import lab_core
from PyICe import lab_utils
try:
    from bokeh.models import Label, Toggle
    from bokeh import colors
    ##  https://docs.bokeh.org/en/latest/docs/reference/colors.html#bokeh-colors-color

    from bokeh.plotting import show, output_file, figure
    from bokeh.io import curdoc
    from bokeh.layouts import layout
except:
    print("Broken Bokeh")
import time

class dict_print(dict):
    def __str__(self):
        ret_str = ""
        max_key_len = 0
        for key,value in self.items():
            max_key_len = len(key) if len(key)>max_key_len else max_key_len
            if type(value) == list and len(value)>=4:
                ret_str += f"{key}:\t[{value[0]}, {value[1]}, ..., {value[-2]}, {value[-1]}]\n"
            else:
                ret_str += f"{key}:\t{value}\n"
        return ret_str.expandtabs(max_key_len+2)

class oscilloscope_waveform_dump(oscilloscope):
    def __init__(self, interface_visa):
        '''interface_visa'''
        self._base_name = "agilent_3034a"
        lab_core.scpi_instrument.__init__(self,"agilent_3034a @ {}".format(interface_visa))
        lab_core.delegator.__init__(self)  # Clears self._interfaces list, so must happen before add_interface_visa(). --FL 12/21/2016
        self.add_interface_visa(interface_visa)
        self.get_interface().write(":WAVeform:FORMat BYTE")
        self.get_interface().write(":WAVeform:POINts:MODE RAW") #maximum number of points by default (scope must be stopped)
        self.get_interface().write(":WAVeform:POINts MAXimum")
    def _get_channel_data(self, channel_num):
        self.get_interface().write(f":Waveform:Source CHANNel{channel_num}")
        return self.fetch_waveform_data()
    def _get_scope_time_info(self):
        ### Requires Waveform Source to be set to an acive channel 
        self.time_info                = {}
        self.time_info["points"]      = int(self.get_interface().ask(":WAVeform:POINts?"))         # int(preamble[2])
        self.time_info["x_increment"]   = float(self.get_interface().ask(":WAVeform:XINCrement?"))   # float(preamble[4])
        self.time_info["x_origin"]      = float(self.get_interface().ask(":WAVeform:XORigin?"))      # float(preamble[5])
        self.time_info["x_reference"]   = float(self.get_interface().ask(":WAVeform:XREFerence?"))   # float(preamble[6])
        self.time_info["x_scale"]       = self.time_info["x_increment"] * self.time_info["points"] / 10
        self.time_info["x_values"] = [(x - self.time_info["x_reference"]) * self.time_info["x_increment"] + self.time_info["x_origin"] for x in range(self.time_info["points"])]
        return self.time_info
    def fetch_active_scope_channels(self):
        results_dict = dict_print()
        for num in [1,2,3,4]:
            displayed = int(self.get_interface().ask(f":Channel{num}:Display?"))
            results_dict[f'channel_{num}_active'] = displayed
            if displayed:
                results_dict[f"channel_{num}"] = self._get_channel_data(num)
                for key,value in self.get_waveform_scaling().items():
                    results_dict[f"channel_{num}_{key}"] = value
                results_dict[f'channel_{num}_name'] = self.user_query_waveform_name(num)
        if len(results_dict):
            results_dict.update(self._get_scope_time_info())
            print(f"Number of points captured = {results_dict['points']}")
        return results_dict
    def user_query_waveform_name(self, channel_number):
        resp = ""
        while not len(resp):
            resp = input(f"What's channel_{channel_number} measuring: ")
        return resp
    def data_to_sqlite(self, db_filename='scope_data.sqlite'):
        logger = lab_core.logger(database=db_filename, use_threads=False)
        scope_data= self.fetch_active_scope_channels()
        logger.add_data_channels(scope_data)
        db_tablename = ''
        while not len(db_tablename):
            db_tablename = input(f"What would you like the table name to be: ")
        logger.new_table(db_tablename)
        sd = logger.log_data(scope_data)
        logger.stop()
        # return sd
        return db_tablename

def plot_dumped_waveform(db_tablename, db_filename = 'scope_data.sqlite'):
    db = lab_utils.sqlite_data(table_name=db_tablename, database_file=db_filename, timezone=None)
    output_file(filename=f'{db_tablename}.html', title = db_tablename)
    curdoc().theme = 'dark_minimal'
    plot = figure(title=db_tablename, plot_width=1000, plot_height=800)
    active_channels = {}
    channel_colors = {1:colors.named.gold, 2:colors.named.forestgreen, 3:colors.named.mediumblue, 4:colors.named.fuchsia}
    (datetime,x_values, active_channels[1], active_channels[2], active_channels[3], active_channels[4]) = db.query(f'SELECT datetime,x_values, channel_1_active, channel_2_active, channel_3_active, channel_4_active FROM {db_tablename}').fetchone()
    toggles={}
    for i in range(1,5):
        if active_channels[i]:
            (ydata,data_name) = db.query(f'SELECT channel_{i}, channel_{i}_name FROM {db_tablename}').fetchone()
            this_line = plot.line(x=x_values, y=ydata, line_color=channel_colors[i], legend_label=f"{data_name}", alpha=.5)
            toggles[i] = Toggle(label=f'Show {data_name}', button_type='success', active=True, background = channel_colors[i]) #background does NOTHING!
            toggles[i].js_link('active', this_line, 'visible')
    show(layout([plot], list(toggles.values())))

if __name__=='__main__':
    answer = input("(P)lot data only or (C)ollect and plot: ")
    if answer.lower() == "c":
        from create_user_files import create_my_scopefile
        create_my_scopefile()
        from local.my_instruments import agilent_3034a
        dump = oscilloscope_waveform_dump(agilent_3034a)
        db_tablename = dump.data_to_sqlite()
    elif answer.lower() == "p":
        db_tablename = input("Enter the table name in the preexisting scope_data.sqlite file: ")
    else:
        print(f"\n\nYour response to (C)ollect or (P)lot was: '{answer}'.\nDon't know what '{answer}' is supposed to do.\nDoing nothing.\n\n")
        exit()
    plot_dumped_waveform(db_tablename)
