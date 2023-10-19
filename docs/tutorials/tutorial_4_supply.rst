================================
TUTORIAL 4 Adding a Power Supply
================================

This script introduces writable channels, specifically within a power supply.
It will use a Rhode and Schwartz (formerly Hameg) HMP4040 power supply.

Note that the HMP4040 is connected via a standard USB (A to B) cable but appears as a virtual COM port in the device manager.
Connecting each instrument to the software comes with its own challenges but this is generally a one time struggle and worth the additional effort.

The HMP4040 is a 4 channel power supply but we will only be using its physical channel #3.

.. code-block:: python

   from PyICe import lab_core
   from PyICe import lab_interfaces
   from PyICe.lab_instruments.hameg_4040 import hameg_4040

   interface_factory = lab_interfaces.interface_factory()
   supply_interface = interface_factory.get_visa_serial_interface("COM16", baudrate=115200, rtscts=True, timeout=10)

   hameg = hameg_4040(supply_interface)
   hameg.add_channel(channel_name="force_voltage", num=3, ilim=1, delay=0.25)

   channel_master = lab_core.channel_master()
   channel_master.add(hameg)

The HMP4040 power supply has current and voltage measurement readback capability built in.

In this tutorial, the *lab_instruments* driver for the *hameg_4040* was written to automatically generate PyICe channels for these commonly used measurement readback channels.
This can be a powerful tool for debugging when physical issues crop up on the bench.

Optionally we can add the other related PyICe channels for this power supply such as a current limit control (assuming the driver was written to support it).
If you find that an instrument driver is devoid of a feature that the instrument physically supports, please consider amending the driver and performing a pull request or contact pyice-developers@analog.com.

.. code-block:: python

   hameg.add_channel_current(channel_name="current_limit", num=3)
   
Now we can write the voltage to 5V and set a 500mA current limit.

.. code-block:: python

   channel_master.write(channel_name='force_voltage', value=5)
   channel_master.write(channel_name='current_limit', value=0.5)

Using the channel_master we can now read all the channels at once.

.. code-block:: python

   print("Reading ALL channels")
   print(channel_master.read_all_channels())
   
This command produces the output:

.. code-block:: text

   Reading ALL channels
   current_limit:        0.5
   force_voltage:        5
   force_voltage_enable: True
   force_voltage_ilim:   1
   force_voltage_isense: 0.0297
   force_voltage_vsense: 4.999

Notice that the auxiliary channels created are prepended with your custom channel name of **force_voltage_**.

We can also read a subset of channels (now that the we know they exist).

.. code-block:: python

   print("Reading the '<your_name>_vsense' and '<your_name>_isense' auxilliary channels")
   print(channel_master.read_channels(item_list=['force_voltage_vsense', 'force_voltage_isense']))
   
And this produces:

.. code-block:: text

   Reading the '<your_name>_vsense' and '<your_name>_isense' auxiliary channels
   force_voltage_isense: 0.0302
   force_voltage_vsense: 5.0