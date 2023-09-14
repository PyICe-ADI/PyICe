'''
Marcom Compliant Plot Generator

This program can be used to generate plots for general lab use or to
generate Marcom specific plots that can be imported directly into the
datasheet in SVG format.


The objects that can be created with this program are:
  1) plot
  2) Page
  3) Multipage_pdf

The basic model is simple. You create one or more plots and add things to them
like traces, histograms, legends, arrows, notes, etc. Once your plots are populated
you create one or more pages and determine how you want the plots to arrange on
each page. For instance you can create an 8.5x11 page and add 9 plots to it in
a standard 3x3 grid. You can make one big page if you want. It doesn't have to be
a standard size if you don't care what the printer does with it and it won't affect
your SVG files to Marcom. If you want to have multiple pages of plots you can
create a Mulipage_pdf and add one or more pages to it.

If you want larger plots with just one plot per page as in plot_tools.py you can
create a page per plot, add a plot to each page and add all of the pages to a
Multipage_pdf.

So to start, you'll need to create a python work file and import this program:
e.g.

::
  
   ----------- LTCXXXX_plots.py -------------- 
  |import sys                                 |
  |sys.path.append("../../../PyICe")          |
  |import LTC_plot                            |
  |    .                                      |
  |    .                                      |
  |    .                                      |
   ------------------------------------------- 

Next you want to create your plots. A generally preferable work flow would be to
create all of your plots without regard to reference on a Page or Multipage_pdf.

::
  
  G0 = LTC_plot.plot(
                      plot_title      = "EN/FBIN Thresholds",
                      plot_name       = "8709 G0",
                      xaxis_label     = "TEMPERATURE (" + DEGC + ")",
                      yaxis_label     = "FBIN CHIP ENABLE (V)",
                      xlims           = (-50, 125),
                      ylims           = (1.2, 1.4),
                      xminor          = 0,
                      xdivs           = 7,
                      yminor          = 0,
                      ydivs           = 10,
                      logx            = False,
                      logy            = False)

A plot is nothing more than a record of the plot you want to create. It doesn't
support any outputting methods itself. A plot must eventually be added to a Page
to be useful. Only a Page can be generated as an SVG file, even if there's only
one plot on the page.

The arguments of a plot instance are shown below. All plot arguments are required.

plot_title  : "string"
plot_name   : "string"
xaxis_label : "string"
yaxis_label : "string"
  Accepts control characters such as \\n to start a second line. 
  These text fields also respond to Tex formatting for subscripting
  There are a few unicode characters available in LTC_plot
  to help with greek characters and degree signs, etc. Be aware
  that the Marcom minus sign is not the same as the one you type.
  You may wan to use LTC_plot.minus.                            
xlims : (xmin, xmax)
ylims : (ymin, ymax)
  These two fields also accept python None or string "auto"
  for automatic scaling. Autoscaling is useful to view the
  data for the first time and then the final values can be
  entered later once the data is understood.
xminor : 0
  This is the number of minor X divisions per major X division.
xdivs : 7
  This is the number of major X divisions.
yminor : 0
  This is the number of minor Y divisions per major XY division.
ydivs : 10
  This is the number of major Y divisions.
logx : False
  Sets the X axis to a log scale with locators at [1,2,3,4,5,6,7,8,9].
logy : False
  Sets the Y axis to a log scale with locators at [1,2,3,4,5,6,7,8,9].

Once you have a plot you can add things to it such as:
  - add_trace()
  - add_histogram()
  - add_scatterplot()
  - add_note()
  - add_legend()
  - add_arrow()
  - make_second_y_axis()

The most common element is a trace. You can add as many traces as you like. The same is true of histograms.
You can also put traces and histograms on the same plot (for instance to show the Gaussian normal curve).

When you add a trace you have the option to specify line style and marker. Linear datasheets often use
dotted or dot dash lines for improved black and white readability but rarely if even use markers so use
them judiciously.

Valid linestyles are:
  - '-'
  - '--'
  - '-.'
  - ':'

and valid markers are:
  - ':'
  - '.'
  - ','
  - 'o'
  - 'v'
  - '^'
  - '<'
  - '>'
  - '1'
  - '2'
  - '3'
  - '4'
  - '8'
  - 's'
  - 'p'
  - '*'
  - 'h'
  - 'H'
  - '+'
  - 'x'
  - 'D'
  - 'd'
  - '|'
  - '_'
  - TICKLEFT
  - TICKRIGHT
  - TICKUP
  - TICKDOWN
  - CARETLEFT
  - CARETRIGHT
  - CARETUP
  - CARETDOWN


Please see matplotlib docs online for more details.

Trace colors currently supported are:
  - LT_RED_1
  - LT_BLUE_1
  - LT_GREEN_1
  - LT_COPPER_1
  - LT_BLACK
  - LT_COPPER_2
  - LT_RED_2
  - LT_BLUE_2
  - LT_GREEN_2
  - LT_YELLOW_2
  - LT_BLUE_2_40PCT
  - LT_RED_1_40PCT

You can make your own colors by entering a list of RGB colors (r,g,b), all of which should be between 0 and 1 rather than 0 to 255.
**This is strongly discouraged however, as it will not be in compliance with LTC standards and should not make its way to Marcom.**

add_legend takes arguments:
  - axis
  - location
  - justification
  - use_axes_scale

axis
  The axis from which the legend items have been added.
location
  Coordinates in an xy list (x, y) of where to place the legend.
  These are relative, see use_axes_scale.
justification
  Justification of the test of the legend. Accepts:
    - "best"
    - "upper right"
    - "upper left"
    - "lower left"
    - "lower right"
    - "right"
    - "center left"
    - "center right"
    - "lower center"
    - "upper center"
    - "center"
    
    
use_axes_scale:
  True means place the legend by the scale of the data values whereas False means use values from 0 to 1 representing data independent percentage of the graph size.

Notes, on the other hand, need to have coordinates given.
Both support the use_axes_scale argument which defaults to True referencing the item to the data values rather than as a percentage (0..1) of the graph limits.

Data can come from a number of sources such as a CSV file or a .sqlite database and should be a zipped list
of (x,y) values for a trace and just a list for a histogram. Consult the examples file for details.

You can also add as many notes as you like. The position of the notes can be set by either referring them
to the axes_scale, a scale relative to your data or a percentage scale (0..1) of the axes extents. The default
is to use the scale of your data. This should be easier to help you locate the notes, etc as the graticules
will more precisely help you picture where the item will be.

You can only add one legend. For each trace on a given axis, it will place a label preceded by a line stub
in the same color and width of the trace. Generally the legend will placed along side the axis to which it
belongs but you can specify where it goes.

An arrow is based on the matplotlib annotate() object and consists of a text box with an arrow emanating
from it. You control where the lower left corner of the text goes as well as the arrow tip.

If you add a second y axis you have to, once again, specify a few required items in a similar manner to when
you created the plot:
1)  yaxis_label
2)  ylims
3)  yminor
4)  ydivs
5)  logy

As you add traces and histograms you'll need to specify to which axis they belong (1 or 2).

Once you have created all of your plots you will need to add them to a page:

::

  Page1 = Page(rows_x_cols = (3, 3), page_size = (8.5, 11))

Defaults for rows_x_cols = (1, 1) and for page_size is None. If you omit the page_size
or specify None, the page will shrink to fit the plots you add to it. If, on the other
hand, you specify a page size and the plots you add to it don't quite fit, the plots
will overlap a bit. That won't matter for datasheet importation as you'll see later.
Alternately, if your plots are swimming on your page, they'll be spread out to roughly
fill the Page.

Pages support the following methods:
  1. add_plot()
  2. create_pdf()
  3. create_svg()
  4. kit_datasheet()

add_plot() has options to change the plot size on the page such as plot_sizex and
plot_sizey. These values are extremely specific to datasheets and should not be changed
if the plots are to be sent to Marcom. It's best to enter the plot instance and position
and leave the rest alone.

::

  Page1.add_plot(G01, position = 1)
  Page1.add_plot(G02, position = 2)
  Page1.add_plot(G03, position = 3)

As you add plots to the page with a given position, the plots appear on the page top to
bottom, left to right.

So a Page that was specified as 3x3 would add up to 9 plots in the following order:

::
  
   ---------------------------
  |                           |
  |   [1]     [2]     [3]     |
  |                           |
  |                           |
  |   [4]     [5]     [6]     |
  |                           |
  |                           |
  |   [7]     [8]     [9]     |
  |                           |
   ---------------------------


Or a 2x2 Page would be positioned as:

::
  
   -------------------
  |                   |
  |   [1]     [2]     |
  |                   |
  |                   |
  |   [3]     [4]     |
  |                   |
   -------------------

Pages support the following methods:
  1. create_pdf("LTCXXXX_Page1")
  2. create_svg("LTCXXXX_Page1")
  3. kit_datasheet("LTCXXXX_Page1")

Each of these takes just a file_basename. The file extension is added to match the
output.

**All output data you request is place in a newly created folder under your work area called "/plots".**

kit_datasheet() performs the following sequence for you:
  1. Creates a zip file.
  2. Creates a disposable page.
  3. Adds one plot that is found on your Page.
  4. Creates an SVG file of the disposable page and adds it to the zip file.
  5. Repeats for each plot on your Page. The disposable Page evaporates.
  6. Creates a PDF of your entire page for reference and dumps it in the zip file.

If you end up needing more than one page of plots you can add your pages to
a Multipage_pdf:

::

  LTCXXXX_typcurves = Multipage_pdf("LTCXXXX_typcurves")
  LTCXXXX_typcurves.add_page(Page1)
  LTCXXXX_typcurves.add_page(Page2)
  LTCXXXX_typcurves.kit_datasheet()

Multipage_pdfs support the methods:
  1. kit_datasheet("LTCXXXX_Page1")
  2. create_pdf("LTCXXXX_Page1")

To really get going and find more example see:

\PyICe\Examples\LTC_plot_example\LTC_plot_example.py

*** TIP ***
  If you get a warning about missing Linear fonts and you have them installed,
  try deleting: "C:\\\\Users\\\\%username%\\\\.matplotlib\\\\fontList.cache and tex.cache"

'''

