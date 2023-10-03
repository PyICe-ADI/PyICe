# PyICe

PyICe is a comprehensive Python framework designed specifically for lab
automation. It can interact with most lab instruments, treating each aspect of
a given instrument as an individual “channel”. The channel model reduces even
the most complex instruments to a collection of scalars that can be monitored
and controlled by test scripts, a graphical user interface, or logged into an
SQLite database or Excel worksheet.

A second distinct aspect of the project is used to interact with internal IC
memory in the same way as other test equipment channels so that the DUT memory
and outside electrical conditions can be monitored, controlled, and logged
synchronously. This part of the project also includes numerous utilites to
generate both publicly distributable libraries and documentation, and private
IC synthesis and test files, all from a single common XML-based register map
description.

For more detailed documentation, please go [here](https://pyice-adi.github.io/PyICe/)

# [PyICe contributors, please go here for install instructions](CONTRIBUTING.md)

