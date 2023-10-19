
Welcome to PyICe's documentation!
=================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorials
   modules


Introduction
-----------------------------
Through planning and automation, PyICe catapults verification productivity when evaluating integrated circuits or other complex systems with laboratory test equipment. Specifically, it contains a tool suite that abstracts all items of interest on a lab bench, including a target integrated circuit, into a single flat namespace. Once all bench items have been identified, and their read and write methods have been declared, interacting with these items becomes much more intuitive and productivity is advanced tremendously. Combined with a clear evaluation plan and a centralized version control system, PyICe greatly fosters the collaboration of multi-person teams.

Some of the services offered by PyICe are:

-   Flexible, human meaningful, object names for clear code intent
-   A simple scripting library for reading and writing to bench objects
-   Automatic parsing and re-assembly of bit-packed registers (i.e. bit-fields)
-   A Matplotlib wrapper for making consistent, publishable graphs in .svg or .pdf
-   A Code Free GUI for quick debug, experimentation and demonstration
-   A substantial library of equipment drivers for abstracting laboratory instruments
-   A SQLite datalogger object for storing, retrieving and filtering large volumes of data
-   No more Excel sheet, column manipulation .csv files, schema-less file formats…
-   A fast binary protocol for interacting with peripherals such as demonstration boards
-   Tools for registering, testing and reporting against product specifications
-   Tools for comparing production test data against laboratory bench results
-   Automated results notifications by text and email for long runs such as temperature sweeps
-   Powerful problem-solving tools for instrument manipulation such as binary search algorithms, slow rampers, fixed time delays, etc
-   Other tools for data analysis such as waveform analyzers, data filters, data scalers, interpolators, various device models, etc
-   A method of declaring, logging, and documenting the physical configuration of the lab bench (electronically and pictorially)
-   Automated bench evaluation report generation (coming soon)

The Channel Concept
-----------------------------
PyICe introduces the notion of a *channel*. A channel is a Python object, typically addressed by a user-chosen character string, that accesses any bench function with which the user wishes to interact. A channel can belong to an integrated circuit such a serial port register or can represent a fragment of a register such as one bit-field of a bit-packed register. A channel can also represent a control signal to an integrated circuit such as an ENABLE input pin from a micro-controller or a PGOOD output pin from the IC. A channel can represent any facet of a lab instrument that is electronically accessible such as a power supply’s voltage or current limit or a signal generator’s frequency or amplitude. Each channel is given a user specific name at creation time, thereby making the latter interaction with the system much more human readable. The totality of all identified channels is aggregated by PyICe into a single Python object called a *channel master*.

Once all channels of interest have been identified by the user, and a path has been established for accessing each channel, the user may begin the important work of interacting with the integrated circuit or target system and lab bench system without the burden of parsing, converting or keeping track of the individual idiosyncrasies of each item on the bench. In fact, Python itself was initially designed by Guido van Rossum in 1991 and developed by Python Software Foundation mainly for emphasis on code readability. Its syntax allows programmers to express concepts in fewer lines of code.

Because the object abstraction layer of PyICe is as high as it can be, it is possible to re-map the objects to a system in the virtual world (AKA simulation) just as easily as the physical world. In concept, it is possible to reuse code written to be simulated pre-silicon on real silicon and bench instruments.

Recommended Workflow
----------------------
The steps below are a suggested workflow for developing a defensible, accountable and transparent verification plan for an integrated circuit or any complex target system using ad hoc bench test equipment.

Evaluation Plan
^^^^^^^^^^^^^^^^^
The importance of an evaluation plan cannot be understated. Often, when a new integrated circuit or PCB system arrives, there is an expectation that an evaluation will be performed quickly. This is true if each requirement of the system needs only a cursory look, but if more accountability is needed, for example with automotive products, medical products or high-volume consumer products, a thorough, yet realistic plan should be formulated.

A good plan starts with the product requirements. Certainly, a product’s datasheet is a good place to start. The plan should have one line item for each declared requirement, claim in the datasheet body text or line of the datasheet electrical table.

It is a good idea to give each item (row in the plan) a unique identifier or *key*. A human-meaningful string is preferential for human comprehension and can be parsed by a computer as well. Other evaluation plan key schemas are possible of course but some form of centralized electronic database is strongly recommended.

Each row can result in a parameter being tested over a wide range of adverse conditions such as temperature, frequency, voltage, product variant, version, etc. In many cases the parameter of interest is meant to be somewhat immune to these conditions and therefore a single set of limits should apply over all of them. An automated test should be envisioned wherein the parameter of interest is tested over all conditions and characterization graphs can be produced. Some of these can be formatted for publication with no intervening human interaction at all. The rows of an evaluation plan, aside from having a unique identifier key, may look much like a datasheet entry with fields (columns) such as MIN, TYP, MAX, UNITS, DESCRIPTION, etc.