import numpy as np
import matplotlib, matplotlib.ticker
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from matplotlib.ticker import FormatStrFormatter
import os, shutil, io, csv, sqlite3, math, itertools

        
class PyICe_data_base():
    def __init__(self, table_name, file_name = "data_log.sqlite"):
        print() ##############################################################
        print() #                                                            #
        print() # PyICe_data_base() from inside LTC_plot is deprecated.      #
        print() # please switch to lab_utils.sqlite_data().                  #
        print() # Contact PyICe-developers@analog.com for more information.  #
        print() # Sorry for the inconvenience.                               #
        print() #                                                            #
        print() ##############################################################

class plot(object):
    def __init__(self, plot_title, plot_name, xaxis_label, yaxis_label, xlims, ylims, xminor, xdivs, yminor, ydivs, logx, logy):
        '''A plot is just a record of what you want to plot and how you want it to look.
        It must be added to a Page before it can be exported.
        Start by creating as many plots as you like and adding data and various annotations to them.
        Once you add your plot or plots to a Page you can generate an SVG or PDF of the Page.'''
        self.plot_title         = plot_title
        self.plot_name          = plot_name
        self.xaxis_label        = xaxis_label
        self.xlims              = xlims
        self.ylims              = ylims
        self.xdivs              = xdivs
        self.xminor             = xminor
        self.logx               = logx
        self.notes              = []
        self.arrows             = []
        self.y1_axis_params     = {}
        self.y2_axis_params     = {}
        self.plot_type          = "regular"
        for y_axis_params in [self.y1_axis_params, self.y2_axis_params]:
            y_axis_params["yaxis_label"]    = yaxis_label 
            y_axis_params["ylims"]          = ylims
            y_axis_params["yminor"]         = yminor
            y_axis_params["ydivs"]          = ydivs
            y_axis_params["logy"]           = logy
            y_axis_params["autoscaley"]     = True
            y_axis_params["place_legend"]   = False
            y_axis_params["legend_loc"]     = None
            y_axis_params["trace_data"]     = []
            y_axis_params["histo_data"]     = []
        self.y1_axis_params["axis_is_used"] = True
        self.y2_axis_params["axis_is_used"] = False
        self.styles = []
        for style in ['-','--','-.',':']:
            for color in MARCOM_COLORSfracRGB:
                self.styles.append( (style,color,) )
        self.current_style_index = 0
        
    def add_trace(self, axis, data, color, marker=None, markersize=0, linestyle="-", legend="", stepped_style=False, vxline=False, hxline=False):
        data = data if not isinstance(data,zip) else list(data)
        legend = legend.replace("-","−") if legend is not None else legend
        if not (vxline or hxline or len(data)):
            print(f"\nLTC_plot WARNING: Attempt to add a trace on axis {axis} with no data has been rejected.\nNo trace will apear for this attempt.\nThe legend entry is '{legend}' if that helps. \nSorry, no more specific information is available.\n")
            return
        trace_data = {  "axis"          : axis,
                        "data"          : data,
                        "color"         : color,
                        "marker"        : marker,
                        "markersize"    : markersize,
                        "linestyle"     : linestyle,
                        "legend"        : legend,
                        "stepped_style" : stepped_style,
                        "vxline"        : vxline,
                        "hxline"        : hxline
                     }
        if axis == 1:
            self.y1_axis_params["trace_data"].append(trace_data)
        else:
            self.y2_axis_params["trace_data"].append(trace_data)

    def add_scatter(self, axis, data, color, marker='*', markersize=4, legend="", stepped_style=False, vxline=False, hxline=False):
        self.add_trace(axis=axis, data=data, color=color, marker=marker, markersize=markersize, linestyle="None", legend=legend, stepped_style=stepped_style, vxline=vxline, hxline=hxline)
            
    def add_horizontal_line(self, value, xrange=None, note=None, axis=1, color=[1,0,0]):
        '''This can be useful for annotating limit lines. It can make dotted red lines for example.'''
        axis_params = self.y1_axis_params if axis==1 else self.y2_axis_params
        ylims = self.ylims if axis==1 else self.y2_axis_params["ylims"]
        if self.xlims in [None,"auto"] and xrange is None:
            hxline = True                                       # Use automatic placement mode
            xrange0 = 0                                         # Should be irrelevant
            xrange1 = 0                                         # Should be irrelevant
            if note is not None:
                print("LTC_plot: Discarding horizontal line note, inability to locate on autoscale.")
            note = None
        elif self.xlims in [None,"auto"] and xrange is not None:         # Use the range given (wierd but whatever)
            print("LTC_plot: Requesting a horizontal line range without graph limits may affect autoscaling!")
            hxline = False                                      # Be advised this may autoscale the graph
            xrange0 = xrange[0]
            xrange1 = xrange[1]
            if ylims not in [None,"auto"] :
                text_location = [xrange[0] + 0.015*(xrange[1]-xrange[0]), value + 0.015*(ylims[1] - ylims[0])]
            else:
                if note is not None:
                    print("LTC_plot: Discarding horizontal line note, inability to locate on autoscale.")
                    note = None
        elif self.xlims not in [None,"auto"] and xrange is None:         # Best guess on the location from xlims as before
            hxline = False
            xrange0 = self.xlims[0]
            xrange1 = self.xlims[1]
            if ylims not in [None,"auto"] :
                text_location = [self.xlims[0] + 0.015*(self.xlims[1]-self.xlims[0]), value + 0.015*(ylims[1] - ylims[0])]
            else:
                if note is not None:
                    print("LTC_plot: Discarding horizontal line note, inability to locate on autoscale.")
                    note = None          
        else:#xlims is not None and xrange is not None:         # Presume the intent is to use the given xrange
            hxline = False
            xrange0 = xrange[0]
            xrange1 = xrange[1]
            if ylims not in [None,"auto"] :
                text_location = [xrange[0] + 0.015*(xrange[1]-xrange[0]), value + 0.015*(ylims[1] - ylims[0])]
            else:
                if note is not None:
                    print("LTC_plot: Discarding horizontal line note, inability to locate on autoscale.")
                    note = None
        self.add_trace(axis=axis, data=value if hxline else [(xrange0,value),(xrange1,value)], color=color, marker=None, markersize=0, linestyle="--", legend="", stepped_style=False, hxline=hxline)
        if note is not None:
            self.add_note(note=note, location=text_location, use_axes_scale=True, fontsize=3, axis=axis)

    def add_vertical_line(self, value, yrange=None, note=None, axis=1, color=[1,0,0]):
        '''This can be useful for annotating limit lines. It can make dotted red lines for example.'''
        if axis not in [1,2]:
            raise Exception("\n\nLTC_plot ERROR: AXIS MUST BE 1 or 2\n")
        axis_params = self.y1_axis_params if axis==1 else self.y2_axis_params
        if axis_params['ylims'] in [None,"auto"] and yrange is None:
            vxline = True                                                   # Use automatic placement mode
            yrange0 = 0                                                     # Should be irrelevant
            yrange1 = 0                                                     # Should be irrelevant
            if note is not None:
                print("LTC_plot: Discarding vertical line note, inability to locate on autoscale.")
                note = None
        elif axis_params['ylims'] in [None,"auto"] and yrange is not None:           # Use the range given (wierd but whatever)
            print("LTC_plot: Requesting a vertical line range without graph limits may affect autoscaling!")
            vxline = False                                                  # Be advised this may autoscale the graph
            yrange0 = yrange[0]
            yrange1 = yrange[1]
            if self.xlims not in [None,"auto"] :
                text_location = [value, yrange0-3*(yrange1-yrange0)/100]
            else:
                if note is not None:
                    print("LTC_plot: Discarding vertical line note, inability to locate on autoscale.")
                    note = None
        elif axis_params['ylims'] not in [None,"auto"]  and yrange is None:           # Best guess on the location from xlims as before
            vxline = False
            yrange0 = axis_params['ylims'][0]
            yrange1 = axis_params['ylims'][1]
            if self.xlims not in [None,"auto"] :
                text_location=[value, yrange0-3*(yrange1-yrange0)/100]
            else:
                if note is not None:
                    print("LTC_plot: Discarding vertical line note, inability to locate on autoscale.")
                    note = None          
        else:#ylims is not None and yrange is not None:                     # Presume the intent is to use the given xrange
            vxline = False
            yrange0 = yrange[0]
            yrange1 = yrange[1]
            if self.xlims not in [None,"auto"] :
                text_location = [value, yrange0-3*(yrange1-yrange0)/100]
            else:
                if note is not None:
                    print("LTC_plot: Discarding vertical line note, inability to locate on autoscale.")
                    note = None
        self.add_trace(axis=axis, data=value if vxline else [(value,yrange0),(value,yrange1)], color=color, marker=None, markersize=0, linestyle="--", legend="", stepped_style=False, vxline=vxline)
        if note is not None:
            self.add_note(note=note, location=text_location, use_axes_scale=True, fontsize=3, axis=axis)

    def add_histogram(self, axis, xdata, num_bins, color, normed=False, legend="", edgecolor="black", linewidth=0.5, alpha=1):
        histo_data = { "axis"           : axis,
                       "xdata"          : xdata,
                       "num_bins"       : num_bins,
                       "color"          : color,
                       "legend"         : legend,
                       "edgecolor"      : edgecolor,
                       "linewidth"      : linewidth,
                       "alpha"          : alpha,
                    }
        if axis == 1:
            self.y1_axis_params["histo_data"].append(histo_data)
        else:
            self.y2_axis_params["histo_data"].append(histo_data)
    def make_second_y_axis(self, yaxis_label, ylims, yminor, ydivs, logy):
        '''A second (right side) y axis is useful if two very different data sets need to be plotted against the same indepdendent axis.
        Be sure to use the same number of divisions on each y-axis to have sensible (common) graticules.'''
        self.y2_axis_params["axis_is_used"] = True
        self.y2_axis_params["yaxis_label"]  = yaxis_label
        self.y2_axis_params["ylims"]        = ylims
        self.y2_axis_params["yminor"]       = yminor
        self.y2_axis_params["ydivs"]        = ydivs
        self.y2_axis_params["logy"]         = logy
    def add_legend(self, axis, location = (0,0), justification = 'lower left', use_axes_scale = False, fontsize=7):
        '''PLace a legend on the graph. The legend labels were acquired from the legend argument in the add_trace call. Position supports data axes and absolute axes.'''
        if axis == 1:
            self.y1_axis_params["place_legend"]         = True
            self.y1_axis_params["legend_loc"]           = location
            self.y1_axis_params["legend_justification"] = justification
            self.y1_axis_params["legend_fontsize"]      = fontsize
            self.y1_axis_params["use_axes_scale"]       = use_axes_scale
        else:
            self.y2_axis_params["place_legend"]         = True
            self.y2_axis_params["legend_loc"]           = location
            self.y2_axis_params["legend_justification"] = justification
            self.y2_axis_params["legend_fontsize"]      = fontsize
            self.y2_axis_params["use_axes_scale"]       = use_axes_scale
    def add_note(self, note, location=[0.05, 0.5], use_axes_scale=True, fontsize=7, axis=1, horizontalalignment="left", verticalalignment="bottom"):
        '''Add an arbitratry note anywhere on the graph. Position supports data axes and absolute axes.'''
        self.notes.append({"note":note, "location":location, "axis":axis, "use_axes_scale":use_axes_scale, "fontsize":fontsize, "horizontalalignment":horizontalalignment, "verticalalignment":verticalalignment})
    def add_arrow(self, text, text_location, arrow_tip, use_axes_scale=True, fontsize=7):
        '''Adds a note and an arrow pointing to something. The arrow shaft emanates from the center of the note text and the arrow tip lands on the arrow top point. Both position follow either the data axes and absolute axes.'''
        self.arrows.append({    "text"          : text,
                                "text_location" : text_location,
                                "arrow_tip"     : arrow_tip,
                                "use_axes_scale": use_axes_scale,
                                "fontsize"      : fontsize
                           })
    def create_svg(self, file_basename):
        '''shortcut to create SVG for a single plot without having to construct a Page.'''
        page = Page(rows_x_cols = None, page_size = None, plot_count = 1)
        page.add_plot(plot=self)
        return page.create_svg(file_basename)
    def create_csv(self, file_basename, filepath=None, dialect='excel'):
        filepath = './csv/' if filepath is None else os.path.join(filepath,'csv')
        try:
            os.makedirs(filepath)
        except OSError:
            pass
        file_basename = os.path.join(filepath, f"{file_basename}.csv".replace(" ", "_"))

        trace_dict = {}
        max_len = 0
        for ax in (self.y1_axis_params["trace_data"], self.y2_axis_params["trace_data"]):
            for trace in ax:
                legend = trace['legend'] if len(trace['legend']) else 'UNLABELED'
                while f'{legend}_x' in trace_dict:
                    legend = f'{legend}_DUPLICATE'
                assert f'{legend}_x' not in trace_dict, f'ERROR: Duplicate CSV header label {legend}_x.'
                assert f'{legend}_y' not in trace_dict, f'ERROR: Duplicate CSV header label {legend}_y.'
                (trace_dict[f'{legend}_x'], trace_dict[f'{legend}_y'])= zip(*trace['data'])
                if len(trace_dict[f'{legend}_x']) > max_len:
                    max_len = len(trace_dict[f'{legend}_x'])
        with open(file_basename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=trace_dict.keys(), restval='', extrasaction='raise', dialect=dialect)
            writer.writeheader()
            for i in range(max_len):
                writer.writerow({k:v[i] for k,v in trace_dict.items() if len(v) > i})
            f.close()

