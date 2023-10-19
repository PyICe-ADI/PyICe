==================================
TUTORIAL 5 Putting it all Together
==================================

This script brings all of the previous concepts together by measuring a laser diode assembly purchased from Amazon. Both the HMP4040 supply and 34401A meter from the previous tutorials are used.

The laser assembly comes with a laser diode (LED) embedded in a brass housing with a lens and a current limiting resistor. The current limiting resistor is visibly exposed.

It is known that 5V can be applied directly across the laser assembly but the raw LED characteristics are unknown as is the current limiting resistor value.

The assembly is wired such that the positive input lead (RED) is connected to the anode of the LED, the LED is connected in series with the resistor and the negative input lead (BLUE) is connected to the "bottom" of the current limiting resistor. The BLUE wire will be considered ground. A third (GREEN) wire was tack soldered to the intermediate node between the LED and resistor. The voltmeter was connected across the resistor (i.e. METER(-) to BLUE (GND) and METER(+) to the intermediate Diode-Resistor node). See the photo in the results folder.

To replicate this experiment with an LED and resistor:

   * Connect the cathode of a red LED to a 220Ω resistor.
   * Connect the positive lead of the power supply to the LED anode.
   * Connect the negative lead of the power supply to the loose resistor end.
   * Place the 34401A meter across the resistor (positive on the intermediate node, negative with the supply negative).

Let's get a *lab_interfaces* **interface_factory**, a 34401a interface and an HMP4040 interface.

.. code-block:: python

   from PyICe import lab_interfaces
   
   interface_factory = lab_interfaces.interface_factory()
   
   a34401_interface = interface_factory.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)
   supply_interface = interface_factory.get_visa_serial_interface("COM16", baudrate=115200, rtscts=True, timeout=10)

Let's get the PyICe drivers for the two instruments from *lab_instruments* and get the instruments configured.

.. code-block:: python

   from PyICe.lab_instruments.agilent_34401a import agilent_34401a
   from PyICe.lab_instruments.hameg_4040 import hameg_4040
   
   meter = agilent_34401a(a34401_interface)
   meter.add_channel("vresistor_vsense")
   meter.config_dc_voltage()
   
   hameg = hameg_4040(supply_interface)
   hameg.add_channel(channel_name="vsweep", num=3, ilim=1, delay=0.25)
   hameg.add_channel_current(channel_name="current_limit", num=3)

Now let's create a **PyICe** *channel_master* from lab_core.py and get our instruments added to it.
This time we'll call our channel_master *bench* to better match its real-world counterpart.

.. code-block:: python

   from PyICe import lab_core
   
   bench = lab_core.channel_master()
   bench.add(meter)
   bench.add(hameg)
  
The order of these steps is not important as long as no step references an object that has yet to be created.

We will need *lab_utils* to generate a floating point voltage sweep range rather than just integer voltages. We will also need it to help us extract data from the SQLite database.

We will also need *LTC_plot* to generate data visualization plots after data collection.

.. code-block:: python

   from PyICe.lab_utils.ranges import floatRangeInc
   from PyICe.lab_utils.sqlite_data import sqlite_data
   from PyICe import LTC_plot

Finally, we will need to create a *lab_core* **logger** object to collect our data rows and columns on each sweep step. We might as well lower the power supply's current limit to 500mA while we're at it.

.. code-block:: python

   logger = lab_core.logger(bench)
   logger.new_table(table_name='diode_data_table', replace_table=True)
   bench.write('current_limit', 0.5)

We've completed the setup steps needed to begin collecting data. The small code block below shows all that is needed to run a powerful (potentially nested) measurement sweep. Let's not forget to "clean up" our bench by setting the power supply voltage back to 0V on the way out (the laser was trying to burn a hole through the HAMEG 😊 ).

.. code-block:: python

   for vsweep in floatRangeInc(0, 6, 0.025):
       print(f"Setting voltage to {vsweep}V")
       bench.write('vsweep', vsweep)
       logger.log()
   bench.write('vsweep', 0)

Now that the data is collected, we will make an **LTC_plot** *Multipage* plot this time.

