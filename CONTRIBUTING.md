# Contributing to PyICe
# Please download Python [3.10.11](https://www.python.org/downloads/release/python-31011/) to develop on PyICe

## Introduction
Welcome to PyICe!  There is always room for improvement, whether it be new instrument
drivers, updated test infrastructure or anything else. 

## Installation and Setup

### Clone a copy of PyICe
Pick a folder on your computer - preferably one not already under version control like OneDrive, etc.

A folder such as c:\users\projects is recommended.

Using a Git client such as Tortoise Git, clone a copy of https://github.com/PyICe-ADI/PyICe.git to that folder

### Create a virtual Environment
Be sure you have added Python 3.10 to the system environment variable _Path_.

In the event you already have an older or newer version of Python installed, you **must** peg the PyICe virtual environment to Python 3.10 as shown below.
```commandline
py -3.10 -m venv pyice-env
```
This will create a directory `pyice-env/` with the Python binaries which will allow
you to install packages for that isolated environment. 
### Activate your virtual environment 
Active your virtual environment in Windows:
```commandline
.\pyice-env\Scripts\activate
```
or in Linux:
```commandline
source ./venv/bin/activate
```
Once the environment is activated, you can install the development packages (
this includes pytest
)

### Install the development packages
Change directory into the PyICe container directory which contains pyproject.toml
```commandline
cd PyICe
```
Install PyICE's depdendencies
```commandline
python -m pip install --editable .[dev]
```

You are now all set up to start developing PyICe on your machine! 

## Contributing Guidelines


## Coding Standards
Please follow PEP8 as best you can.

## Contact info
General PyICe inquires:

    Developers: pyice-developers@analog.com
    Zachary Lewko: zachary.lewko@analog.com
    Dave Simmons: david.simmons@analog.com
    Steve Martin: steve.martin@analog.com

Environment questions or concerns:
    Tim Laracy: Tlaracy@marvell.com

User group:
	pyice-users@analog.com


## New Git Users!

Check out [this link](https://education.github.com/git-cheat-sheet-education.pdf)
for a handy cheatsheet on how to use git.  If you find yourself in a pickle, 
there is also [oh s***, git!](https://ohshitgit.com/), which has a several ways to
clean up a Git disaster.

When you beging working on a feature, please branch off of the master branch
```commandline
git checkout master
git branch new_feature_name
```
Make your commits small - that makes it much easier for other contributors to
see your workflow.