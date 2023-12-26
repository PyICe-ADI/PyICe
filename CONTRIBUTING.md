# Contributing to PyICe
# Please download Python [3.10.11](https://www.python.org/downloads/release/python-31011/) to develop on PyICe 
## Introduction
Welcome to PyICe!  There is always room for improvement, whether it be new instrument
drivers, updated test infrastructure or anything else. 

## Installation and Setup

### Create a virtual Environment
Once you have cloned the PyICe git repository, you will need to create a virtual environment:
```commandline
python -m venv pyice-env
```
If you already have an older or newer version of Python installed, you can peg the PyICe virtual environment to Python 3.10 as shown below.
Be sure you have added Python 3.10 to the system environment variable _Path_.
```commandline
py -3.10 -m venv pyice-env
```
This will create a directory `pyice-env/` with the Python binaries which will allow
you to install packages for that isolated environment. 
### Activate your virtual environment 
You can activate your virtual environment in a Windows Powershell:
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

```commandline
python -m pip install -r PyICe/requirements/dev-requirements.txt
```
You are now all set up to start developing PyICe on your machine! 

## Get an editable copy of PyICe on your machine
If you would like to work on an editable copy of PyICe on your machine in 
a different environment, you can. Go to your cloned copy of PyICe, and in your shell
(**please make sure to complete the previous step**):
```commandline
python -m pip install --editable .[dev]
```
Note: if pip gives you a warning to upgrade, please do so. You may need to upgrade 
pip to install an editable version of PyICe from the pyproject.toml file.
Adding `[dev]` will include the optional development packages in your local 
editable install. 


## Contributing Guidelines


## Coding Standards
Please follow PEP8 as best you can.

## Contact info
General: PyICe inquires:
    Developers: pyice-developers@analog.com
    Dave Simmons: david.simmons@analog.com
    Steve Martin: steve.martin@analog.com 

Environment questions or concerns:
    Tim Laracy: tim.laracy@analog.com

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