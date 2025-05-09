from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.lab_utils.eng_string import eng_string
from PyICe.lab_utils.banners import print_banner
from sqlite3 import OperationalError
import numpy

class scope_data():
    '''This class can be used to convert data read from an oscilloscope's record into a more useful format once it has been logged into a PyICe SQLite database from a normal logger call.
       It was mainly used with the Agilent/Keysight Infinivision Series MSO-X 3034A Oscilloscopes. It may work for your scope or at least provide a framework for creating your own.'''

    def __init__(self, database, table_name, where_clause=''):
        query = f'SELECT * FROM {table_name} {where_clause}'
        try:
            database.query(query)
        except OperationalError as e:
            self.raise_sqlite_exception(query, e)
        assert len(database) == 1, f"Query returned multiple rows.\nTry pasting this line into a dbBrowser and see what it returns:\n\n{query}"
        self.row = database[0]
        self.trace_params = {}
        try:
            self.row['scope_Xposition_readback']
            self.row['scope_Xrange_readback']
            self.row['scope_Xreference_readback']
            self.readbacks_available = True
        except IndexError as e:
            self.readbacks_available = False
            print_banner("WARNING - Scope X and Y scales may be incorrect - not obtained from the scope readback channel!")
            print(e)
        self._get_time_info()

    def  _get_time_info(self):
        if self.readbacks_available:
            self.Xposition = self.row["scope_Xposition_readback"]
            self.Xrange = self.row["scope_Xrange_readback"]
            xref_text = self.row["scope_Xreference_readback"]
        else:
            self.Xposition = self.row["scope_Xposition"]
            self.Xrange = self.row["scope_Xrange"]
            xref_text = self.row["scope_Xreference"]
        if xref_text == "LEFT":
            self.Xreference = self.Xrange * 1 / 10.
        elif xref_text == "CENT" or xref_text == "CENTER":
            self.Xreference = self.Xrange * 5 / 10.
        elif xref_text == "RIGH" or xref_text == "RIGHT":
            self.Xreference = self.Xrange * 9 / 10.
        self.time_left = -self.Xreference - self.Xposition 
        self.time_right = self.time_left + self.Xrange # Not necessarily right. Sometimes xpoints recored (length) is not the same as xrange for unknown reason.

    def raise_error(self, trace_name, request, e):
        raise Exception(f'\n\nPyICE Oscilloscope Tools:\nNo trace parameters available for "{trace_name}" {request} request.\nTry adding a {trace_name} trace first.\n\n') from e

    def raise_sqlite_exception(self, query, e):
        raise Exception(f'\n\nPyICE Oscilloscope Tools: A failure occurred when querying the database.\nTry pasting this line into a dbBrowser and see what it returns:\n\n{query}') from e

    def time_range(self):
        return (self.time_left, self.time_right)

    def time_label(self, xlimits=None):
        if xlimits is None:
            return f"{eng_string((self.time_right - self.time_left) / 10, fmt=':.3g', si=True)}s/DIV"
        else:
            return f"{eng_string((xlimits[1] - xlimits[0]) / 10, fmt=':.3g', si=True)}s/DIV"

    def all_time_refmarkers(self):
        return {'xlocation_open'   : -self.Xposition,
                'xlocation_closed' : 0}

    def trace_data(self, trace_name, graticule=None, scale_by=1):
        self.trace_params[trace_name] = {"graticule": graticule, "scale_factor": scale_by}
        if self.readbacks_available:
            Yrange = self.row[f'{trace_name}_Yrange_readback']
            Yoffset = self.row[f'{trace_name}_Yoffset_readback']/Yrange * 8 + 4 if graticule is None else graticule
        else:
            Yrange = self.row[f'{trace_name}_Yrange']
            Yoffset = self.row[f'{trace_name}_Yoffset']/Yrange * 8 + 4 if graticule is None else graticule
        x,y = self.row['scope_timedata'], self.row[f'{trace_name}']
        if isinstance(x,numpy.ndarray) and isinstance(y,numpy.ndarray):
            ydata = y * 8/Yrange * scale_by + Yoffset
            return numpy.column_stack((x, ydata))                                                   #Significant speedup if data is kept in numpy.  It might be slightly better to use numpy views.
        else:
            ydata = [data/Yrange * 8 * scale_by + Yoffset for data in self.row[f'{trace_name}']]
            return list(zip(self.row['scope_timedata'], ydata))                                     #Kept for backwards compatability with old databases with scope data not stored as a BLOB.  This is slow.

    def marker_location(self, trace_name): # Expecting use_axes_scale of False
        try:
            graticule = self.trace_params[trace_name]["graticule"]
        except Exception as e:
            self.raise_error(trace_name, "reference marker", e)
        if self.readbacks_available:
            return 0.5 + self.row[f'{trace_name}_Yoffset_readback'] / self.row[f'{trace_name}_Yrange_readback'] if graticule is None else graticule / 8
        else:
            return 0.5 + self.row[f'{trace_name}_Yoffset'] / self.row[f'{trace_name}_Yrange'] if graticule is None else graticule / 8

    def trace_locator(self, trace_name, value=0):
        try:
            scale_factor = self.trace_params[trace_name]["scale_factor"]
        except Exception as e:
            self.raise_error(trace_name, "trace label", e)
        try:
            graticule = self.trace_params[trace_name]["graticule"]
        except Exception as e:
            self.raise_error(trace_name, "Trace Locator", e)
        if self.readbacks_available:
            if graticule is None:
                Yrange = self.row[f'{trace_name}_Yrange_readback']
                Yoffset = self.row[f'{trace_name}_Yoffset_readback']/Yrange * 8 + 4
                return value/Yrange * 8 * scale_factor + Yoffset
            else:
                return graticule + value * 8 * scale_factor / self.row[f'{trace_name}_Yrange_readback']
        else:
            if graticule is None:
                Yrange = self.row[f'{trace_name}_Yrange']
                Yoffset = self.row[f'{trace_name}_Yoffset']/Yrange * 8 + 4
                return value/Yrange * 8 * scale_factor + Yoffset
            else:
                return graticule + value * 8 * scale_factor / self.row[f'{trace_name}_Yrange']

    def trace_label(self, trace_name, display_name = None):
        try:
            scale_factor = self.trace_params[trace_name]["scale_factor"]
        except Exception as e:
            self.raise_error(trace_name, "trace label", e)
        if self.row[f'{trace_name}_units'] in ["VOLT", "AMP"]:
            trace_units = self.row[f'{trace_name}_units'][0] # Just pick up the A or the V. Manual page 278 says Return Format <units> ::= {VOLT | AMP}
        else:
            trace_units = self.row[f'{trace_name}_units'] # else just get whatever wierdo unit it is
        if self.readbacks_available:
            return f"{trace_name.replace('scope_','') if display_name is None else display_name}\n{eng_string(self.row[f'{trace_name}_Yrange_readback'] / 8 / scale_factor, fmt=':.3g', si=True)}{trace_units}/DIV"
        else:
            return f"{trace_name.replace('scope_','') if display_name is None else display_name}\n{eng_string(self.row[f'{trace_name}_Yrange'] / 8 / scale_factor, fmt=':.3g', si=True)}{trace_units}/DIV"

    def axis_info(self, xlimits=None):
        return {'xaxis_label'   : self.time_label(xlimits=xlimits),
                'xlims'         : self.time_range() if xlimits is None else xlimits,
                'ylims'         : [0,8]} # All scaling now maps to unit graticules

    def volts_per_division(self, channel_name):
        return self.row[f'{channel_name}_Yrange_readback'] / 8



