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

# [PyICe contributors, please go here for install instructions](CONTRIBUTING.md)

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)


## Installation

PyICe is a python package. To install, you will need to first log into
[ADI Artifactory](https://artifactory.analog.com/ui/packages)  to set up your
Artifactory credentials. Click on the dropdown that says "Welcome < username>",
and then "Set me up".

* Select "Package Type" as PyPI, and repository as "power-fusa-pypi"
* Enter in your password, select "Resolve"
* Copy just the link itself, and paste it along with code below into ~/.pip/pip.conf (~/pip/pip.ini for Windows)
  ```bash
  [global]
  extra-index-url = <paste the link here>
  ```
* Finally, install the PyICe package to your local conda environment with the following command
```commandline
pip install PyICe-adi
```

### Other softwares
Other softwares can be installed to improve PyICe's capabilites.
* Graphviz https://pypi.org/project/graphviz/