class scope_plot(plot):
    def __init__(self, plot_title, plot_name, xaxis_label, xlims, ylims):
        '''A plot is just a record of what you want to plot and how you want it to look.
        It must be added to a Page before it can be exported.
        Start by creating as many plots as you like and adding data and various annotations to them.
        Once you add your plot or plots to a Page you can generate an SVG or PDF of the Page.
        
        The scope_plot is a special plot that is 8 graticules high by 10 graticules wide and has its x and y labels listed in units/div like an oscilloscope.'''
        self.plot_title                                 = plot_title
        self.plot_name                                  = plot_name
        self.xaxis_label                                = xaxis_label
        self.xlims                                      = xlims
        self.xdivs                                      = 10
        self.xminor                                     = None
        self.logx                                       = False
        # self.include_time_refmarkers                    = False
        self.notes                                      = []
        self.arrows                                     = []
        self.ref_markers                                = []
        self.trace_labels                               = []
        self.plot_type                                  = "scope_plot"
        self.y1_axis_params                             = {}
        self.y1_axis_params["ylims"]                    = ylims
        self.y1_axis_params["yminor"]                   = None
        self.y1_axis_params["ydivs"]                    = 8
        self.y1_axis_params["logy"]                     = False
        self.y1_axis_params["autoscaley"]               = True
        self.y1_axis_params["place_legend"]             = False
        self.y1_axis_params["legend_loc"]               = None
        self.y1_axis_params["trace_data"]               = []
        self.y1_axis_params["ref_marker_loc"]           = 0
        self.y1_axis_params["ref_marker_color"]         = LT_BLACK
        self.y1_axis_params["marker_use_axes_scale"]    = False
        self.y1_axis_params["axis_is_used"]             = True
        self.y2_axis_params                             = {}
        self.y2_axis_params["axis_is_used"]             = False
        self.include_time_refmarker_open                = False
        self.include_time_refmarker_closed              = False
        self.styles = []
        for style in ['-','--','-.',':']:
            for color in MARCOM_COLORSfracRGB:
                self.styles.append( (style,color,) )
        self.current_style_index = 0
    def add_trace(self, data, color, marker = None, markersize = 0, linestyle = "-", legend = ""):
        plot.add_trace(self, axis=1, data=data, color=color, marker=marker, markersize=markersize, linestyle=linestyle, legend=legend)
    def add_legend(self, axis=1, location=(0,0), justification='lower left', use_axes_scale=False, fontsize=7):
        plot.add_legend(self, axis=axis, location=location, justification=justification, use_axes_scale=use_axes_scale, fontsize=fontsize)
    def make_second_y_axis(self, *args, **kwargs):
        raise Exception('Second y-axis not implemented for scope plots.')
    def add_ref_marker(self, ylocation, marker_color, use_axes_scale):
        self.ref_markers.append({"ylocation" : ylocation, "marker_color" : marker_color, "use_axes_scale": use_axes_scale})
    def add_trace_label(self, trace_label, ylocation, use_axes_scale):
        self.trace_labels.append({"trace_label" : trace_label, "ylocation" : ylocation, "use_axes_scale": use_axes_scale})
    def add_time_refmarker_open(self, xlocation):
        self.include_time_refmarker_open = True
        self.time_refmarker_open_xlocation=xlocation
    def add_time_refmarker_closed(self, xlocation):
        self.include_time_refmarker_closed = True
        self.time_refmarker_closed_xlocation=xlocation
    def add_all_time_refmarkers(self, xlocation_open, xlocation_closed):
        self.add_time_refmarker_open(xlocation_open)
        self.add_time_refmarker_closed(xlocation_closed)
    def add_horizontal_line(self, value, xrange=None, note=None, color=[1,0,0]):
        xrange0 = self.xlims[0] if xrange is None else xrange[0]
        xrange1 = self.xlims[1] if xrange is None else xrange[1]
        self.add_trace(data=[(xrange0,value),(xrange1,value)], color=color, marker=None, markersize=0, linestyle="--", legend="")
        if note is not None:
            yrange0 = self.y1_axis_params['ylims'][0]
            yrange1 = self.y1_axis_params['ylims'][1]
            self.add_note(note=note, location=[xrange0 + 0.015*(xrange1-xrange0), value + 0.015*(yrange1 - yrange0)], use_axes_scale=True, fontsize=3, axis=1)
    def add_vertical_line(self, value, yrange=None, note=None, color=[1,0,0]):
        yrange0 = self.y1_axis_params['ylims'][0] if yrange is None else yrange[0]
        yrange1 = self.y1_axis_params['ylims'][1] if yrange is None else yrange[1]
        self.add_trace(data=[(value,yrange0),(value,yrange1)], color=color, marker=None, markersize=0, linestyle="--", legend="")
        if note is not None:
            self.add_note(note=note, location=[value, yrange0+0.015*(yrange1-yrange0)], use_axes_scale=True, fontsize=3, axis=1)
        
