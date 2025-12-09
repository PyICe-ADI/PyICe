from bokeh.plotting import figure, show
from bokeh.layouts import column, row
from bokeh.models import (CustomJS, LinearAxis, Range1d, Select,
                          WheelZoomTool, ZoomInTool, ZoomOutTool, Span, Label)
import inspect
import sys
this_module = sys.modules[__name__]


def bind_to_base(self, base_func, *args, **kwargs):
    sig = inspect.signature(base_func)
    bound = sig.bind_partial(self, *args, **kwargs)
    bound.apply_defaults()
    return bound.arguments


class LTCPlotBokehAdapter:
    def __init__(self, *args, **kwargs):
        print(f"A call to undefined constructor of: '{type(self)}' was made with arguments: {args}, {kwargs}.")
        self._args = args
        self._kwargs = kwargs
    def __getattr__(self, name):
        # This function will be called for any undefined method/attribute
        print(f"A call to undefined method: '{type(self)}.{name}' was made.")
        def dynamic_warning_method(*args, **kwargs):
            print(f"WARNING: Ignoring call to '{name}' with arguments: {args}, {kwargs}")
            return None
        return dynamic_warning_method

class plot(LTCPlotBokehAdapter):
    '''bokeh plot adapter'''
    def __init__(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['plot'].__init__, *args, **kwargs)
        self._plotted = False #Russell notifications replot hack. To be revisited!!!!
        self._fig = figure(title=args_map['plot_title'],
                           x_range=args_map['xlims'],
                           y_range=args_map['ylims'],
                           background_fill_color="#fafafa",
                           y_axis_type="log" if args_map['logy'] else "linear",
                           x_axis_type="log" if args_map['logx'] else "linear",
                           width=1200,
                           height=1200,
                           )
        #'xaxis_label': 'FREQUENCY (MHz)', 'yaxis_label': 'AMPLITUDE ($dBV_{RMS}$) / √10Hz)',
        self._fig.yaxis.axis_label = args_map['yaxis_label']
        self._fig.xaxis.axis_label = args_map['xaxis_label']
        # self._fig.legend.location = "bottom_left"      # other options: 'top_right', 'bottom_left', etc.
        # self._fig.legend.click_policy = "hide"
        # self._fig.legend.label_text_font_size = "7pt"
        # self._fig.legend.background_fill_alpha = 0.6
        self._fig.add_tools(WheelZoomTool())

        #TODO add axis titles
        #TODO add series switch widgets
        #TODO add log toggle widgets
        #TODO add zoom controls
        #TODO plot name is "Bokeh Plot" in browser
    def add_note(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['plot'].add_note, *args, **kwargs)
        #(self, note, location=[0.05, 0.5], use_axes_scale=True, fontsize=7, axis=1, horizontalalignment="left", verticalalignment="bottom"):
    def add_trace(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['plot'].add_trace, *args, **kwargs)
        #(self, axis, data, color, marker=None, markersize=0, linestyle="-", legend="", stepped_style=False, vxline=False, hxline=False):
        unzip_data = zip(*args_map['data'])
        x_data = next(unzip_data)
        y_data = next(unzip_data)
        color = tuple(map(lambda zero_one: int(round(255*zero_one)), args_map['color']))
        self._fig.line(x=x_data, y=y_data, alpha=1, color=color, legend_label=args_map['legend'])
        #TODO line style, etc?
    def add_horizontal_line(self, *args, **kwargs):
        #(self, value, xrange=None, note=None, axis=1, color=[1,0,0]):
        args_map = bind_to_base(self, original_classes['plot'].add_horizontal_line, *args, **kwargs)
        color = tuple(map(lambda zero_one: int(round(255*zero_one)), args_map['color']))
        hline = Span(location=args_map['value'], dimension='width', line_color=color, line_width=0.2, line_dash='dashed')
        if args_map['note'] is not None:
            label = Label(x=0.1*self._fig.width, y=args_map['value'], text=args_map['note'], x_units='screen', text_font_size="6pt")
            self._fig.add_layout(label)
        self._fig.add_layout(hline)
    def add_vertical_line(self, *args, **kwargs):
        #(self, value, yrange=None, note=None, axis=1, color=[1,0,0]):
        args_map = bind_to_base(self, original_classes['plot'].add_vertical_line, *args, **kwargs)
        color = tuple(map(lambda zero_one: int(round(255*zero_one)), args_map['color']))
        vline = Span(location=args_map['value'], dimension='height', line_color=color, line_width=0.2, line_dash='dashed')
        if args_map['note'] is not None:
            label = Label(x=args_map['value'], y=0.1*self._fig.height, text=args_map['note'], y_units='screen', text_font_size="6pt")
            self._fig.add_layout(label)
        self._fig.add_layout(vline)
    def make_second_y_axis(self, yaxis_label, ylims, yminor, ydivs, logy):
        pass
    def add_legend(self, axis, location = (0,0), justification = 'lower left', use_axes_scale = False, fontsize=7):
        pass

class Page(LTCPlotBokehAdapter):
    '''bokeh Page adapter'''
    def __init__(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['Page'].__init__, *args, **kwargs)
        self._plots = []
    def create_svg(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['Page'].create_svg, *args, **kwargs)
        #(self, file_basename=None, filepath=None):
        for cnt, plt in enumerate(self._plots):
            if not plt._plotted:
                plt._plotted = True
                show(column(plt._fig))

    def add_plot(self, *args, **kwargs):
        args_map = bind_to_base(self, original_classes['Page'].add_plot, *args, **kwargs)
        plt = args_map['plot']
        plt._fig.legend.location = "bottom_left"      # other options: 'top_right', 'bottom_left', etc.
        plt._fig.legend.click_policy = "hide"
        plt._fig.legend.label_text_font_size = "7pt"
        plt._fig.legend.background_fill_alpha = 0.6
        self._plots.append(plt)
    # (   self, plot,
    #                 position        = None,     # This is if there's just one plot.
    #                 plot_sizex      = None,     # Graphs are exactly 11 pica which is 1/6 of an inch
    #                 plot_sizey      = None,     # Graphs are exactly 11 pica which is 1/6 of an inch
    #                 left_border     = 0.7,      # in inches
    #                 right_border    = 0.7,      # in inches
    #                 top_border      = 0.7,      # in inches
    #                 bottom_border   = 0.7,      # in inches
    #                 x_gap           = 1,        # in inches. LTC marcom uses 0.8 but places only individual plots anyway so this is not used for datasheet placement.
    #                 y_gap           = 1,        # in inches. LTC marcom uses 0.8 but places only individual plots anyway so this is not used for datasheet placement.
    #                 trace_width     = None      # in ???s
    #              ):
        pass
class Multipage_pdf(LTCPlotBokehAdapter):
    '''bokeh Multipage_pdf adapter'''
    def add_page(self, page):
        pass
    def create_pdf(self, file_basename, filepath=None):
        pass

original_classes = {}
def install(calling_module):
    def store_and_replace(class_name):
        original_classes[class_name] = getattr(calling_module.LTC_plot, class_name)
        setattr(calling_module.LTC_plot, class_name, getattr(this_module, class_name))
    print(f'INFO: Replacing LTCPlot calls with Bokey adapter from {this_module}')
    store_and_replace('plot')
    store_and_replace('Page')
    store_and_replace('Multipage_pdf')
