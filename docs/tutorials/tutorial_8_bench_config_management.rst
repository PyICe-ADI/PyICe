========================
TUTORIAL 8 Bench Configuration Management
========================

Keeping a record of exactly how a bench is set up when a test is run is crucial for repeatability testing and for building confidence that a test was run correctly. PyICe offers a method of reporting the connections amongst bench components alongside the test. Additionally, when running multiple tests that store their connections this way, the final report will be of the test's combined connections, and will even warn the user if there is a conflict with the proposed test suite.

There are two main files a test will have to import in order to use these services: bench_configuration_management, and lab_components. The bench_configuration_management file defines what a bench component is and allows for assigning connections. The lab_components is an every growing list of available components anyone can use. 

To get started, import the two files and create objects to store the components and connections utilized by the test:

.. code-block:: python

   from PyICe.bench_configuration_management   import bench_configuration_management, bench_visualizer, lab_components
   
   test_components = bench_configuration_management.component_collection()
   test_connections = bench_configuration_management.connection_collection("test_connections")


Suppose on your test bench you have an Agilent 34972 DAQ, and you are going to use a AGILENT 34908A multiplexer in one of the bays. Looking in lab_components, you see that these instruments already exist and have the following terminals to use for connections.

.. code-block:: python

	class Agilent_3497x(bench_config_component):
		def add_terminals(self):
			self.add_terminal("BAY1", instrument=self)
			self.add_terminal("BAY2", instrument=self)
			self.add_terminal("BAY3", instrument=self)

	class Agilent_34908A(bench_config_component):
		'''40 Channel Single Ended Plugin'''
		def add_terminals(self):
			self.add_terminal("BAY", instrument=self)
			self.add_terminal("SINGLE_1-8", instrument=self)
			self.add_terminal("SINGLE_9-16", instrument=self)
			self.add_terminal("SINGLE_17-24", instrument=self)
			self.add_terminal("SINGLE_25-32", instrument=self)
			self.add_terminal("SINGLE_33-40", instrument=self)
			self.add_terminal("DZ", instrument=self)

Add the components to the component_collection object, and the proposed connection to the connection_collection object like so:

.. code-block:: python

    components.add_component(lab_components.Agilent_3497x("AGILENT_3497x"))
    components.add_component(lab_components.Agilent_34908A("AGILENT_34908A"))
    test_connections.add_connection(test_components.get_components["AGILENT_3497x"]["BAY1"],             test_components.get_components["AGILENT_34908A"]["BAY"])

Additionally, PyICe offers a method of making a virtual representation of your test bench as a .svg file, like this:

*Figure out how to add an image of test bench.

To do this, a collection of images will have to be supplied, as well as where the images should be placed in the overall bench representation. For an example:

.. code-block:: python

	import pathlib

	class component_locations:
		def __init__(self):
			path =  pathlib.Path(__file__).parent.resolve().as_posix() + "/visualizer_images/"
			self.locations = {
			#####################################################
			#                                                   #
			# Test Equipment                                    #
			#                                                   #
			#####################################################
			"CONFIGURATORXT"                    : {"position" : {"xpos":0, "ypos":0}        , "image" : f"{path}ConfigXT.PNG", "use_label" : False},
			"SIGLENT"                           : {"position" : {"xpos":500, "ypos":1000}   , "image" : f"{path}Siglent.PNG", "use_label" : False},
			"SPAT"                              : {"position" : {"xpos":-800, "ypos":-200}  , "image" : f"{path}SPAT.PNG", "use_label" : False},
			"AGILENT_U2300_DAQ"                 : {"position" : {"xpos":-800, "ypos":500}   , "image" : f"{path}U2331A.PNG", "use_label" : False},
			"U2300_TO_CAT5"                     : {"position" : {"xpos":-800, "ypos":250}   , "image" : f"{path}U2331A_Adapter.PNG", "use_label" : False},
			"HAMEG"                             : {"position" : {"xpos":-700, "ypos":-500} , "image" : f"{path}Hameg4040.PNG", "use_label" : False},
			"Rampinator"                        : {"position" : {"xpos":-800, "ypos":-800}  , "image" : f"{path}Rampinator.PNG", "use_label" : False},
			"OSCILLOSCOPE"                      : {"position" : {"xpos":1350, "ypos":925}   , "image" : f"{path}Agilent3034a.PNG", "use_label" : False},
			"AGILENT_3497x"                     : {"position" : {"xpos":-800, "ypos":500}  , "image" : f"{path}Agilent34970.PNG", "use_label" : False},
			"AGILENT_34908A"                    : {"position" : {"xpos":-100, "ypos":575}  , "image" : f"{path}Agilent34908a.PNG", "use_label" : False},
			"AGILENT_34901A_2"                  : {"position" : {"xpos":-100, "ypos":500}  , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
			"AGILENT_34901A_3"                  : {"position" : {"xpos":-100, "ypos":425}   , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
			"PSA_RFMUX"                         : {"position" : {"xpos":1500, "ypos":-500}  , "image" : f"{path}HTX9016.PNG", "use_label" : False},
			"PSA"                               : {"position" : {"xpos":1850, "ypos":-1350} , "image" : f"{path}PSA.png", "use_label" : False},
			}

with the images saved in the "visualizer_images" folder mentioned in the code.

Then, all that has to be done is to make an instance of the visualizer with the components and connections of the bench and generate the image. Like so:

.. code-block:: python

    visualizer = bench_visualizer.visualizer(connections=test_connections.connections, locations=visualizer_locations.component_locations().locations)
    visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')

This will produce an svg file for easy presentation.