class Page():
    def __init__(self, rows_x_cols = None, page_size = None, plot_count = None):
        '''A Page containing one or more plots can be exported as a PDF or SVG.
        Alternately you can kit the page for datasheet submission.
        This is where the plots are actually "constructed" from matplotlib objects.'''
        #################################################################
        # Create the matplotlib Figure and do some datasheet setup      #
        #################################################################
        self.Figure = matplotlib.figure.Figure()
        if rows_x_cols is not None and plot_count is None:
            self.rows_x_cols = rows_x_cols
        elif rows_x_cols is None and plot_count is not None:
            self.rows_x_cols = ((plot_count-1)//3+1, plot_count if plot_count <=3 else 3)
        else:
            raise Exception('Specify exactly one of rows_x_cols or plot_count arguments. rows_x_cols should be a two-element list or tuple.')
        self.page_size      = page_size
        self.plot_list      = []
        self.page_type      = None
        self.next_position = 0
        matplotlib.rcParams['axes.linewidth']           = 0.6
        matplotlib.rcParams['font.family']              = 'Arial' #'Linear Helv Cond'
        matplotlib.rcParams['font.stretch']             = 'ultra-condensed' #'Linear Helv Cond'
        matplotlib.rcParams['text.color']               = LT_TEXT
        matplotlib.rcParams['axes.labelcolor']          = LT_TEXT
        matplotlib.rcParams['svg.fonttype']             = "none"    # Prevents characters from being converted to paths.
        matplotlib.rcParams['text.usetex']              = False     # Not Sure
        matplotlib.rcParams['mathtext.default']         = 'regular' # Prevents subscripts from changing fonts.
        matplotlib.rcParams['axes.unicode_minus']       = True
        matplotlib.mathtext.SHRINK_FACTOR               = 6.0/7.0   # Makes subscripts kind of OK
        matplotlib.mathtext.GROW_FACTOR                 = 1 / matplotlib.mathtext.SHRINK_FACTOR
    def LTC_LOG10_Formatter(self, x):
        if x >= 1:
            return str(int(x))
        else:
            return str(x)
    def add_plot(   self, plot,
                    position        = None,     # This is if there's just one plot.
                    plot_sizex      = None,     # Graphs are exactly 11 pica which is 1/6 of an inch
                    plot_sizey      = None,     # Graphs are exactly 11 pica which is 1/6 of an inch
                    left_border     = 0.7,      # in inches
                    right_border    = 0.7,      # in inches
                    top_border      = 0.7,      # in inches
                    bottom_border   = 0.7,      # in inches
                    x_gap           = 1,        # in inches. LTC marcom uses 0.8 but places only individual plots anyway so this is not used for datasheet placement.
                    y_gap           = 1,        # in inches. LTC marcom uses 0.8 but places only individual plots anyway so this is not used for datasheet placement.
                    trace_width     = None      # in ???s
                 ):
        #################################################################
        # Create subplots                                               #
        #################################################################
        if self.page_type is None:
            self.page_type = plot.plot_type
        elif self.page_type != plot.plot_type:
            raise Exception("\n\n\n**************************************************\nPlots of different types not allowed on same page.\nPlease combine only common plot types per page.\n**************************************************\n\n\n")
        if position is None:
            self.next_position += 1
        else:
            self.next_position = position
        graph = self.Figure.add_subplot(self.rows_x_cols[0], self.rows_x_cols[1], self.next_position)
        self.plot_list.append(plot)
        rows, columns = self.rows_x_cols
        if plot_sizex is None:
            plot_sizex = 11.0/6.0 # Graphs are exactly 11 pica which is 1/6 of an inch
        else:
            plot_sizex =  float(plot_sizex)
        if plot_sizey is None:
            if plot.plot_type == "scope_plot":
                plot_sizey  = float(8.8/6.0) # Graphs are exactly 11x8.8 pica which make perfect squares on a 10x8 grid. Bob Reay's tool uses 8.6667 pica. Not sure why.
            else:
                plot_sizey = 11.0/6.0 # Graphs are exactly 11 pica which is 1/6 of an inch
        else:
            plot_sizey = float(plot_sizey)
        if trace_width is None:
            if plot.plot_type == "scope_plot":
                trace_width = 0.6
            else:
                trace_width = 1.2
        left_border     =  float(left_border)
        right_border    =  float(right_border)
        top_border      =  float(top_border)
        bottom_border   =  float(bottom_border)
        x_gap           =  float(x_gap)
        y_gap           =  float(y_gap)
        if self.page_size is not None:
            x_gap           = (self.page_size[0] - columns * plot_sizex) / (columns + 1)
            y_gap           = (self.page_size[1] - rows * plot_sizey) / (rows + 1)
            left_border     = x_gap
            right_border    = x_gap
            top_border      = y_gap
            bottom_border   = y_gap
            x_total         = self.page_size[0]
            y_total         = self.page_size[1]
        else:
            x_total = left_border + right_border + plot_sizex * columns + x_gap * (columns - 1)
            y_total = bottom_border + top_border + plot_sizey * rows + y_gap * (rows - 1)
        left        = left_border / x_total
        right       = (x_total - right_border) / x_total
        bottom      = bottom_border / y_total
        top         = (y_total - top_border) / y_total
        hspace      = y_gap / plot_sizey # hspace and wspace are percentages of a plot scale
        wspace      = x_gap / plot_sizex # for example, wspace = 1 makes gaps the size of the x dimension of a plot
        self.Figure.set_size_inches(x_total, y_total)
        graph.figure.subplots_adjust(left = left, right = right, bottom = bottom, top = top, wspace = wspace, hspace = hspace)
        graph.set_axisbelow(True) # Puts data in front of axes
        try:
            graph.set_title(plot.plot_title, fontsize = 9.5, fontweight = "bold", color = 'black', loc = "left")
        except:
            graph.set_title(plot.plot_title, fontsize = 9.5, fontweight = "bold", color = 'black')
            print("\nYou have an older version of matplotlib, consider upgrading to winpython 2.7.6.4\n")
        if plot.plot_type == "scope_plot":
            graph.axes.get_xaxis().set_ticklabels([]) # Kill the conventional X axis labels
            graph.axes.get_yaxis().set_ticklabels([]) # Kill the conventional Y axis labels
            #Add X label back in as text
            note_props = dict(boxstyle = 'square, pad = 0.125', facecolor = 'white', edgecolor = "white", alpha = 1)
            graph.text(0.4, -0.02, plot.xaxis_label, fontsize = 7, transform = graph.transAxes, horizontalalignment = 'left', verticalalignment = 'top', bbox = note_props)
            #Add Y label back in as text
            # graph.text(-0.02, 0.4, plot.y1_axis_params["yaxis_label"], fontsize = 7, transform = graph.transAxes, horizontalalignment = 'right', verticalalignment = 'bottom', bbox = note_props)
        else:
            graph.set_xlabel(plot.xaxis_label, fontsize = 7)
            graph.set_ylabel(plot.y1_axis_params["yaxis_label"], fontsize = 7)
        note_props = dict(boxstyle = 'square, pad = 0.125', facecolor = 'white', edgecolor = "white", alpha = 1)
        if plot.plot_type == "scope_plot":
            for trace_label in plot.trace_labels:
                if trace_label["use_axes_scale"] == True:
                    coordinate_system = graph.transData
                    x = plot.xlims[0] - 0.02 * (plot.xlims[1] - plot.xlims[0])
                    y = trace_label["ylocation"]
                else:
                    coordinate_system = graph.transAxes
                    x = -0.04
                    y = trace_label["ylocation"]
                graph.text(x, y, trace_label["trace_label"], fontsize = 5, transform = coordinate_system, horizontalalignment = "right", verticalalignment = 'center', bbox = note_props)
        #################################################################
        # Add plot_name in lower right corner                           #
        #################################################################
        plotname_props = dict(boxstyle = 'square', facecolor = 'white', edgecolor = "white", alpha = 1)
        graph.text(x = 1, y = -0.2, s = plot.plot_name, fontsize = 4, transform = graph.transAxes, verticalalignment = 'top', horizontalalignment = 'right', bbox = plotname_props)
        #############################################################################################
        # Deal with second axis first (seems to keep first axis tick marks from coming back)        #
        #############################################################################################
        if plot.y2_axis_params["axis_is_used"]:
            twin = graph.twinx()
            if plot.plot_type == "scope_plot":
                twin.axes.get_yaxis().set_ticklabels([]) # Kill the conventional Y axis labels
                #Add Y label back in as text
                # note_props = dict(boxstyle = 'square, pad = 0.125', facecolor = 'white', edgecolor = "white", alpha = 1)
                # twin.text(1.02, 0.4, plot.y2_axis_params["yaxis_label"], fontsize = 7, transform = twin.transAxes, horizontalalignment = 'left', verticalalignment = 'bottom', bbox = note_props)
            else:
                twin.set_ylabel(plot.y2_axis_params["yaxis_label"], fontsize = 7, rotation = -90)
            twin.yaxis.labelpad = 17 # TODO, this should be a function of the number of digits in the axes numbers
            for label in twin.yaxis.get_majorticklabels():
                label.set_fontsize(7)
            if plot.y2_axis_params["logy"]:
                twin.set_yscale('log')
                twin.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: self.LTC_LOG10_Formatter(x)))
                if plot.y2_axis_params["yminor"] != 0:
                    twin.yaxis.set_minor_locator(matplotlib.ticker.LogLocator(subs = [2,3,4,5,6,7,8,9]))
                else:
                    twin.yaxis.set_minor_locator(matplotlib.ticker.LogLocator(subs = []))
            else:
                if plot.plot_type == "regular":
                    twin.get_yaxis().get_major_formatter().set_useOffset(False)
                    twin.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(plot.y2_axis_params["ydivs"] + 1))
                    if plot.y2_axis_params["yminor"] not in [None, 0]:
                        twin.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(plot.y2_axis_params["yminor"]))
            if plot.y2_axis_params["ylims"] not in [None, "auto"]:
                plot.y2_axis_params["autoscale"] = False
                twin.set_ylim(ymin = plot.y2_axis_params["ylims"][0], ymax = plot.y2_axis_params["ylims"][1])
            else:
                plot.y2_axis_params["autoscaley"] = True
            for tic in twin.yaxis.get_major_ticks():
                tic.tick1line.set_visible(False)
            for tic in twin.yaxis.get_minor_ticks():
                tic.tick1line.set_visible(False)
            for tic in twin.yaxis.get_major_ticks():
                tic.tick1line.set_visible(False)
        #################################################################
        # Deal with first axis limits                                   #
        #################################################################
        if plot.xlims in [None, "auto"]:
            autoscalex = True
        else:
            autoscalex = False
            graph.axis(xmin = plot.xlims[0], xmax = plot.xlims[1])
        if plot.y1_axis_params["ylims"] in [None, "auto"]:
            plot.y1_axis_params["autoscaley"] = True
        else:
            plot.y1_axis_params["autoscaley"] = False
            graph.axis(ymin = plot.y1_axis_params["ylims"][0], ymax = plot.y1_axis_params["ylims"][1])
        if plot.logx:
            graph.set_xscale('log')
            graph.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: self.LTC_LOG10_Formatter(x)))
            if plot.xminor != 0:
                graph.xaxis.set_minor_formatter(FormatStrFormatter(""))
                graph.xaxis.set_minor_locator( matplotlib.ticker.LogLocator(subs=(2,3,4,5,6,7,8,9), numticks=None))
            else:
                graph.xaxis.set_minor_locator( matplotlib.ticker.LogLocator(subs=[], numticks=None))
        else:
            graph.xaxis.set_major_locator(matplotlib.ticker.LinearLocator(plot.xdivs + 1))
            if plot.plot_type == "regular":
                graph.get_xaxis().get_major_formatter().set_useOffset(False)
                if plot.xminor not in [None, 0]:
                    graph.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(plot.xminor))
        if plot.y1_axis_params["logy"]:
            graph.set_yscale('log')
            graph.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, pos: self.LTC_LOG10_Formatter(x)))
            if plot.y1_axis_params["yminor"] != 0:
                graph.yaxis.set_minor_locator(matplotlib.ticker.LogLocator(base=10.0, subs=(0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9), numticks=None))
                graph.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            else:
                graph.yaxis.set_minor_locator(matplotlib.ticker.LogLocator(subs = []))
        else:
            if plot.plot_type == "regular":
                graph.get_yaxis().get_major_formatter().set_useOffset(False)
            graph.yaxis.set_major_locator(matplotlib.ticker.LinearLocator(plot.y1_axis_params["ydivs"] + 1))
            if plot.y1_axis_params["yminor"] not in [None, 0]:
                graph.yaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(plot.y1_axis_params["yminor"]))
        if plot.plot_type == "scope_plot":
            grid_color = LT_SCOPE_GRID
        else:
            grid_color = LT_GRID
        graph.grid(visible = True, which = 'both', color = grid_color, linestyle='-', linewidth = 0.35)
        graph.tick_params(axis='both', colors=LT_GRID, gridOn=True, tick1On=False, tick2On=False, labelsize=7, labelcolor=LT_TEXT)
        if plot.plot_type == "scope_plot":
            TIC_LENGTH = 0.00644 # percentage of graph width
            # Make my own Y axis tics manually
            for major in range(8): # 0..7
                for minor in range(1,5): # 1..4
                    line = [(0.5 - TIC_LENGTH, major/8. + minor/40.), (0.5 + TIC_LENGTH, major/8. + minor/40.)]
                    (line_xs, line_ys) = list(zip(*line))
                    graph.add_line(Line2D(line_xs, line_ys, linewidth=0.35, color=LT_SCOPE_GRID, transform=graph.transAxes))
            # Make my own X axis tics manually
            for major in range(10): # 0..9
                for minor in range(1,5): # 1..4
                    line = [(major/10. + minor/50., 0.5 - TIC_LENGTH), ( major/10. + minor/50., 0.5 + TIC_LENGTH)]
                    (line_xs, line_ys) = list(zip(*line))
                    graph.add_line(Line2D(line_xs, line_ys, linewidth=0.35, color=LT_SCOPE_GRID, transform=graph.transAxes))
        for tic in graph.xaxis.get_major_ticks():
            tic.tick1line.set_visible(False)
        for tic in graph.xaxis.get_minor_ticks():
            tic.tick1line.set_visible(False)
        #################################################################
        # Add the data                                                  #
        #################################################################
        plot.y1_axis_params["axis"] = graph
        if plot.y2_axis_params["axis_is_used"]:
            plot.y2_axis_params["axis"] = twin
        for y_axis_params in [plot.y1_axis_params, plot.y2_axis_params]:
            if y_axis_params["axis_is_used"]:
                for trace in y_axis_params["trace_data"]:
                    if trace["vxline"]:
                        y_axis_params["axis"].axvline(  x           = trace["data"],
                                                        color       = trace["color"],
                                                        linewidth   = trace_width,
                                                        linestyle   = trace["linestyle"]
                                                        )
                    elif trace["hxline"]:
                        y_axis_params["axis"].axhline(  y           = trace["data"],
                                                        color       = trace["color"],
                                                        linewidth   = trace_width,
                                                        linestyle   = trace["linestyle"]
                                                        )
                    else:
                        if isinstance(trace['data'],np.ndarray) and not isinstance(trace['data'],np.recarray):
                            unzip = trace['data'].T                 #Numpy views may be slightly faster.  Also, views could be used to also handle recarray coming in, instead of list,zip
                            x = unzip[0]
                            y = unzip[1]
                        else:
                            x,y = zip(*trace["data"])
                        if trace["stepped_style"]:
                            y_axis_params["axis"].step(         x,
                                                                y,
                                                color           = trace["color"],
                                                linewidth       = trace_width,
                                                marker          = trace["marker"],
                                                markersize      = trace["markersize"],
                                                label           = trace["legend"],
                                                linestyle       = trace["linestyle"],
                                                alpha           = 1,
                                                scalex          = y_axis_params["autoscaley"],
                                                scaley          = y_axis_params["autoscaley"],
                                                where           ='post')
                        else:
                            y_axis_params["axis"].plot(         x,
                                                                y,
                                                color           = trace["color"],
                                                linewidth       = trace_width,
                                                marker          = trace["marker"],
                                                markersize      = trace["markersize"],
                                                label           = trace["legend"],
                                                linestyle       = trace["linestyle"],
                                                alpha           = 1,
                                                scalex          = y_axis_params["autoscaley"],
                                                scaley          = y_axis_params["autoscaley"])
                if plot.plot_type != "scope_plot":
                    for histogram in y_axis_params["histo_data"]:
                        y_axis_params["axis"].hist(  x  = histogram["xdata"],
                                            bins        = histogram["num_bins"],
                                            range       = None,
                                            weights     = None,
                                            cumulative  = False,
                                            bottom      = None,
                                            histtype    = 'bar',
                                            align       = 'mid',
                                            orientation = 'vertical',
                                            rwidth      = None,
                                            log         = False,
                                            color       = histogram["color"],
                                            label       = histogram["legend"],
                                            stacked     = False,
                                            linewidth   = histogram["linewidth"],
                                            alpha       = histogram["alpha"],
                                            edgecolor   = histogram["edgecolor"])
        #################################################################
        # Place the legends                                             #
        #################################################################
                if y_axis_params["place_legend"]:
                    if y_axis_params == plot.y1_axis_params:
                        if plot.y1_axis_params["use_axes_scale"]:
                            coordinate_system = graph.transData
                        else:
                            coordinate_system = graph.transAxes
                    if y_axis_params == plot.y2_axis_params:
                        if plot.y2_axis_params["use_axes_scale"]:
                            coordinate_system = graph.transData
                        else:
                            coordinate_system = graph.transAxes
                    legend = y_axis_params["axis"].legend(frameon=True, fontsize=y_axis_params["legend_fontsize"], loc=y_axis_params["legend_justification"], bbox_to_anchor=y_axis_params["legend_loc"], framealpha=1, borderpad=0.25, bbox_transform=coordinate_system)
                    legend.get_frame().set_linewidth(0)
        #################################################################
        # Add the reference marker (scope_plot only)                    #
        #################################################################
                if plot.plot_type == "scope_plot":
                    marker_x_offset = 0.038
                    marker = "►"
                    for ref_marker in plot.ref_markers:
                        if ref_marker["use_axes_scale"]:
                            coordinate_system = graph.transData
                            # if ref_marker['axis'] == 1:
                            x = plot.xlims[0] - marker_x_offset * (plot.xlims[1] - plot.xlims[0])
                            y = ref_marker["ylocation"] - 0.03 / 8 * (plot.y1_axis_params['ylims'][1] - plot.y1_axis_params['ylims'][0])
                            # marker = u"►"
                            # else: # must be second y axis
                                # x = plot.xlims[1] + marker_x_offset * (plot.xlims[1] - plot.xlims[0]) # Not sure why offset is needed, text arrow not centered with its bbox?
                                # y = ref_marker["ylocation"] - 0.03 / 8 * (plot.y2_axis_params['ylims'][1] - plot.y2_axis_params['ylims'][0])
                                # marker = u"◄"
                        else: # must be absolute scale (0 - 1)
                            coordinate_system = graph.transAxes
                            # if ref_marker['axis'] == 1:
                            x = -marker_x_offset
                            # marker = u"►"
                            # else: # must be second y axis
                                # x = 1 - marker_x_offset # Not sure why offset is needed, text arrow not centered with its bbox?
                                # marker = u"◄"
                            y = ref_marker["ylocation"] - 0.0038                            # Not sure why offset is needed, text arrow not centered with its bbox?
                        note_props = dict(boxstyle = 'square, pad = 0.125', facecolor = 'white', edgecolor = "white", alpha = 0)
                        color = ref_marker["marker_color"]
                        graph.text(x, y, marker, fontsize = 5, color = color, family = 'Arial', transform = coordinate_system, horizontalalignment = 'left', verticalalignment = 'center', bbox = note_props)
        #################################################################
        # Add the time reference markers (scope_plot only)              #
        #################################################################
                if plot.plot_type == "scope_plot" and plot.include_time_refmarker_open:
                    x = plot.time_refmarker_open_xlocation
                    y = ref_marker["ylocation"] - 0.03 / 8 * (plot.y1_axis_params['ylims'][1] - plot.y1_axis_params['ylims'][0])
                    y = plot.y1_axis_params['ylims'][1]*0.995
                    note_props = dict(boxstyle='square, pad=0.125', facecolor='white', edgecolor="white", alpha=0)
                    graph.text(x, y, "▽", fontsize = 5, color = [0,0,0], family = 'DejaVu Sans', transform = graph.transData, horizontalalignment = 'center', verticalalignment = 'bottom', bbox = note_props)
                if plot.plot_type == "scope_plot" and plot.include_time_refmarker_closed:
                    x = plot.time_refmarker_closed_xlocation
                    y = plot.y1_axis_params['ylims'][1]*0.995
                    note_props = dict(boxstyle='square, pad=0.125', facecolor='white', edgecolor="white", alpha=0)
                    graph.text(x, y, "▼", fontsize = 5, color = [0,0,0], family = 'DejaVu Sans', transform = graph.transData, horizontalalignment = 'center', verticalalignment = 'bottom', bbox = note_props) 
        #################################################################
        # Add the notes                                                 #
        #################################################################
        note_props = dict(boxstyle="square, pad=0.125", facecolor="white", edgecolor="white", alpha=1)
        for note_dict in plot.notes:
            note    = note_dict["note"].replace("-","-")
            x       = note_dict["location"][0]
            y       = note_dict["location"][1]
            if note_dict["axis"] == 1:
                if note_dict["use_axes_scale"]:
                    coordinate_system = graph.transData
                else:
                    coordinate_system = graph.transAxes
                graph.text(x, y, note, fontsize=note_dict["fontsize"], transform=coordinate_system, horizontalalignment=note_dict["horizontalalignment"], verticalalignment=note_dict["verticalalignment"], bbox=note_props)
            elif note_dict["axis"] == 2:
                if note_dict["use_axes_scale"]:
                    coordinate_system = twin.transData
                else:
                    coordinate_system = twin.transAxes
                twin.text(x, y, note, fontsize=note_dict["fontsize"], transform=coordinate_system, horizontalalignment=note_dict["horizontalalignment"], verticalalignment=note_dict["verticalalignment"], bbox=note_props)
            else:
                print(f"An LTC_plot error occured attempting to add a note to axis {axis}, please contact Steve Martin with this example.")
        #################################################################
        # Add the arrows (matplotlib "annotation")                      #
        #################################################################
        # White Stripe, useless arrowhead
        arrowprops1 = dict(arrowstyle    = "-|>, head_length=0, head_width=1e-37",
                                connectionstyle = "arc3, rad = 0",
                                facecolor       = "white",
                                edgecolor       = "white",
                                linewidth       = 1.4
                                )
        # Main arrow and head
        arrowprops2 = dict(arrowstyle    = "-|>, head_length=0.8, head_width=0.24",
                                connectionstyle = "arc3, rad = 0",
                                facecolor       = "black",
                                edgecolor       = "white",
                                linewidth       = 0
                                )
        # Offset white arrow over top to make the "barb"
        arrowprops3 = dict(arrowstyle    = "-|>, head_length=0.2, head_width=0.31",
                                connectionstyle = "arc3, rad = 0",
                                facecolor       = "white",
                                edgecolor       = "black",
                                linewidth       = 0,
                                shrinkA         = 0,
                                shrinkB         = 6.5,
                                alpha           = 1 # change this to barb arrow.
                                )
        # Rebuild black line, skip arrow head
        arrowprops4 = dict(arrowstyle    = "-|>, head_length=0, head_width=1e-37",
                                connectionstyle = "arc3, rad = 0",
                                facecolor       = "black",
                                edgecolor       = "black",
                                linewidth       = 0.3,
                                shrinkA         = 0,
                                shrinkB         = 5
                                )
        arrowprops = []
        arrowprops.append(arrowprops1)
        arrowprops.append(arrowprops2)
        arrowprops.append(arrowprops3)
        arrowprops.append(arrowprops4)
        bbox = dict(boxstyle            = "square, pad = -0.05",
                    facecolor           = "white",
                    edgecolor           = "white")
        for arrow_dict in plot.arrows:
            coordinate_system = "data" if arrow_dict["use_axes_scale"] else "axes fraction"
            for arrowprop in arrowprops:
                graph.annotate( arrow_dict["text"],
                                xy          = arrow_dict["arrow_tip"],
                                xycoords    = coordinate_system,
                                xytext      = arrow_dict["text_location"],
                                textcoords  = coordinate_system,
                                arrowprops  = arrowprop,
                                bbox        = bbox,
                                size        = arrow_dict["fontsize"])

    def create_svg(self, file_basename=None, filepath=None):
        FigureCanvasSVG(self.Figure)
        figdata = io.StringIO()
        self.Figure.savefig(figdata, format="svg")
        output = figdata.getvalue().replace("Linear Helv Cond", "LinearHelvCond").replace("font-size:9.5px;font-style:normal", "font-size:9.5px;font-weight:bold").replace("font-size:8.14285714286px;font-style:bold", "font-size:8.14285714286px;font-weight:bold").replace("font-size:9.5px;font-style:bold", "font-size:9.5px;font-weight:bold").encode("utf-8")
        if file_basename is not None:
            filepath = './plots/' if filepath is None else os.path.join(filepath,'plots')
            try:
                os.makedirs(filepath)
            except OSError:
                pass
            file_basename = os.path.join(filepath,"{}.svg".format(file_basename).replace(" ", "_"))
            output_file = open(file_basename, 'wb')
            output_file.write(output)
            output_file.close()
        return output
    def create_pdf(self, file_basename, filepath=None):
        filepath = './plots/' if filepath is None else os.path.join(filepath,'plots')
        try:
            os.makedirs(filepath)
        except OSError:
            pass
        file_basename = os.path.join(filepath,"{}.pdf".format(file_basename).replace(" ", "_"))
        FigureCanvasPdf(self.Figure)
        self.Figure.savefig(file_basename, format="pdf")
    def kit_datasheet(self, file_basename = "datasheet_kit"):
        filepath = '{}\\'.format(file_basename)
        try:
            os.makedirs('.\\plots\\' + filepath)
        except OSError:
            pass
        print("\nKitting datasheet plots in .\\plots\\\n")
        for plot in self.plot_list:
            plot_name = "{}".format(plot.plot_name).replace(" ", "_")
            DummyPage = Page(rows_x_cols = (1, 1))
            DummyPage.add_plot(plot)
            DummyPage.create_svg(filepath + plot_name)
        self.create_pdf('\\{}\\PDFView'.format(file_basename))
        shutil.make_archive('.\\plots\\{}'.format(file_basename), 'zip', '.\\plots\\' + filepath)
        shutil.rmtree('.\\plots\\{}'.format(file_basename))
        print("\nWrote file: {}.zip\n".format(file_basename))
        
