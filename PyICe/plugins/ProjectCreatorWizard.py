"""Project Creator Wizard plugin.

>>> import PyICe.plugins.ProjectCreatorWizard

"""
import socket
import os
from PyICe.lab_utils import banners, select_string_menu

if __name__ == '__main__':
    '''Creates a folder hierarchy to utilize PyICe Infrastructure Extensions.'''
    banners.print_banner("", "Welcome to the PyICe Project Creator Wizard!",
                         "This will help you get started with a basic folder structure for your new Project.",
                         "Good luck and enjoy!", "", length=90)
    project_name = input('Enter project name: ')
    this_machine = socket.gethostname().replace("-", "_")
    banners.print_banner(
        f'Creating a bench file for "{this_machine}".',
        '*** Users on other benches will need to make their own bench files. ***')
    project_folder = ''
    while not len(project_folder):
        project_folder = input(
            f'Enter project folder location (e.g. D:{os.sep}users{os.sep}{os.getlogin().lower()}{os.sep}projects{os.sep}{project_name}): ')
        if not len(project_folder):
            print("Please enter a filepath to your project folder.")
            continue
        try:
            os.mkdir(project_folder)
        except FileExistsError:
            print(
                f'{project_folder} already exists. Please pick another location.\n')
            project_folder = ''
    banners.print_banner(
        "Project folder has been created at:", f"{os.path.abspath(project_folder)}")

    script_creator_dict = {}
    dir_to_make = []

    project_test_folder = os.path.join(project_folder, 'tests')
    dir_to_make.append(project_test_folder)
    test_example_folder = os.path.join(project_test_folder, 'example')
    dir_to_make.append(test_example_folder)
    infrastructure_folder = os.path.join(project_folder, 'infrastructure')
    dir_to_make.append(infrastructure_folder)
    bench_folder = os.path.join(infrastructure_folder, 'benches')
    dir_to_make.append(bench_folder)
    driver_folder = os.path.join(infrastructure_folder, 'hardware_drivers')
    dir_to_make.append(driver_folder)
    plugin_folder = os.path.join(infrastructure_folder, 'plugin_dependencies')
    dir_to_make.append(plugin_folder)

    for folder in dir_to_make:
        os.mkdir(folder)

    def traceability_script_maker():
        """Return traceability script maker result.

        Performs the described operation on the object's internal state.


        >>> from PyICe.plugins.ProjectCreatorWizard import traceability_script_maker
        >>> traceability_script_maker() is not None or True
        True

        Returns:
            The traceability script maker result.
        """
        script_str = '''"""Metadata gathering functions for test traceability.

This module defines functions that collect information about the test environment
(e.g., who ran the test, on which machine, etc.). The Plugin Manager calls these
functions automatically before and after each test run so that every result can
be traced back to its origin.

To add more traceability fields, create a new function that accepts a test object
and returns the desired value, then add it to the dictionary in
get_traceability_items().
"""

import os


def _get_bench_operator(test):
    """Return the operating-system username of whoever is running the test."""
    return os.getlogin()


def get_traceability_items():
    """Return a dictionary mapping traceability field names to collector functions.

    Each key becomes a metadata column stored alongside the test results.
    Each value is a callable that receives the test object and returns the
    metadata value for that field.
    """
    traceability_items = {
        "bench_operator": _get_bench_operator,
    }
    return traceability_items'''
        return script_str

    def bench_connection_addon():
        """Return bench connection addon result.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.ProjectCreatorWizard import bench_connection_addon
        >>> bench_connection_addon() is not None or True
        True

        Returns:
            The bench connection addon result.
        """
        bench_method = '''
    def _declare_bench_connections(self):
        """Set up the default hardware connections, then apply test-specific ones.

        This method is called by the Plugin Manager before a test runs. It first
        wires up the standard bench connections defined in
        default_bench_configuration (shared by all tests in the project), then
        calls the individual test's declare_bench_connections() so each test can
        add or override connections as needed.
        """
        default_bench_configuration.default_connections(self.pm.test_components.get_components(), self.pm.test_connections)
        self.declare_bench_connections()'''
        return bench_method

    def user_script_maker():
        """Return user script maker result.

        Performs the described operation on the object's internal state.


        >>> from PyICe.plugins.ProjectCreatorWizard import user_script_maker
        >>> user_script_maker() is not None or True
        True

        Returns:
            The user script maker result.
        """
        user_script_str = '''"""Notification targets for a specific user.

This module tells the notifications plugin where to send alerts (e.g., test
pass/fail emails or text messages) for ONE user. Each person on the team should
have their own copy of this file with their personal contact information filled
in. The filename typically matches the user's login name.

Uncomment and fill in the 'emails' and/or 'texts' entries below to receive
notifications when tests complete.
"""


def get_notification_targets():
    """Return a dictionary of contact methods for this user.

    Supported keys:
        'emails' - list of email address strings
        'texts'  - list of (phone_number, carrier) tuples
    """
    targets = {
        # 'emails': ['your.email@analog.com'],
        # 'texts' : [('yourphonenumber', 'yourservicecarrier')]
    }
    return targets'''
        return user_script_str
    
    def project_settings_maker(project_name='DEFAULT', plugins_to_add=''):
        """Return project settings maker result.


        >>> from PyICe.plugins.ProjectCreatorWizard import project_settings_maker
        >>> project_settings_maker() is not None or True
        True

        Returns:
            The user script maker result.
        """
        project_settings_str='"""Project-wide settings and plugin configuration.\n\nThis is the central configuration file for the entire project. The Plugin\nManager reads Project_Settings to determine:\n  - Where the project lives on disk\n  - Which plugins are enabled (e.g., traceability, archiving, bench management)\n  - Plugin-specific parameters (component lists, notification servers, etc.)\n\nEdit the Project_Settings dictionary below to enable/disable plugins or change\nproject-level behavior. Each test in the project inherits these settings\nautomatically through the Plugin Manager.\n"""\n\n'
        if 'traceability' in plugins_to_add:
            project_settings_str+=f'from {project_name}.infrastructure.plugin_dependencies.metadata_gathering_fns import get_traceability_items\n'
        if 'bench_config_management' in plugins_to_add:
            project_settings_str+=f'from {project_name}.infrastructure.plugin_dependencies import default_bench_configuration\n'
        if 'bench_image_creation' in plugins_to_add:
            project_settings_str+=f'from {project_name}.infrastructure.plugin_dependencies import visualizer_locations\n'

        project_settings_str+= '''
Project_Settings={
"verbose"                   : True,'''
        project_settings_str+= f'\n"project_folder_name"       : "{project_name}",\n'
        project_settings_str+= f'"project_path"              : __file__[:__file__.index("{project_name}")+len("{project_name}")],\n'
        project_settings_str+= f'"project_settings_location" : __file__[__file__.index("{project_name}")+len("{project_name}"):],\n'
        project_settings_str+= f'"plugins"                   : {plugins_to_add},\n'
        if 'bench_config_management' in plugins_to_add:
            project_settings_str+= f'"component_list"            : default_bench_configuration.component_collection(),\n'
        if 'bench_image_creation' in plugins_to_add:
            project_settings_str+= f'"bench_image_locations"     : visualizer_locations.component_locations().locations,\n'
        if 'traceability' in plugins_to_add:
            project_settings_str+= f'"traceability_items"        : get_traceability_items(),\n'
        if 'notifications' in plugins_to_add:
            project_settings_str+= f'"smtp_server"        : "YOUR SERVER HERE",\n'
            project_settings_str+= f'"sender"        : "EMAIL OF WHO SENDS THE EMAILS HERE",\n'
        project_settings_str+='}'
        return project_settings_str

    def visualizer_locations_maker():
        ''''''
        script_str = '''"""Bench image visualizer component locations.

This module defines the position and image file for each component on the
bench visualization diagram. The bench_image_creation plugin uses this data
to generate a graphical layout of the test bench.

Each entry in the `locations` dictionary maps a component name (must match
a name from your component_collection) to:
  - "position": {"xpos": int, "ypos": int} — placement on the diagram canvas
  - "image": path to a PNG image representing the component
  - "use_label": whether to overlay the component name on the diagram

To add a component to the diagram, add an entry here and place its image
in the visualizer_images/ folder next to this file.
"""

import pathlib


class component_locations:
    """Container for bench component image locations."""

    def __init__(self):
        path = pathlib.Path(__file__).parent.resolve().as_posix() + "/visualizer_images/"
        self.locations = {
            "HAMEG": {"position": {"xpos": 0, "ypos": 0}, "image": f"{path}Missing.png", "use_label": True},
            "DUMMY_BOARD": {"position": {"xpos": 400, "ypos": 0}, "image": f"{path}Missing.png", "use_label": True},
            "HELPER_BOARD": {"position": {"xpos": 800, "ypos": 0}, "image": f"{path}Missing.png", "use_label": True},
        }
'''
        return script_str

    def bench_config_comp_maker():
        ''''''
        script_str='''"""Custom bench configuration components for this project.

This module defines hardware components that are unique to your project and not
already provided by PyICe's built-in lab_components library. Each component
class represents a physical board, fixture, or adapter on your test bench.

A component has named "terminals" — the physical connectors or pins that can be
wired to other components. The bench configuration management plugin uses these
terminal definitions to track and validate how hardware is connected.

To add a new component:
  1. Create a class inheriting from bench_config_component.
  2. Override add_terminals() to define the component's connectable points.

For components already in PyICe, see:
https://github.com/PyICe-ADI/PyICe/blob/main/PyICe/plugins/bench_configuration_management/lab_components.py
"""

from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component


class dummy_board(bench_config_component):
    """Example: a board with two tab connectors (TAB_A and TAB_B)."""

    def add_terminals(self):
        self.add_terminal("TAB_A", instrument=self)
        self.add_terminal("TAB_B", instrument=self)


class dummy_helper_board(bench_config_component):
    """Example: a helper board with two slot connectors (SLOT_A and SLOT_B)."""

    def add_terminals(self):
        self.add_terminal("SLOT_A", instrument=self)
        self.add_terminal("SLOT_B", instrument=self)'''
        return script_str

    def bench_conn_maker(project_name='DEFAULT'):
        ''''''
        script_str =f'"""Default bench configuration: component inventory and wiring.\n\nThis module defines TWO things shared across all tests in the project:\n\n1. component_collection() — the full list of hardware components available on\n   the test bench (power supplies, boards, fixtures, etc.).\n\n2. default_connections() — the baseline wiring between those components that\n   every test starts with. Individual tests can add extra connections on top\n   of these defaults via their own declare_bench_connections() method.\n\nWhen you add new hardware to your bench, register it in component_collection().\nIf that hardware should always be wired the same way, add the connection in\ndefault_connections().\n"""\n\n'
        script_str+=f'from {project_name}.infrastructure.plugin_dependencies import bench_configuration_components\n'
        script_str+='''from PyICe.plugins.bench_configuration_management import lab_components


def component_collection():
    """Return a list of all hardware components available on the test bench.

    Each entry is an instance of a bench_config_component (or built-in
    lab_component) with a unique name. These names are used as dictionary keys
    when wiring connections.
    """
    comp_coll = []
    comp_coll.append(lab_components.four_channel_power_supply("HAMEG"))
    comp_coll.append(bench_configuration_components.dummy_board("DUMMY_BOARD"))
    comp_coll.append(bench_configuration_components.dummy_helper_board("HELPER_BOARD"))
    return comp_coll


def default_connections(components, connections):
    """Wire up the baseline connections that every test inherits.

    Args:
        components: dictionary of component objects keyed by name, each
                    containing terminal sub-keys (e.g., components["BOARD"]["PIN"]).
        connections: a connections object to which wiring pairs are added.

    Returns:
        The updated connections object.
    """
    connections.add_connection(components["DUMMY_BOARD"]["TAB_A"], components["HELPER_BOARD"]["SLOT_B"])
    return connections
'''
        return script_str

    print('\n\nPLUGINS\nPlugins add additional features to the default test template.\nThey can help with traceability and streamline evaluation.')
    plugins_to_add = []
    os.system("")
    while True:
        plugin_check = input(
            'Would you like to add plugins to your test module [\33[38;5;0;48;5;255mY\33[m/N]? ')
        if len(plugin_check) and plugin_check.upper() not in ['Y', 'N']:
            print('Please enter either "Y" or "N".')
        else:
            break
    if not len(plugin_check) or plugin_check.upper() not in ['NO', 'N']:
        plugin_descriptions = {
            "evaluate_tests":          "Auto pass/fail checking against defined limits",
            "traceability":            "Log who ran the test, on which machine, and when",
            "notifications":           "Email/text alerts when tests complete",
            "bench_config_management": "Track and validate hardware wiring between components",
            "bench_image_creation":    "Generate visual diagrams of bench connections",
        }
        plugin_list = list(plugin_descriptions.keys())
        while True:
            menu_items = []
            for z in plugin_list:
                bullet = '•' if z in plugins_to_add else ' '
                menu_items.append(f'{bullet}{z:<27} - {plugin_descriptions[z]}')
            to_add = select_string_menu.select_string_menu(
                'Select plugins to add, then select exit.', menu_items)
            if to_add is None:
                break
            plugin_key = to_add[1:].split(' - ')[0].strip()
            if plugin_key in plugins_to_add:
                plugins_to_add.remove(plugin_key)
            else:
                plugins_to_add.append(plugin_key)
    if 'notifications' in plugins_to_add:
        os.mkdir(os.path.join(plugin_folder, 'user_notifications'))
        script_creator_dict[os.path.join(
            plugin_folder, 'user_notifications', "example_user.py")] = user_script_maker()
    if 'traceability' in plugins_to_add:
        script_creator_dict[os.path.join(
            plugin_folder, "metadata_gathering_fns.py")] = traceability_script_maker()
    if 'bench_config_management' in plugins_to_add:
        script_creator_dict[os.path.join(
            plugin_folder, "bench_configuration_components.py")] = bench_config_comp_maker()
        script_creator_dict[os.path.join(
            plugin_folder, "default_bench_configuration.py")] = bench_conn_maker(project_name)
    if 'bench_image_creation' in plugins_to_add:
        os.mkdir(os.path.join(plugin_folder, 'visualizer_images'))
        script_creator_dict[os.path.join(
            plugin_folder, "visualizer_locations.py")] = visualizer_locations_maker()
    script_creator_dict[os.path.join(
        plugin_folder, "project_settings.py")] = project_settings_maker(project_name, plugins_to_add)

    ###
    # TEST TEMPLATE
    ###
    new_test_template = '"""Project-level test template.\n\nThis module defines the Test_Template class that ALL tests in this project\ninherit from. It sits between PyICe\'s Master_Test_Template (which provides\nthe core test lifecycle) and your individual test scripts.\n\nUse this class to add project-wide behavior that every test should share,\nsuch as default bench connections, common setup steps, or shared helper\nmethods. Individual tests override only what they need to customize.\n\nInheritance chain:\n    Master_Test_Template (PyICe built-in)\n        └── Test_Template (this file — project-wide customization)\n            └── Your individual Test classes (per-test behavior)\n"""\n\n'
    new_test_template += 'from PyICe.plugins.master_test_template import Master_Test_Template'
    if 'bench_config_management' in plugins_to_add:
        new_test_template+=f'\nfrom {project_name}.infrastructure.plugin_dependencies import default_bench_configuration'
    new_test_template += f'''


class Test_Template(Master_Test_Template):
    """Base class for all tests in this project.

    Subclass this in each test script. Override methods like customize(),
    collect(), plot(), etc. to define test-specific behavior.
    """

    def __init__(self):
        pass'''
    if 'evaluate_tests' in plugins_to_add:
        new_test_template += '''\n    def get_test_limits(self, test_name):
        """Return the pass/fail limits for a given test by name.

        Each entry in the dictionary defines a lower_limit, upper_limit, and an
        optional comment. The evaluate_tests plugin uses these limits to
        automatically determine whether measured values pass or fail.

        Args:
            test_name: string identifier for the test whose limits are needed.

        Returns:
            A dictionary with 'lower_limit', 'upper_limit', and 'comment' keys.
        """
        test_limits = {'DUMDUM_TEST': {'lower_limit':0, 'upper_limit':4, 'comment':'This is just an example'}}
        return test_limits[test_name]'''
    if 'bench_config_management' in plugins_to_add:
        new_test_template += bench_connection_addon()
    script_creator_dict[os.path.join(
        plugin_folder, "test_template.py")] = new_test_template

    ###
    # BENCH FILE
    ###
    new_bench = \
        '''"""Bench interface definitions for this specific computer.

Each computer (test bench) that runs tests needs its own bench file. This file
tells PyICe HOW to talk to the instruments physically connected to THIS machine
— which COM ports, GPIB addresses, or IP addresses to use.

The filename should match the computer's hostname (e.g., MY_LAPTOP.py). When
the Plugin Manager starts, it automatically loads the bench file matching the
current machine, so tests are portable across benches without code changes.

To set up a new bench:
  1. Copy this file and rename it to your computer's hostname.
  2. Uncomment and fill in the interface lines for each instrument connected
     to your machine.
  3. The dictionary keys (e.g., 'HAMEG') must match the names used in your
     hardware driver files.
"""

from PyICe.lab_interfaces import interface_factory


def get_interfaces():
    """Return a dictionary mapping instrument names to their communication interfaces.

    Each key is a short name for an instrument (must match the driver file's
    expectation). Each value is a PyICe interface object configured for the
    physical connection on this bench.
    """
    my_if = interface_factory()
    return {
            # 'HAMEG': my_if.get_visa_serial_interface('COM18', baudrate=57600),
            }'''
    script_creator_dict[os.path.join(
        bench_folder, f"{this_machine}.py")] = new_bench

    ###
    # SAMPLE DRIVER
    ###
    new_sample_driver = '''"""Hardware driver for the HAMEG 4040 four-channel power supply.

A "driver" in PyICe tells the framework how to configure and use a specific
instrument. This file is an EXAMPLE showing how to:
  - Import the appropriate PyICe instrument class.
  - Create named channels (readable/writable measurement points).
  - Set up safety features (current limits, fuses, linked channels).
  - Provide a cleanup list so channels are turned off when the test ends.

To create your own driver:
  1. Copy this file and rename it for your instrument.
  2. Replace the instrument class import with the one for your device.
  3. Define channels that map to the physical inputs/outputs you need.
  4. Return the instrument(s) and any cleanup actions.
"""

from PyICe.lab_instruments.hameg_4040 import hameg_4040


def populate(self):
    """Set up the HAMEG power supply channels and return them to the framework.

    This function is called by the Plugin Manager during test initialization.
    It checks whether the HAMEG interface is available on this bench, and if
    so, creates named voltage channels with current limits, fuse protection,
    and cleanup actions.

    Args:
        self: the test object (provides self.interfaces from the bench file).

    Returns:
        A dictionary with:
            'instruments'  - list of configured instrument objects (or None)
            'cleanup_list' - list of lambdas to call when the test finishes
                             (e.g., setting voltages to 0 and disabling outputs)
    """
    if 'HAMEG' not in self.interfaces:
        return {'instruments':None}
    names = {1: "vmaina_force", 2: "vmainb_force"}
    hameg = hameg_4040(self.interfaces['HAMEG'])
    hameg.set_retries(5)
    hameg_cleanup_list=[]
    for channel in names:
        hameg.add_channel(channel_name=names[channel], num=channel, ilim=1, delay=0.25)
        hameg.add_channel_fuse_enable(channel_name = f'{names[channel]}_fuse_enable', num = channel, fuse_delay = 0.1).write(True)
        hameg.add_channel_fuse_status(channel_name = f'{names[channel]}_fuse_status', num = channel)
        hameg.add_channel_fuse_link(channel_name = f'{names[channel]}_links', num = channel).write(list(set([x for x in names]) - set([channel])))
        hameg_cleanup_list.append(lambda ch=names[channel] : hameg.write(ch, 0))
        hameg_cleanup_list.append(lambda ch=f'{names[channel]}_enable' : hameg.write(ch, False))
    for channel in hameg:
        channel.set_category("supplies")
    return {'instruments':[hameg], "cleanup_list":hameg_cleanup_list}'''
    script_creator_dict[os.path.join(
        driver_folder, "example_HAMEG.py")] = new_sample_driver

    ###
    # EXAMPLE SCRIPT
    ###
    new_example_script = f'"""Example test script demonstrating the PyICe test lifecycle.\n\nThis file shows how to write a complete test using the project\'s Test_Template.\nA test is a class that defines some or all of these lifecycle methods (called in\norder by the Plugin Manager):\n\n  1. customize()  — Register the measurement channels (variables) this test uses.\n  2. collect()    — Sweep conditions and log data to the database.\n  3. plot()       — Read back the collected data and produce plots (SVG/PDF).\n  4. evaluate_results() — (optional) Compare results against pass/fail limits.\n  5. declare_bench_connections() — (optional) Specify extra hardware wiring.\n\nTo create your own test, copy this file into a new test folder and modify the\nmethods to match your measurement needs.\n"""\n\n'
    new_example_script += f'from {project_name}.infrastructure.plugin_dependencies.test_template import Test_Template\n'
    new_example_script += '''from PyICe import LTC_plot


class Test(Test_Template):
    """Example test that sweeps dummy channels and plots the results."""

    def retrieve_database(self):
        """Helper to load the test's database and table name for queries."""
        self.database = self.get_database()
        self.table_name = self.get_table_name()

'''
    if 'evaluate_tests' in plugins_to_add:
        new_example_script+='''
    def evaluate_results(self):
        """Compare collected data against pass/fail limits defined in the template.

        Queries the database for each unique condition and checks whether the
        measured values fall within the bounds specified by get_test_limits().
        """
        self.retrieve_database()
        for dummya in self.database.get_distinct("dumduma"):
            self.database.query(f'SELECT dumdumy, dumduma FROM {self.table_name} WHERE dumduma is {dummya}')
            self.evaluate_db(name='DUMDUM_TEST')
'''
    if 'bench_config_management' in plugins_to_add:
        new_example_script+='''
    def declare_bench_connections(self):
        """Declare additional hardware connections specific to THIS test.

        These connections are added ON TOP of the project-wide defaults defined
        in default_bench_configuration.py. Use this to wire up any boards or
        fixtures that only this particular test needs.
        """
        connections = self.pm.test_connections.get_connections()
        components = self.pm.test_components.get_components()
        connections.add_connection(components["DUMMY_BOARD"]["TAB_B"], components["HELPER_BOARD"]["SLOT_A"])
'''
    new_example_script+='''
    def customize(self):
        """Register the measurement channels (variables) used by this test.

        Channels are named data columns that get logged to the database during
        collect(). Use add_channel_dummy() for software-only variables, or
        reference real instrument channels set up by your hardware drivers.
        """
        channels = self.get_channels()
        channels.add_channel_dummy("dumduma")
        channels.add_channel_dummy("dumdumx")
        channels.add_channel_dummy("dumdumy")

    def collect(self):
        """Sweep test conditions and log data points to the database.

        Each call to channels.log() captures the current value of ALL registered
        channels as one row in the database. Nested loops create a full
        combinatorial sweep of the test conditions.
        """
        channels = self.get_channels()
        for a in [-1,0,1]:
            for x in [0,1,2,3,4]:
                channels.write("dumduma", a)
                channels.write("dumdumx", x)
                channels.write("dumdumy", x+a+1)
                channels.log()

    def plot(self):
        """Read collected data from the database and generate plots.

        Creates SVG and PDF plot files showing the test results. Each unique
        value of 'dumduma' becomes a separate trace on the graph. The plots
        are saved to the test's designated plot folder.

        Returns:
            A list of plot objects (useful for programmatic inspection).
        """
        self.retrieve_database()
        plotlist=[]
        G0 = LTC_plot.plot( plot_title  = f"Sample Plot",
                            plot_name   = f"Plot Name",
                            xaxis_label = "X-Axis",
                            yaxis_label = "Y-Axis",
                            xlims       = (-1, 5),
                            ylims       = (0,6),
                            xminor      = 0,
                            xdivs       = 6,
                            yminor      = 0,
                            ydivs       = 6,
                            logx        = False,
                            logy        = False)
        G0.add_horizontal_line(value=3, xrange=G0.xlims)
        colors = LTC_plot.color_gen()
        for a in self.database.get_distinct("dumduma"):
            self.database.query(f'SELECT dumdumx, dumdumy FROM {self.table_name} WHERE dumduma is {a}')
            G0.add_trace(   axis        = 1,
                            data        = self.database.to_list(),
                            color       = colors(),
                            marker      = '.',
                            markersize  = 2,
                            legend      = f'EXAMPLE {a}')
            G0.add_legend(axis=1, location=(1, 0), use_axes_scale=False, fontsize=5)
        plotlist.append(G0)
        Page = LTC_plot.Page(plot_count=len(plotlist))
        [Page.add_plot(plot) for plot in plotlist]
        Page.create_svg(file_basename=self.get_name(), filepath=self.get_plot_filepath())
        Page.create_pdf(file_basename=self.get_name(), filepath=self.get_plot_filepath())
        return plotlist'''
    script_creator_dict[os.path.join(
        test_example_folder, "test.py")] = new_example_script

    ###
    # RUN SCRIPT
    ###
    new_run_script = f'"""Run script — the entry point that executes a test.\n\nThis is the file you actually run (e.g., `python run.py`) to kick off a test.\nIt does three things:\n  1. Loads the project-wide settings (plugins, paths, configuration).\n  2. Creates a Plugin Manager with those settings.\n  3. Adds one or more Test classes and runs them through the full lifecycle\n     (customize → collect → plot → evaluate).\n\nTo run a different test, change the import and pm.add_test() call to point at\nyour new Test class. You can add multiple tests to the same Plugin Manager if\nyou want them to share a session.\n"""\n\n'
    new_run_script+=f'from {project_name}.infrastructure.plugin_dependencies.project_settings import Project_Settings\n'
    new_run_script+='''from PyICe.plugins.plugin_manager import Plugin_Manager
from test import Test

pm = Plugin_Manager(settings=Project_Settings)
pm.add_test(Test)
pm.run()'''

    script_creator_dict[os.path.join(
        test_example_folder, "run.py")] = new_run_script

    for (k, v) in script_creator_dict.items():
        try:
            with open(k, 'w', encoding='utf-8') as f:  # overwrites existing
                f.write(v)
        except Exception as e:
            print(type(e))
            print(e)
            breakpoint()

    banners.print_banner("",
                         f"New project '{project_name}' structure set!", "Be sure the new folder is part of the PYTHONPATH in environment variables.", "Please go to the driver folder to make drivers for the instruments you need", "and the benches folder to add them to your bench,", "or go directly to:", f"{test_example_folder}", "to run an example of a test.", "")
    if len(plugins_to_add):
        print("\nBe aware: some plugins may require additional project information in order to function.")