def plot_waveform(y_data_column_names, db_tablename, db_filename = 'scope_data.sqlite'):
    from bokeh import colors
    from bokeh.io import curdoc
    from bokeh.layouts import layout
    from bokeh.models import Label, Toggle, Arrow, NormalHead
    from bokeh.plotting import show, output_file, figure
    
    db = sqlite_data(table_name=db_tablename, database_file=db_filename, timezone=None)
    sd = scope_data(database=db, table_name=db_tablename, where_clause='')
    output_file(filename=f'{db_tablename}.html', title = db_tablename)
    curdoc().theme = 'dark_minimal'
    axis_info = sd.axis_info()
    plot = figure(title=db_tablename, plot_width=1000, plot_height=800, x_range=axis_info['xlims'], y_range=axis_info['ylims'])
    plot = figure(title=db_tablename, width=1000, height=800, x_range=axis_info['xlims'], y_range=axis_info['ylims'])
    plot.xaxis.axis_label = axis_info['xaxis_label']
    #x ticks https://docs.bokeh.org/en/latest/docs/user_guide/styling/plots.html#customjsticker
    #plot.yaxis.axis_label = "Height (in)"


    channel_colors = {1:colors.named.gold, 2:colors.named.forestgreen, 3:colors.named.mediumblue, 4:colors.named.fuchsia}
    toggles={}
    for i, ch in enumerate(y_data_column_names):
        j = i%4+1
        ch_data = sd.trace_data(trace_name=ch, graticule=None, scale_by=1)
        ch_neatname = sd.trace_label(ch)
        #todo sd.trace_locator()??
        this_line = plot.line(x=ch_data[:,0], y=ch_data[:,1], line_color=channel_colors[j], legend_label=f"{ch_neatname}", alpha=.5)
        nh = NormalHead(fill_color=channel_colors[j], fill_alpha=0.5, line_color=channel_colors[j])
        # plot.add_layout(Arrow(end=nh, line_color=channel_colors[j], x_start=axis_info['xlims'][0]*(1-1/20)+axis_info['xlims'][1], x_end=axis_info['xlims'][0], y_start=sd.marker_location(ch), y_end=sd.marker_location(ch)))
        toggles[j] = Toggle(label=f'Show {ch_neatname}', button_type='success', active=True, background = channel_colors[j]) #background does NOTHING!
        toggles[j].js_link('active', this_line, 'visible')
    show(layout([plot], list(toggles.values())))

if __name__=='__main__':
    db_filename = input("Database filename? [data_log.sqlite]: ")
    if db_filename == "":
        db_filename = "data_log.sqlite"
    db = sqlite_data(table_name=None, database_file=db_filename, timezone=None)
    try:
        first_table = db.get_table_names(include_views=True)[0]
    except IndexError as e:
        raise Exception(f'{db_filename} contains no tables.') from e
    db_table = input(f"Database tablename? [{first_table}]: ")
    if db_table == "":
        db_table = first_table
    col_names = []
    while True:
        col_name = input(f"Y{len(col_names)+1} data column name or Enter to continue? ")
        if col_name == "":
            break
        else:
            col_names.append(col_name)
    assert len(col_names), "Cannot plot zero traces."
    plot_waveform(y_data_column_names=col_names, db_tablename=db_table, db_filename=db_filename)