class Multipage_pdf():
    '''Add one or more Pages to a Multipage_pdf to keep your page sizes manageable (such as 8.5x11).
    Multipage_pdf also support kit_datasheet().'''
    def __init__(self):
        self.page_list = []
    def add_page(self, page):
        FigureCanvasPdf(page.Figure)
        self.page_list.append(page)
    def create_pdf(self, file_basename):
        filepath = '.\\plots\\'
        filename = filepath + "{}.pdf".format(file_basename).replace(" ", "_")
        try:
            os.makedirs(filepath)
        except OSError:
            pass
        self.pdf_file = PdfPages(filename)
        for page in self.page_list:
            self.pdf_file.savefig(page.Figure)
        self.pdf_file.close()
    def kit_datasheet(self, file_basename = "datasheet_kit"):
        filepath = 'datasheet_kit\\'
        try:
            os.makedirs('.\\plots\\' + filepath)
        except OSError:
            pass
        print("\nKitting datasheet plots in .\\plots\\\n")
        for page in self.page_list:
            for plot in range(len(page.plot_list)):
                plot_name = "{}".format(page.plot_list[plot].plot_name).replace(" ", "_")
                DummyPage = Page(rows_x_cols = (1, 1))
                DummyPage.add_plot(page.plot_list[plot])
                DummyPage.create_svg(filepath + plot_name)
        self.create_pdf("\\datasheet_kit\\PDFView")
        shutil.make_archive('.\\plots\\{}'.format(file_basename), 'zip', '.\\plots\\' + filepath)
        shutil.rmtree('.\\plots\\datasheet_kit')
        print("\nWrote file: {}.zip\n".format(file_basename))
        