Hardware Plan
^^^^^^^^^^^^^^^
The hardware plan comes from the Evaluation plan. Once all parameters of interest are identified, the hardware plan including circuit board stack-up, environmental chambers, equipment list, necessary purchases, etc. can be created. The hardware plan should include mechanisms to interact with (both set and get/measure) all hardware pins on an integrated circuit for example.

Manually making and breaking connections from the equipment to the target system hinders automation and should be avoided. If possible, the use of multi-channel or scanning voltmeters, power distribution multiplexers, RF multiplexers, etc. should be used to enable as many tests to be run without human interaction as possible.

A plan to immerse the target device in an environmental chamber from the start is imperative and should not be deferred until after the hardware plan is executed.

Software Plan
^^^^^^^^^^^^^^^
PyICe uses a single flat namespace for easy human interaction. As each resource or attribute of the target device is identified, it should be given a unique name. Once named, A Python object for each item of interest is created and referred to as a channel. Channels maybe addressed directly by their Python object or added to a **channel master**. The channel master is mainly an aggregator of PyICe channels. Once all channels have been added to a master object, communication with them is conducted through the master as a proxy rather than with the channels themselves (although this is not prohibited). The master (usually only one) therefore inherits the read and write methods for every channel added to it. This object model is the key to giving evaluation programming in PyICe an incredibly powerful productivity boost.

Once a channel master is created, and all channels registered with (added to) it, a datalogger object can be created. The datalogger object learns the various paths from the registered channels to their respective representation in the real world from the channel master. That is, the data logger knows how to read and write the values of every channel, just as does the channel master.

The datalogger captures the data from every channel in the system with a single simple call. The normal flow of a particular test is to setup the instruments and device to the desired excitation conditions and call the logger’s **log()** method for each case of interest. A pseudo-code example is shown below:

.. code-block:: python

    def collect(bench, master, logger):
        master.write("vmaina_voltage", 3.3)
        for current in FloatRangeInc(start=0, stop=3, step=0.1)
            master.write("iout2_current", current)
            logger.log()
        bench.cleanup()

Centralized Data Storage
^^^^^^^^^^^^^^^^^^^^^^^^
Automation works well when the system under test is functioning well. When the target system or IC is not performing well, there is much more experimentation and debugging than formalized evidence collection. For a comprehensive evidence collection system, a centralized and well-organized data storage location should be deployed. In a well-documented evidence collection plan, it is possible to keep all runs of all versions of a given test in storage for future reference.

Centralized storage is also a must for evaluation IP such as infrastructure scripts and actual testing scripts when working on multi-person teams. Having each team member create their own infrastructure and private work product runs counter to productivity, accountability and quality.

Version Control
^^^^^^^^^^^^^^^
Version control of not only the evaluation IP (infrastructure and scripts) but also of the collected data, pass/fail results, plots, etc. is the best way to maintain an effective verification system. As IP is altered to fix bugs or increase functionality, reverting or reviewing previous version can become invaluable even within a single user.

Verification Tracking
^^^^^^^^^^^^^^^^^^^^^
Once evaluation hardware and software plans are implemented, it’s time to begin the verification activities. Connecting the evaluation results back to the evaluation plan is the best way to track the performance of the target system (IC for example) against requirements. When using PyICe to its fullest potential, there is a module, or *plugin*, that can be used to make this connection. Use of this feature requires an upfront commitment on the part of the evaluation project leader to include the requisite Python methods that make the connection back to the plan. If this commitment is made, PyICe will compare the results and generate compliance reports in the form of local .json files. It can also include in the report all instrument tracking information such as equipment serial numbers as well as serial numbers of boards d.u.t.s, operator, etc. if such information is declared as part of the bench system.

Correlation Plan
^^^^^^^^^^^^^^^^
In the semiconductor industry it is traditional to correlate production tester readings of critical parameters back to bench readings of the same parameter. Heretofore, this procedure has been ad-hoc, sometimes confusing, very labor intensive and not very transparent. If there is a commitment to evaluation plan parameter **keys** from the beginning of the project, and the device under test is uniquely identifiable (i.e. has a serial number of sorts), PyICe can perform automated bench to ATE correlation against well documented limits and provide a detailed discrepancy report.

Automated Report Generation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Coming soon (time.now()=July ‘23) PyICe can generate automated evaluation reports. Following a simple markdown file for content, PyICe will hunt through the local directory structure for official results-declaration cookies. Cookies must be placed by hand or some other automation means to declare that the .json results file is to be rolled into the generated report. The characterization report can include all relevant information about each test including characterization plots, bench connections, pass/fail results, serial numbers, etc. Many such different reports can be generated factoring in, or out, relevant portions of the system being evaluated.

Getting Started
=======================
To get started using PyICe, there is a recommended folder structure shown below. PyICe has a project creator wizard to help with this. The wizard will conduct a simple interview and generate the directory structure needed to support the requested PyICe plugins. To get started, run **ProjectCreatorWizard.py** from the main PyICe directory.

