============================================
TUTORIAL 1 Adding a Single Channel Voltmeter
============================================

This tutorial explains the steps required to connect to a meter and take a measurement.
The ubiquitous Agilent/Keysight 34401A single channel meter will be used.

If you have completed TUTORIAL 0, you should have an IDE (perhaps Notepad++), Python, PyICe and, preferably, a Python environment.
You should also have a folder in which to work and the file **pyice_example.py** in the folder in which to work.

To communicate with our instrument, we will need an interface object or "handle" to it.
We can get the handle from the interface_factory in lab_interfaces.py.

Open **pyice_example.py** in Notepad++ and import *lab_interfaces* from PyICe.

.. code-block:: python

   from PyICe import lab_interfaces
   
To retrieve an interface, we can create an interface_factory object and call the appropriate *getter* method for our interface type.

.. code-block:: python

   interface_factory = lab_interfaces.interface_factory()
   my_a34401_interface = interface_factory.get_visa_serial_interface("COM10", baudrate=9600, dsrdtr=True, timeout=5)
   
Next we will import lab_core which contains the base *channel* framework of PyICe, a PyICe **channel_master**.

PyICe introduces the concept of a *channel*, a Python object most often a scalar value but sometimes a vector, that represents a single object that we would like to access on the bench.
It could be the reading of a volt meter, the voltage or current limit setting of a power supply, the amplitude of a waveform or even the X or Y record of an oscilloscope trace.
We will create many channels as we build up our PyICe workspace.
The key benefit of PyICe is that, once we teach it how to access these resources, it will aggregate these channels into a single, large, flat namespace.
Each PyICe channel will be named, by you, with a simple, unique text string.
The channel name (string) can be as long and verbose as you like, the purpose of which is to make interacting with the bench resources as human friendly as possible.

Channels generally have only a *read* method **or** a *write* method but not both.
If a channel was defined with a write method, PyICe will generally return a buffered version of the value written when asked to read from the channel.
If the channel has yet to be written to, the Python value **None** will be returned.
If the channel was defined with a read method, and an attempt to write it occurs, PyICe will throw up a warning in its console and take no further action.
There are exceptions to this rule, for example with serial port reads and writes.
These are automatically considered volatile and the read method actively reads live data from the device.

In order to aggregate all of our channels, and with them, their interfaces into a single access point, we must first create a PyICe *channel_master*.
Generally our project will have only one instance of a PyICe channel_master which we will create by requesting from lab_core.py.

.. code-block:: python

   from PyICe import lab_core
   channel_master = lab_core.channel_master()

In this tutorial, the meter is connected via a USB to quad-RS232 expander with the FTDI chip set.
The first RS232 connector landed on port COM10.
When using RS232 equipment, be sure to determine if it needs a null modem adapter or not as not all RS232 ports have been assigned the correct hierarchical stature (DCE vs DTE).
The 33401A meter is one such example and does require a combination null modem adapter and gender changer.

Next we need to get a driver for our instrument.

The lab_instruments module contains drivers to translate from each instrument's native language (e.g. SCPI, binary, freds_binary_scpi) to PyICe channels.
In essence, the PyICe channel concept realizes the abstraction layer that SCPI (Hardware HPIB, GPIB and IEEE-488) attempted to achieve so many years ago.
It creates a unified standard for interacting with bench instruments by inserting a new, truly consistent, interposing abstraction layer.

There is a large, and growing, library of instrument driver definitions in lab_instruments.
If you need a driver for an instrument not present, there is usually a similar one that serves as a good example from which to start.
An instrument driver can usually be written in 1 to 6 hours depending on instrument complexity and features to be supported.

.. code-block:: python

   from PyICe import lab_instruments

We create the *instrument object* by passing it the previously acquired interface *my_a34401_interface*. 
Each instrument constructor takes an interface as its argument.

.. code-block:: python

   my_a34401 = lab_instruments.agilent_34401a(my_a34401_interface)

Now my_a34401 is an agilent_34401a instrument object.
We can talk to the a33401 meter through this interface but doing so would thwart the benefits of adding the instrument and its channels to the channel_master.
That said, the channel_master doesn't know about this instrument yet, so we must add it to the channel_master.

.. code-block:: python

   channel_master.add(my_a34401)

The meter object **my_a34401** doesn't have any *channels* yet.
Channels are named objects (using simple, meaningful strings) that represent physical parameters such as the 34401a measurement results.
The following lines create a channel called "vmeas", and then sets up the meter to read dc voltage into this channel (rather than current which the meter also supports).

.. code-block:: python

   my_a34401.add_channel("vmeas")
   my_a34401.config_dc_voltage()

These configuration commands can be completed before **or** after adding the meter object to the channel_master.
The channel_master will inherit the attributes either way.

There are three ways to read the "vmeas" channel.
The first, and most common, way is to ask the *channel_master* to read it for you.
This is also the most convenient since the channel_master knows about all the channels and you don't have to remember to which instrument a given channel belongs.

.. code-block:: python

   reading = channel_master.read('vmeas')
   print(f"Measuring 'vmeas' using channel_master, reading = {reading}V.")

Most of the time the above method is sufficient and is considered the most *PyCIeonic*.
The following two methods are included for completeness.

Another way is to *go around* the channel_master and ask the instrument itself to read the channel.

.. code-block:: python

   reading = my_a34401.read('vmeas')
   print(f"Measuring 'vmeas' using by circumventing the channel_master and using my_a34401 (not recommended), reading = {reading}V.")

As we will see later, this method subverts the powerful logging feature of PyICe and, therefore, is generally discouraged.
It also sacrifices the benefit of the channel aggregation feature of PyICe, requiring the programmer to manually track the origin of each channel.
In this small tutorial that may seem inconsequential but for realistic projects you should expect to have hundreds of PyICe channels.

A slightly more terse method is to retrieve the value from the channel_master by the channel_master like a dictionary-like object.
Channel objects can be retrieved from any *channel_group* (channel_master or instrument) containing them.

.. code-block:: python

   vmeas_channel_object = channel_master['vmeas']  # This gets the channel object. It could also be obtained from my_a34401
   reading = vmeas_channel_object.read()
   print(f"Measuring 'vmeas' by retreiving the actual channel first and asking it to read. Reading = {reading}.")
   
This method could be condensed down to:

.. code-block:: python

   reading = channel_master['vmeas'].read()
   print(f"Measuring 'vmeas' using the condensed version of rereiving the channel. Reading = {reading}.")

The channel_master.read() method or dictionary-like read method should be selected at the start of the project and remain consistent throughout.
Both methods of accessing the channel via the channel_master are acceptable but this tutorial writer prefers the channel_master.read('channel_name') method for clarity and readability.