class color_gen(object):
    '''Color yielding generator. Returns a new color each time an instance is called'''
    def __init__(self, rollover=True):
        '''set rollover False to cause an IndexError exception when colors are exhausted'''
        self.colors = MARCOM_COLORSfracRGB[:]
        self.reset()
        self.rollover = rollover
    def __call__(self):
        color = self.colors[self.index]
        self.index += 1
        if self.rollover:
            self.index %= len(self.colors)
        return color
    def reset(self):
        '''start color sequence over'''
        self.index = 0

def list_markers():
    '''Valid linestyles are ['-' '--' '-.' ':' 'None' ' ' '']
    Valid markers are [':' '.' ',' 'o' 'v' '^' '<' '>' '1' '2' '3' '4' '8' 's' 'p' '*' 'h' 'H' '+' 'x' 'D' 'd' '|' '_' TICKLEFT TICKRIGHT TICKUP TICKDOWN CARETLEFT CARETRIGHT CARETUP CARETDOWN]'''
    print()
    print("Valid markers are: " + "[':' '.' ',' 'o' 'v' '^' '<' '>' '1' '2' '3' '4' '8' 's' 'p' '*' 'h' 'H' '+' 'x' 'D' 'd' '|' '_' TICKLEFT TICKRIGHT TICKUP TICKDOWN CARETLEFT CARETRIGHT CARETUP CARETDOWN]")
    print()
    print("Valid linestyles are: " + "['-' '--' '-.' ':' 'None' ' ' '']")
    print()