The plots will go into separated pages within a single file rather than individual files.

The curves will be:

#. Plot the assembly current\* vs the applied voltage
#. Plot the assembly current\* vs the raw laser diode voltage on a logarithmic axis
#. Plot the power of the raw laser diode and the entire assembly vs applied voltage
#. Plot the power of the raw laser diode vs the assembly current\*

\*Note that the assembly current is the same as both the resistor and LED currents as they are in series.

Let's first retrieve the data from the SQLite database created during the collection phase.

.. code-block:: python

   database = sqlite_data(table_name="diode_data_table", database_file="data_log.sqlite")            

Now let's create the laser assembly's I-V plot and add the desired trace. In this plot we'll also dig out the data needed to compute the resistor value and annotate the plot with it.

.. code-block:: python

   #########################################################################
   #                                                                       #
   # Laser Diode Assembly Current vs Voltage
   #                                                                       #
   #########################################################################
   G1 = LTC_plot.plot(plot_title   = "Laser Diode Assembly Current vs\nApplied Voltage",
                      plot_name    = "G1",
                      xaxis_label  = "ASSEMBLY VOLTAGE (V)",
                      yaxis_label  = "ASSEMBLY CURRENT (mA)",
                      xlims        = (0, 6),
                      ylims        = (0, 40),
                      xminor       = 0,
                      xdivs        = 6,
                      yminor       = 2,
                      ydivs        = 4,
                      logx         = False,
                      logy         = False)
   database.query('SELECT vsweep_vsense, vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
   G1.add_trace(   axis    = 1,
                   data    = database.to_list(),
                   color   = LTC_plot.LT_RED_1,
                   legend  = "")
   database.query('SELECT vresistor_vsense, vsweep_isense FROM diode_data_table WHERE vsweep==6')
   V_6V, I_6V = database[0]
   database.query('SELECT vresistor_vsense, vsweep_isense FROM diode_data_table WHERE vsweep==3')
   V_3V, I_3V = database[0]
   rmeasured = (V_6V - V_3V) / (I_6V - I_3V)
   G1.add_note(note=r"$R_{SERIES}=$" + f"{rmeasured:0.2f}Ω", location=[0.1, 36], use_axes_scale=True, fontsize=9, axis=1, horizontalalignment="left", verticalalignment="bottom")
   #########################################################################
   #                                                                       #
   #########################################################################

Note, in this tutorial that LaTeX string formatting is supported by matplotlib (and therefore LTC_plot). An example of subscripting is shown in the **add_note()** method above. LaTeX string formatting requires the text string to be declared a *raw* string by preceding the quotes with an **r**. More information on LaTeX string formatting syntax may be found here: https://matplotlib.org/stable/gallery/text_labels_and_annotations/tex_demo.html

Also recall that the **PyICe** driver for the power supply created helper channels for the power supply current and voltage readback that you did not create explicitly. These helper channels are the ones seen in the SQLite query.

If you use an instrument driver that doesn't automatically add channels that you need, you will need to peruse your instrument's driver file in *lab_instruments* to find the add() method for the channel(s) you need.

In the next plot we'll extract just the LED voltage and plot the LED (aka assembly) current against it on a log scale.

.. code-block:: python

   #########################################################################
   #                                                                       #
   # Laser Diode Assembly Current vs Raw Laser Diode Voltage
   #                                                                       #
   #########################################################################
   G2 = LTC_plot.plot(plot_title   = "Laser Diode Current vs\nRaw Diode Voltage",
                      plot_name    = "G2",
                      xaxis_label  = "DIODE VOLTAGE (V)",
                      yaxis_label  = "DIODE CURRENT (mA)",
                      xlims        = (1.6, 2.4),
                      ylims        = (0.3, 40),
                      xminor       = 2,
                      xdivs        = 4,
                      yminor       = 1,
                      ydivs        = 4,
                      logx         = False,
                      logy         = True) # <---- Note Log scale
   database.query('SELECT vsweep_vsense - vresistor_vsense, vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense - vresistor_vsense')
   G2.add_trace(   axis    = 1,
                   data    = database.to_list(),
                   color   = LTC_plot.LT_RED_1,
                   legend  = "")
   #########################################################################
   #                                                                       #
   #########################################################################

Now we'll create the plot that shows the raw LED power and the assembly power levels plotted against the applied voltage.

.. code-block:: python

   #########################################################################
   #                                                                       #
   # Laser Diode Assembly Total Power and Diode Power vs Applied Voltage
   #                                                                       #
   #########################################################################
   G3 = LTC_plot.plot( plot_title  = "Power of the Laser Diode Assembly\nand Raw Laser Diode",
                      plot_name    = "G3",
                      xaxis_label  = "VOLTAGE (V)",
                      yaxis_label  = "POWER (mW)",
                      xlims        = (0, 6),
                      ylims        = (0, 240),
                      xminor       = 0,
                      xdivs        = 6,
                      yminor       = 0,
                      ydivs        = 6,
                      logx         = False,
                      logy         = False)
   database.query('SELECT vsweep_vsense, vsweep_vsense * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
   G3.add_trace(   axis    = 1,
                   data    = database.to_list(),
                   color   = LTC_plot.LT_RED_1,
                   legend  = r"$P_{ASSY}$")
   database.query('SELECT vsweep_vsense, (vsweep_vsense - vresistor_vsense) * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_vsense')
   G3.add_trace(   axis    = 1,
                   data    = database.to_list(),
                   color   = LTC_plot.LT_BLUE_1,
                   legend  = r"$P_{DIODE}$")
   G3.add_legend(axis=1, location=(1, 0), justification='lower left', use_axes_scale=False, fontsize=7)
   #########################################################################
   #                                                                       #
   #########################################################################
   
Note the use of LaTeX string formatting in the trace legend above.

Finally, we'll plot the raw LED power as a function of the LED (aka assembly) current.

.. code-block:: python

   #########################################################################
   #                                                                       #
   # Raw Laser Diode Power vs Diode Current
   #                                                                       #
   #########################################################################
   G4 = LTC_plot.plot( plot_title  = "Power of the Raw Laser Diode\nvs Diode Current" + r"$^{*}$",
                      plot_name    = "G4",
                      xaxis_label  = "CURRENT (mA)",
                      yaxis_label  = "POWER (mW)",
                      xlims        = (0, 40),
                      ylims        = (0, 100),
                      xminor       = 0,
                      xdivs        = 4,
                      yminor       = 0,
                      ydivs        = 5,
                      logx         = False,
                      logy         = False)
   database.query('SELECT vsweep_isense * 1e3, (vsweep_vsense - vresistor_vsense) * vsweep_isense * 1e3 FROM diode_data_table ORDER BY vsweep_isense')
   G4.add_trace(   axis    = 1,
                   data    = database.to_list(),
                   color   = LTC_plot.LT_RED_1,
                   legend  = r"")
   G4.add_note(note= r"$^{*}$" + "Diode current is the same\n as the assembly current", location=[0.05, 0.95], use_axes_scale=False, fontsize=7, axis=1, horizontalalignment="left", verticalalignment="top")
   #########################################################################
   #                                                                       #
   #########################################################################
   
Again, note the use of LaTeX string formatting in the **add_note()** method and the plot title.

The only thing left to do is add the plots to some pages, add the pages to a multipage PDF file and generate the output file.

.. code-block:: python

   #########################################################################
   #                                                                       #
   # Assembling and Generating the Pages
   #                                                                       #
   #########################################################################
   
   Page1 = LTC_plot.Page(rows_x_cols=(1, 2), page_size=None)
   Page1.add_plot(G1, position=1)
   Page1.add_plot(G2, position=2)
   
   Page2 = LTC_plot.Page(rows_x_cols=(1, 2), page_size=None)
   Page2.add_plot(G3, position=1)
   Page2.add_plot(G4, position=2)
   
   Multipage = LTC_plot.Multipage_pdf()
   Multipage.add_page(Page1)
   Multipage.add_page(Page2)
   
   Multipage.create_pdf("Laser Diode Test")

The results of these tutorials and the SQLite file are stored in the **...\\results\\** folder for reference.