An example of the recommended directory structure is shown below:

  |    **projname**
  |     ├── **eval_plan** (highly recommended)
  |     │     └ evalplan.xls
  |     ├── **traceability_info**
  |     │     ├ **board_serialization**
  |     │     │    ├ target_board_1.jsonc
  |     │     │    ├ target_board_2.jsonc
  |     │     │    ├ aux_board_1.jsonc
  |     │     │    └ aux_board_1.jsonc
  |     │     └ **component_purpose**
  |     │          ├ targetboard_component_purpose.jsonc
  |     │          └ auxboard_component_purpose.jsonc
  |     ├── **quickstart_gui**
  |     │     └ EZ_projname_GUI.py
  |     ├── **tests**
  |     │     ├ **ipmodule_1**
  |     │     │    └ ip_1_test1
  |     │     │         ├ ip_1_test1.py
  |     │     │         ├ ip_1_test1_results
  |     │     │         └ data ...
  |     │     └ **ipmodule_2**
  |     │          └ ip_2_test1
  |     │               ├ ip_2_test1.py
  |     │               └ ip_2_test1_results
  |     │                   └ data ...
  |     ├── **projname_base**
  |     │     ├ **benches**
  |     │     │    ├ member1_bench.py
  |     │     │    ├ member2_bench.py
  |     │     │    └ ...
  |     │     ├ **hardware_drivers**
  |     │     │    ├ mini_driver1.py
  |     │     │    ├ mini_driver2.py
  |     │     │    └ ...
  |     │     └ **modules**
  |     │          ├ bench_base.py
  |     │          ├ test_module.py
  |     │          └ **projname_plugins**
  |     │               ├ pyice_plugin1.py
  |     │               ├ pyice_plugin2.py
  |     │               └ ...

The evaluation project work product (scripts and resultant data) as well as infrastructure live under a single folder projname. By using centralize data management and version control, this folder structure will be the same on all team member’s computers. PyICe should not be in this folder.

The **eval_plan** folder is highly recommended. There may be better plan tracking options, but in lieu of a more centralized system, it is strongly recommended to capture the intent and scope of the verification goals somewhere.

The **traceability_info** folder can be used to track any static traceability information. Typically it is envisioned that this will include PC board information such as serial numbers, board configuration jumper settings, component values, etc. These files can be as detailed or sparse as needed to capture the relevant information about how the measurement was configured at the time data was taken. The state of these files will be captured and logged with each test run. The supported file format is .json which is both human and machine readable. There can be files to track other system states, PyICe is agnostic to the data stored in these files.

PyICe also has the capability to log other, more dynamic, tracking data by supplying a dictionary like data structure. One example is the serial number of the target device which may not be known until the system and device are powered up. The same would be true of test equipment serial numbers which can only be read out when the equipment is powered (Although PyICe is already configured to log this automatically).

The **quickstart_gui** folder contains a low-overhead script to get the bench equipment configured and the target device powered up. While not a recommended way to perform a detailed evaluation, the Code-free GUI can be invaluable for experimenting with the system or target device or debugging/demonstrating some simple feature or capability. Once debugging and experimenting is complete, serious data collection should be captured by collection scripts in the tests section.

The **tests** folder is recommended for storing the scripts that perform the detailed test sweeps. It is also a suitable location for collecting and archiving the results of each run of each test in an organized manner.

By scripting each test individually, the system configuration and what was done to the d.u.t. to collect the data becomes a matter of record. One of the desirable features of Python is its readability. Therefore Python scripts make an excellent record of the test procedure undertaken. This can be invaluable after the data collection is complete and is being reviewed with peers for accuracy and validity.

The **projname_base** folder contains project specific infrastructure code that is needed by all project members. **(DO WE REALLY NEED THIS FOLDER LAYER?)**

The **benches** section represents an abstraction layer containing the minimum information necessary for PyICe to physically locate all of the equipment and resources on the bench. PyICe was originally developed to be used with an ad-hoc collection of general-purpose benchtop test equipment vs a single unified test equipment platform (although that is not precluded). Since no two benches will have their equipment located on the same addresses, say COM ports, USB IDs or GPIB channels, each  team member will have their own bench file for storing this information. The benches area of the workspace should comprise the totality of unique project code per team member.

The **hardware_drivers** section is a place where project leaders can make project-specific customizations and assign project-specific channel names to instruments and their respective channels. By creating a mini_driver for each instrument and its channels, the entire team will have a single common namespace. This will greatly facilitate test review, reuse and sharing. 

PyICe contains a sizeable collection of test bench equipment drivers. If a new piece of equipment is needed, and there is no driver for it, there is usually a similar driver that can serve as an example for developing the new driver. Driver development generally takes from 1 to 8 hours per instrument depending on complexity.

The **modules** section contains project-specific infrastructure files that PyICe needs to facilitate high level goals such as environmental testing (e.g. temperature forcing on the outer loop of test suites), test results gathering and reporting, automated production to bench correlation, automated report generation, etc.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
