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
description. Register maps can be imported from proprietary XML, Yoda JSON, or
industry-standard IP-XACT (IEEE 1685-2014 / SPIRIT 1685-2009) files via
`twi_instrument.populate_from_ipxact()` and `spiInstrument.from_ipxact()`.

## IP-XACT Register Map Import

PyICe can import register maps directly from IP-XACT XML files (IEEE 1685-2014 / SPIRIT 1685-2009).

**Command-line conversion (no Python required):**
```console
python -m PyICe.ipxact_parser my_device.xml -o my_device_regmap.json
```

**Python — direct import (skip JSON):**
```python
from PyICe.twi_instrument import twi_instrument

inst = twi_instrument(interface)
inst.populate_from_ipxact("my_device.xml", addr7=0x50)
```

**Python — convert to JSON first, then import:**
```python
from PyICe.ipxact_parser import ipxact_to_pyice_json

ipxact_to_pyice_json("my_device.xml", output_file="my_device_regmap.json")
```

See `python -m PyICe.ipxact_parser --help` for all CLI options, or
`help(PyICe.ipxact_parser)` for the full module walkthrough.

For more detailed documentation, please go [here](https://pyice-adi.github.io/PyICe/)

# [PyICe contributors, please go here for install instructions](https://github.com/PyICe-ADI/PyICe/blob/main/CONTRIBUTING.md)

# PyICe user install instructions
To install PyICe from PyPI, run the command: 
```console
pip install pyice-adi
```
