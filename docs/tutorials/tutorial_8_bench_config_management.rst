========================
TUTORIAL 8 Bench Configuration Management
========================

Data presented without an exact understanding of how it was collected is data that can't be trusted. That is why keeping a record of exactly how a bench is set up when a test is run is crucial for repeatability testing and for building confidence that a test was run correctly. PyICe offers a method of reporting the connections amongst bench components alongside the test. Additionally, when running multiple tests as part of a suite of tests that store their connections this way, the final report will be of the test's combined connections, and will even show the proposed test suite has compatible connections.


The main features of a bench are a set of components, terminals, and connections. Each component has a set of terminals and each terminal can make a single connection to the terminal of another component. Of note, a terminal is always singular, even if it is a multipin connector. Think of a single plug and single socket serving as one connection between two terminals.

There are two main files a test will have to import in order to use these services: bench_configuration_management, and lab_components. The bench_configuration_management file defines what a bench component is and allows for assigning connections. The lab_components is an ever growing list of available components anyone can use.

Bench_configuration_management has the following classes:

* bench_config_component
    * This is the base class for all components added to your bench, whether imported from lab_components or created for a project. For example, the lab_components includes a *one_channel_power_supply*. This component has a single terminal called "VOUT1". Using lab_components as an example, each project will likely make custom components to include in their bench as part of their infrastructure. Alternatively, a PyICe contributor can add a new instrument to lab_components and submit a pull request on GitHub to expand the list of available components for future projects.
* component_collection
    * This creates a dictionary to which the instruments are added by the add_component() method.
* connection_collection
    * This creates a list of connections between terminals of all instruments for a test. Connections are added by calling the add_connection method and listing the two terminals that will be conneced, e.g. add_connection(test_components.get_components["AGILENT_3497x"]["BAY1"], test_components.get_components["AGILENT_34908A"]["BAY"]). To prevent influence on sensitive ports, terminals can also be declared "blocked". A test with a connection made to a terminal cannot be run alongside another test with that terminal "blocked". It is also in this class that connection lists from multiple tests can be merged into a set of connections using the distill method.

To get started, import the two files and create objects to store the components and connections utilized by the test:

.. code-block:: python

   from PyICe.bench_configuration_management import bench_configuration_management, lab_components
   
   test_components = bench_configuration_management.component_collection()
   test_connections = bench_configuration_management.connection_collection(name="test_connections")


Suppose on your test bench you have an Agilent 34972 DAQ, a meter that uses plugins in its 3 plugin bays. Now assume you are going to use a AGILENT 34908A plugin in one of the bays. Looking in lab_components, you see that these instruments already exist and have the following terminals to use for connections.

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

    test_components.add_component(lab_components.Agilent_3497x("AGILENT_3497x"))
    test_components.add_component(lab_components.Agilent_34908A("AGILENT_34908A"))
    test_connections.add_connection(test_components.get_components["AGILENT_3497x"]["BAY1"], test_components.get_components["AGILENT_34908A"]["BAY"])

This is just our first connection. There will likely be dozens of declared connections for a given test. Once all components and their connections are declared, the connections can be stored in a PyICe logger for storage in a SQLite database. For details on how to make a logger, see tutorial_2_logging.


.. code-block:: python

	logger.add_channel_dummy("bench_connections")
	logger.write("bench_connections", test_connections.get_connections())

They can also be displayed in your output terminal like so:

.. code-block:: python

	print(test_connections.print_connections())

Additionally, PyICe offers a method of making a virtual representation of your test bench as an svg file.

To do this, graphviz will have to be installed, as well as a collection of images will have to be supplied, and where the images should be placed in the overall bench representation. For an example:

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
			"CONFIGURATORXT"                    : {"position" : {"xpos":0,    "ypos":0}      , "image" : f"{path}ConfigXT.PNG", "use_label" : False},
			"HAMEG"                             : {"position" : {"xpos":-700, "ypos":-500}   , "image" : f"{path}Hameg4040.PNG", "use_label" : False},
			"AGILENT_3497x"                     : {"position" : {"xpos":-800, "ypos":500}    , "image" : f"{path}Agilent34970.PNG", "use_label" : False},
			"AGILENT_34908A"                    : {"position" : {"xpos":-100, "ypos":575}    , "image" : f"{path}Agilent34908a.PNG", "use_label" : False},
			"AGILENT_34901A_2"                  : {"position" : {"xpos":-100, "ypos":500}    , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
			"AGILENT_34901A_3"                  : {"position" : {"xpos":-100, "ypos":425}    , "image" : f"{path}Agilent34901A.PNG", "use_label" : False},
			}

Each component's position will have to be carefully arranged to not interfere with each other and to allow for space for the automated wiring to be computed by graphviz.
with the images saved in the "visualizer_images" folder mentioned in the code.

Then, all that has to be done is to make an instance of the visualizer with the connections of the bench and generate the image:

.. code-block:: python

    visualizer = bench_visualizer.visualizer(connections=test_connections.connections, locations=visualizer_locations.component_locations().locations)
    visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')

This will produce an svg file for easy presentation, such as:

https://github.com/PyICe-ADI/PyICe/tree/main/PyICe/tutorials/bench_config_management_tutorial/bench_image_example/Bench_Config.svg

Note that while the wiring is not physically accurate terminal to terminal, hoving over a wire will reveal what connection it represents in regards to both components and terminals.