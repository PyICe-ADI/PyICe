==========================================
TUTORIAL 0 Setting up a Python Environment
==========================================

This tutorial series will introduce the basic tenets of PyICe and how to get started with it.
Each tutorial builds on the previous and doesn't re-explain material already covered.
Going through these in order is recommended.
This tutorial does not attempt to teach programming or Python; numerous examples for both exist online.

This tutorial explains the steps required to install PyICe and use Notepad++ as a quick-start IDE.
If you are an experienced programmer and have a better workflow and a better programming environment - have at it.

You will need to download and install:

* Python 3.9 or higher
* PyICe (using a git client such as Tortoise Git or other)
* Keysight / Agilent IO Suite (or another VISA)
* An IDE for running Python
    * Notepad++ 32 bit with the PyNPP plugin added is a good candidate
    * 64 bit Notepad++ may not support PyNPP

You will need to complete the following steps:

#. Download and install Python 3.9 or higher

#. Download and install Tortoise GIT
    * You will also need to install a GIT engine.
    * Tortoise GIT may offer to help via URL in one of its install pages - you should probably follow it.
    * Tortoise may also help you populate its GIT engine path if you install GIT from the Tortoise installer.

#. Download and install Notepad++ 32 bit

#. Run Notepad++, navigate to **Plugins->Plugins Admin...** and search for the *PyNPP* plugin
    * Install *PyNPP*
    * Install *Python Indent* while you are there
    
#. Add the location of your Python install to the system environment variable **PATH**
    * e.g. C:/Users/*<yourname>*/AppData/Local/Programs/Python/Python310/

#. Create a new Python environment
    * Create a working folder, perhaps in C:/users/<*yourname*>/projects/
    * Using a cmd window, navigate to this new folder and type **python -m venv pyice-env**

#. Git clone PyICe from https://github.com/PyICe-ADI/PyICe into a folder, perhaps into C:/users/<*yourname*>/projects/
    * This will create a folder called *pyice-adi* there
    
#. Now we need to activate this environment. We can use the current cmd shell by typing: **.\\pyice-env\\Scripts\\activate**
    * This should return a cmd prompt similar to: **(pyice-env) D:\\users\\<yourname>\\projects>**

#. To build your PyICe dependency stack, navigate into the **\\projects\\pyice-adi\\** folder. The **\\requirements\\** folder will be found there.

#. Type **python -m pip install -r requirements/dev-requirements.txt**

#. Point Notepad++ to your Python environment folder
    * In Notepad++ navigate to **Plugins->PyNPP->Options**
    * Click the ellipsis on the right **[...]**
    * Navigate to the path that contains your Python environment definition
    * e.g. C:/users/<yourname>/projects/pyice-env/Scripts

#. Edit your *System Environment Variables* and create or edit a system variable called **PYTHONPATH**
    * Set **PYTHONPATH** to point the folder PyICe within your pyice-adi distribution folder
    * e.g.: **PYTHONPATH** = C:/users/<*yourname*>/projects/pyice-adi
    
#. Navigate into the **/pyice-adi/PyICePad/** folder and double-click the file **create PyICepad.bat**
    * Follow the instructions on the screen (some of which you have already completed here)
    * This should create a file **PyICepad++.bat** in the PyICepad directory
    * You can drag this batch file to your desktop or make a shortcut of it and change its icon

#. Create a new example project folder on your computer, perhaps in C:/users/<*yourname*>/projects/pyice_example/

#. Create a file inside that folder, perhaps called "pyice_example.py".

#. Double click the **PyICepad++.bat** file created from the create PyICpad step above
    * This should create a background cmd window and bring up Notepad++
    * Notepad++ is now operating in the correct virtual environment
    * The background cmd window needs to exist for the duration of the Notepad++ session as it holds the session information
    
#. Open **pyice_example.py** in Notepad++
    * With Notepad++ having been opened from PyICepad++, all files opened into Notepad++ will be in the special environment session