========================
TUTORIAL 3 Plotting Data
========================

The plotting utility, *LTC_plot*, of **PyICe** can generate datasheet-ready plots in either Scalable Vector Graphics (.svg) or PDF format.

It is a wrapper of Matplotlib which is an extensive Matlab-like plotting library for Python.

It was configured to make datasheet plots that are 100% compliant with the datasheet standards of the now defunct semiconductor company Linear Technology (https://en.wikipedia.org/wiki/Linear_Technology).

We use only a very small subset of it.

A major advantage of using LTC_plot is documentation and reproducibility of *what* exactly was plotted.

What's more, collecting data and plotting it should not be presumed to be a one-time event.

As hardware IP progresses for a given project (e.g. IC, system or PCB), it is likely that measurements will need to be made, remade and remade again.

Adopting a scripting methodology for collecting, logging and *plotting* data is the best path to developing a product defensibly free of regression.

First we'll import LTC_plot.

.. code-block:: python

   from PyICe import LTC_plot

The next part of this script operates on the data collected in ex_2_logging without re-collecting.

An important tenet of PyICe is that data can be collected *now* and processed independently *later*.

This will prove to be a very power methodology for more complex evaluation efforts.

The module *lab_utils* contains helper functions that can extract data from the SQLite file and format it for plotting.

.. code-block:: python

   from PyICe.lab_utils.sqlite_data import sqlite_data

LTC_plot defines *plots* and *pages*.

Data can be plotted on plots and plots can be added to pages.

Pages can be generated as .svg or .pdf files.

First we'll create an **LTC_plot.plot()**.

As an easy reminder of formatting parameters, the plot object was defined with the most commonly known settings clearly enumerated in its creator method.

.. code-block:: python

   GX = LTC_plot.plot( plot_title   = "Demonstration of Meter Readings\nVs Iteration Number",
                       plot_name    = "TUTORIAL 3",
                       xaxis_label  = "ITERATION ()",
                       yaxis_label  = "VOLTAGE (µV)",
                       xlims        = (1, 9),
                       ylims        = (-10, 10),
                       xminor       = 0,
                       xdivs        = 8,
                       yminor       = 0,
                       ydivs        = 10,
                       logx         = False,
                       logy         = False)

Next we will need a SQLite query to extract the data from the SQLite file.

The data expected by LTC_plot is of the form: ((x1,y1), (x2,y2), (x3,y3)) so always select the *x* column first and then the *y* column.

.. code-block:: python

   my_query = 'SELECT rowid, vmeas*1e6 FROM tutorial_2_table ORDER BY rowid'
                    
Using SQLite requires some knowledge of the SQLite query language.

There are many examples of this online, it is not overly burdensome to learn, and the benefits will become abundantly obvious with practice.

One such benefit of using SQLite querys is that columnwise calculations are essentially free and the query clearly documents *what* was plotted.
       
.. code-block:: python
       
   database = sqlite_data(table_name="tutorial_2_table", database_file="data_log.sqlite")            
   database.query(my_query)

The **database** object is stateful and retains a record of the most recent query made against it.

Next we will add a trace to the LTC_plot.plot() created above using the data from the query.

.. code-block:: python

   GX.add_trace(axis   = 1,
                data   = database.to_list(),
                color  = LTC_plot.LT_RED_1,
                legend = "Only\nTrace")

For multiple traces, it is likely desirable to add a meaningful legend to the plot.

.. code-block:: python

   GX.add_legend(axis=1, location=(1.02, 0), use_axes_scale=False)
   
Most features of LTC_plot support using the data axes (axes values against which the data is plotted) or absolute axes (values from 0 to 1 representing 0 to 100% of the graph size).

Loose notes can also be added to the plot.

.. code-block:: python

   GX.add_note(note="Add Your Note Here", location=(0.02, 0.02), use_axes_scale=False)

Finally, an LTC_plot *Page* can be created, plots added to it, and output files generated.

.. code-block:: python

   Page1 = LTC_plot.Page(rows_x_cols=(1, 1), page_size=None)
   Page1.add_plot(plot=GX, position=1)
   Page1.create_svg(file_basename="TUTORIAL 3")
   Page1.create_pdf(file_basename="TUTORIAL 3")
   
   print("\n\nLook in the \\results\\plots folder for the Tutorial 3 files.")
   
Other features such as arrows can be added and histograms can be plotted, etc.

See the **PyICe** folder **PyICe\\tutorials\\LTC_plot_example** for more plotting examples.