def smooth(data, window = 5):
    print("##########################################################")
    print("#                                                        #")
    print("#  WARNING, LTC_plot.smooth() is deprecated!!!           #")
    print("#  Please create a lab_utils.ordered_pair()              #")
    print("#  and use its better supported smoothing feature.       #")
    print("#                                                        #")
    print("##########################################################")
    # exit()
    # data = window * [data[0]] + list(data) + window * [data[-1]]            # Extend data end points left/right
    # data = np.convolve(data, np.ones(int(window))/float(window), 'same')    # to assist running average algorithm
    # data = data.ravel().tolist()                                            # Convert array to list
    # data[0:window] = []                                                     # Strip off left padding
    # data[len(data)-window:] = []                                            # Strip off right padding
    # return data
def smooth_y_vector(data, window = 5):
    print("##########################################################")
    print("#                                                        #")
    print("#  WARNING, LTC_plot.smooth_y_vector() is deprecated!!!  #")
    print("#  Please create a lab_utils.ordered_pair()              #")
    print("#  and use its better supported smoothing feature.       #")
    print("#                                                        #")
    print("##########################################################")
    # xdata, ydata = zip(*data)
    # ydata = smooth(ydata, window)
    # return zip(xdata, ydata)
def data_from_file(filename):
    x = []
    y = []
    input_file = open(filename, 'r')
    for line in input_file:
        x.append(float(line.split(",")[0]))
        y.append(float(line.split(",")[1]))
    input_file.close()
    return list(zip(x,y))
