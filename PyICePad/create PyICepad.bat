@echo off
IF EXIST PyICepad++.bat del PyICepad++.bat
@echo.
@echo This script helps create a quick and dirty Python IDE using Notepad++
@echo Presumably you have Python installed already
@echo.
@echo     1) Install the ***32-Bit Version*** of Notepad++ from here: https://notepad-plus-plus.org/
@echo     2) Open a cmd shell and create a new Python environment with python -m venv pyice-env
@echo     3) Enter the absolute path to your new Python environment below
@echo        This should be the path only up to, but *NOT* including, \pyice-env\...
@echo.
@set /p PYENV="Enter an absolute path leading up to, but *NOT* including, \pyice-env --->"
@echo call %PYENV%\pyice-env\Scripts\activate.bat >> PyICepad++.bat
@echo "C:\Program Files (x86)\Notepad++\notepad++.exe" >> PyICepad++.bat
@echo.
@echo *** Success *** Created the file: "PyICepad++.bat"
@echo.
@echo     4) Make a shortcut of PyICepad++.bat or move it to any convienent location (e.g. your Desktop)
@echo     5) Double click the file and it should open Notepad++
@echo     6) DO NOT close the background window, it must remain open
@echo     7) Add the PyNPP plugin to Notepad++ from the [Plugins][Plugins Admin...] menu
@echo     8) Under [Plugins][PyNPP][Options][Python folder] use the [...]
@echo        to navigate to the location of your Python.exe executable or environment folder
@echo     9) [Plugins][PyNPP][Run File in Python Interactive] or Alt+Shift+F5 now runs a Python script
@echo.
pause