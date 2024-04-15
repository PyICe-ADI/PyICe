========================
TUTORIAL 8 Bench Configuration Management
========================

Keeping a record of exactly how a bench is set up when a test is run is crucial for repeatability testing and for building confidence that a test was run correctly. PyICe offers a method of reporting the connections amongst bench components alongside the test as well as creating a .png file for easy presentation. Additionally, when running multiple tests that store their connections this way, the final report will be of the test's combined connections, and will even warn the user if there is a conflict with the proposed test suite.

There are three main files a test will have to import in order to use these services: bench_configuration_management, bench_visualizer, and lab_components. The bench_configuration_management file defines what a bench component is and allows for assigning connections. The bench visualizer is the graphing tool used to create the virtual interpretaion of the bench, and the lab_components is an every growing list of available components anyone can use. 

To get started, import the three files and create objects to store the components and connections utilized by the test:

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