def CMYK_to_fracRGB(CMYK):
    R = (1 - CMYK[0]) * (1 - CMYK[3])
    G = (1 - CMYK[1]) * (1 - CMYK[3])
    B = (1 - CMYK[2]) * (1 - CMYK[3])
    return (R,G,B)
def fracRGB_to_CMYK(RGB):
    C = 1 - RGB[0]
    M = 1 - RGB[1]
    Y = 1 - RGB[2]
    K = min(C,M,Y)
    if ( K == 1 ): # Really Black
        C = 0
        M = 0
        Y = 0
    else:
       C = ( C - K ) / ( 1 - K )
       M = ( M - K ) / ( 1 - K )
       Y = ( Y - K ) / ( 1 - K )
    return (C,M,Y,K)
def webRGB_to_fracRGB(webRGB):
    R = int(webRGB[0:2],16) / 255.0
    G = int(webRGB[2:4],16) / 255.0
    B = int(webRGB[4:6],16) / 255.0
    return (R,G,B)
def webRGB_to_RGB(webRGB):
    R = int(webRGB[0:2],16)
    G = int(webRGB[2:4],16)
    B = int(webRGB[4:6],16)
    return (R,G,B)
def RGB_to_webRGB(RGB):
    R = hex(int(RGB[0]))
    G = hex(int(RGB[1]))
    B = hex(int(RGB[2]))
    return (R,G,B)
def fracRGB_to_RGB(fracRGB):
    R = int(round(fracRGB[0] * 255.0))
    G = int(round(fracRGB[1] * 255.0))
    B = int(round(fracRGB[2] * 255.0))
    return (R,G,B)
def RGB_to_fracRGB(RGB):
    R = RGB[0] / 255.0
    G = RGB[1] / 255.0
    B = RGB[2] / 255.0
    return (R,G,B)
def fracRGB_to_webRGB(fracRGB):
    return RGB_to_webRGB(fracRGB_to_RGB(fracRGB))
    
def _escape_attrib_reversal(s):
    # Don't know why SVG backend does this, need to reverse it to include html entities.
    # 12/26/2016 Bill had complained that he couldn't use & character which as true because the I had the next line uncommented.
    # This was here to accommodate html entities exactly such as include and & but in retrospect this was a bad idea.
    # It's easier to just declare the text unicode by preceding the text with a u such as u"Ω" rather than &#937;.
    # s = s.replace("&amp;", "&")
    # s = s.replace(u"&apos;", u"'")
    # s = s.replace(u"&quot;", u"\"")
    # s = s.replace(u"&lt;", u"<")
    # s = s.replace(u"&gt;", u">")
    return s
    
# These are the Reay colors and they don't match the CMYK values using the simple transforms above.
# They look like they were pulled out of the "GSM Complete Book 0315.pdf" with a color picker program like pain.
# I found them to be with a few codes using that method. The spec doesn't have RGB values for the secondary colors
# so I have Reay's colors here.
# Bob also had the text color and black trace color as 231f20 which is kind of grey.
REAY_COLORS =   ["900027", "3a52a4", "36864b", "b57233", "000000", "da2031", "cdb33c", "537ebc", "cc7b4a", "40ad48"]
MARCOM_COLORS = ["990033", "336699", "339933", "996633", "000000"]
MARCOM_COLORSfracRGB = [webRGB_to_fracRGB(color) for color in MARCOM_COLORS]

# The CMYK values are included here just for reference. They come from the document "LT Graph Color Palette and Styles.pdf"
LT_RED_1        = webRGB_to_fracRGB(MARCOM_COLORS[0])   # CMYK_to_RGB([0.00,   1.00,   0.65,   0.47])
LT_BLUE_1       = webRGB_to_fracRGB(MARCOM_COLORS[1])   # CMYK_to_RGB([0.88,   0.77,   0.00,   0.00])
LT_GREEN_1      = webRGB_to_fracRGB(MARCOM_COLORS[2])   # CMYK_to_RGB([0.80,   0.25,   0.90,   0.10])
LT_COPPER_1     = webRGB_to_fracRGB(MARCOM_COLORS[3])   # CMYK_to_RGB([0.24,   0.58,   0.92,   0.09])
LT_BLACK        = webRGB_to_fracRGB(MARCOM_COLORS[4])   # CMYK_to_RGB([0.00,   0.00,   0.00,   1.00])
LT_GREEN_2      = webRGB_to_fracRGB(REAY_COLORS[9])     # CMYK_to_RGB([0.75,   0.05,   1.00,   0.00])
LT_COPPER_2     = webRGB_to_fracRGB(REAY_COLORS[8])     # CMYK_to_RGB([0.20,   0.60,   0.80,   0.00])
LT_BLUE_2       = webRGB_to_fracRGB(REAY_COLORS[7])     # CMYK_to_RGB([0.70,   0.45,   0.01,   0.01])??
LT_YELLOW_2     = webRGB_to_fracRGB(REAY_COLORS[6])     # CMYK_to_RGB([0.22,   0.25,   0.92,   0.00])
LT_RED_2        = webRGB_to_fracRGB(REAY_COLORS[5])     # CMYK_to_RGB([0.10,   1.00,   0.90,   0.00])
LT_BLUE_2_40PCT = RGB_to_fracRGB([187, 204, 228])       # Use for histograms
LT_RED_1_40PCT  = RGB_to_fracRGB([228, 192, 187])       # Use for histograms
LT_GRID         = CMYK_to_fracRGB([0, 0, 0, 0.8])       # This comes out as #333333 whereas Bob Reay's value is #323232
LT_SCOPE_GRID   = CMYK_to_fracRGB([0, 0, 0, 0.2])       # 
LT_TEXT         = webRGB_to_fracRGB("000000")           # This makes the most sense - Black

#
# These are special characters that can be used in labels, notes and arrows.
# Bob Reay's version outputs web values which seems to import into Illustrator
# but these unicodes work just fine as well. Some characters such as sigma will
# an error upon importation because LinearHelvCond doesn't have the character
# but I found in my trial copy that Illustrator will just find a place a substitute.
# Web values will only work if _escape_attrib_reversal() is called because for some
# reason svg_backend is replacing things like "&" with "&amp;".
# S.L.M.
# 
DELTA           = "\u0394"
DEGC            = "\u00B0C"
DEG             = "\u00B0"
mu              = "\u00B5" # "&#181;"  
sigma           = "\u03C3" # "&#963;"
SIGMA           = "\u03A3"
minus           = "\u2212"
# From the 4630A G02 SVG sent from Dan:
# GRID width = 0.35
# border width = 0.6
# subscripts are size 6
# text color is not set and comes out 000000
# LT_ BORDER    = 000000
# LT_GRID       = 58595B
# LT_RED_1      = 981B1E
# LT_BLUE_1     = 3953A4
# LT_GREEN_1    = 37864B
# LT_COPPER_1   = B57233
# LT_BLACK      = 000000
# LT_RED_2      = DA2032
# LT_BLUE_2     = 547FBC
# LT_YELLOW_2   = CFB43D #(MUSTARD)

if __name__ == "__main__":
    import pydoc
    pydoc.writedoc('LTC_plot')
    os.startfile("LTC_plot.html")
    #print __doc__
