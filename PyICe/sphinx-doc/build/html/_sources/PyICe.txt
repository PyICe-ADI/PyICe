PyICe
=====

Python Integrated Circuit Evaluation Environment
------------------------------------------------

::

                     \|||/
                     (o o)
  +-------------oooO--(_)---------------------+
  | ____           ______   ____              |
  |/\  _`\        /\__  _\ /\  _`\            |
  |\ \ \L\ \__  __\/_/\ \/ \ \ \/\_\     __   |
  | \ \ ,__/\ \/\ \  \ \ \  \ \ \/_/_  /'__`\ |
  |  \ \ \/\ \ \_\ \  \_\ \__\ \ \L\ \/\  __/ |
  |   \ \_\ \/`____ \ /\_____\\ \____/\ \____\|
  |    \/_/  `/___/> \\/_____/ \/___/  \/____/|
  |             /\___/                        |
  |             \/__/                         |
  +------------------------oooO---------------+
                    |  |  |
                    |__|__|
                     || ||
                     || ||
                    ooO Ooo

PyICe is a comprehensive Python framework designed specifically for lab automation.
It can interact with most lab instruments, treating each aspect of a given instrument
as an individual "channel". The channel model reduces even the most complex instruments
to a collection of scalars that can be monitored and controlled by test scripts, a
graphical user interface, or logged into an SQLite database or Excel worksheet.

A second distinct aspect of the project is used to interact with internal IC memory in the same way as
other test equipment channels so that the DUT memory and outside electrical conditions can be
monitored, controlled, and logged synchronously.
This part of the project also includes numerous utilites to generate 
both publicly distributable libraries and documentation, and private IC synthesis and test files,
all from a single common XML-based register map description.

Check out a series of quick-start tutorials
and a brief overview of the basic capabilities and usage here:
::

  PyICe/Examples/getting_started_examples

The PyICe library is relatively stable but is under ongoing development.

A working copy can be checked out from the Boston SVN server (linux credentials required) here:
::

  http://bos-svn.engineering.linear.com/svn/PyICe/trunk/


.. autosummary::
    :toctree: _autosummary

    PyICe.lab_instruments
    PyICe.lab_core
    PyICe.lab_utils
    PyICe.LTC_plot
    PyICe.lab_gui
    PyICe.lab_interfaces
    PyICe.twi_instrument
    PyICe.twoWireInterface
    PyICe.spi_instrument
    PyICe.spi_interface
    PyICe.visa_wrappers
    PyICe.xml_registers

Documentation is a work in progress.

Please contact us with any questions, requests for documentation, or to volunteer help developing additional instrument drivers:
  - Steve Martin
    smartin@linear.com
  - Dave Simmons
    dsimmons@linear.com
  - Zach Lewko
    zlewko@linear.com










