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
        script_str = '''import os

def _get_bench_operator(test):
    return os.getlogin()

def get_traceability_items():
    traceability_items ={  
                        "bench_operator"                : _get_bench_operator,
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
        #Here user has the option to add project specific components to self.pm.test_components and default connections to self.pm.test_connections before adding the test's changes.
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
        user_script_str = '''def get_notification_targets():
    targets =   {
                # 'emails':['your.email@analog.com'],
                # 'texts' :[('yourphonenumber', 'yourservicecarrier')]
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
        project_settings_str=''
        if 'traceability' in plugins_to_add:
            project_settings_str+=f'from {project_name}.infrastructure.plugin_dependencies.metadata_gathering_fns import get_traceability_items\n'
        if 'bench_config_management' in plugins_to_add:
            project_settings_str+=f'from {project_name}.infrastructure.plugin_dependencies import default_bench_configuration'
        
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

    def bench_config_comp_maker():
        ''''''
        script_str='''from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
# Add components not available in PyICe (see https://github.com/PyICe-ADI/PyICe/blob/main/PyICe/plugins/bench_configuration_management/lab_components.py)
class dummy_board(bench_config_component):
    def add_terminals(self):
        self.add_terminal("TAB_A", instrument=self)
        self.add_terminal("TAB_B", instrument=self)

class dummy_helper_board(bench_config_component):
    def add_terminals(self):
        self.add_terminal("SLOT_A", instrument=self)
        self.add_terminal("SLOT_B", instrument=self)'''
        return script_str

    def bench_conn_maker(project_name='DEFAULT'):
        ''''''
        script_str =f'from {project_name}.infrastructure.plugin_dependencies import bench_configuration_components\n'
        script_str+='''from PyICe.plugins.bench_configuration_management import lab_components

def component_collection():
    comp_coll = []
    # Add the components used for test benches here
    comp_coll.append(lab_components.four_channel_power_supply("HAMEG"))
    comp_coll.append(bench_configuration_components.dummy_board("DUMMY_BOARD"))
    comp_coll.append(bench_configuration_components.dummy_helper_board("HELPER_BOARD"))
    return comp_coll

def default_connections(components, connections):
    # Each test script will have by default the connections listed here.
    connections.add_connection(components["DUMMY_BOARD"]["TAB_A"],            components["HELPER_BOARD"]["SLOT_B"])
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
        while True:
            plugin_list = [
                "evaluate_tests",
                "traceability",
                "archive",
                "notifications",
                "bench_config_management",
                "bench_image_creation"]
            to_add = select_string_menu.select_string_menu(
                'Select plugins to add, then select exit.', [
                    (' ' if z not in plugins_to_add else '•') + z for z in plugin_list])
            if to_add is None:  # The menu returns a None when default menu item 'exit' is selected.
                break
            elif to_add[1:] in plugins_to_add:
                plugins_to_add.remove(to_add[1:])
            else:
                plugins_to_add.append(to_add[1:])
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
    script_creator_dict[os.path.join(
        plugin_folder, "project_settings.py")] = project_settings_maker(project_name, plugins_to_add)

    ###
    # TEST TEMPLATE
    ###
    new_test_template = 'from PyICe.plugins.master_test_template import Master_Test_Template'
    if 'bench_config_management' in plugins_to_add:
        new_test_template+=f'\nfrom {project_name}.infrastructure.plugin_dependencies import default_bench_configuration'
    new_test_template += f'''

class Test_Template(Master_Test_Template):
    def __init__(self):
        pass'''
    if 'evaluate_tests' in plugins_to_add:
        new_test_template += "\n    def get_test_limits(self, test_name):\n        #User code to determine limits of given test. e.g.:\n        test_limits = {'DUMDUM_TEST': {'lower_limit':0, 'upper_limit':4, 'comment':'This is just an example'}}\n        return test_limits[test_name]"
    if 'bench_config_management' in plugins_to_add:
        new_test_template += bench_connection_addon()
    script_creator_dict[os.path.join(
        plugin_folder, "test_template.py")] = new_test_template

    ###
    # BENCH FILE
    ###
    new_bench = \
        '''from PyICe.lab_interfaces import interface_factory

def get_interfaces():
    # Add the instruments used by this computer and their information as shown
    my_if = interface_factory()
    return {
            # 'HAMEG'                 : my_if.get_visa_serial_interface('COM18', baudrate= 57600), # For example
            }'''
    script_creator_dict[os.path.join(
        bench_folder, f"{this_machine}.py")] = new_bench

    ###
    # SAMPLE DRIVER
    ###
    new_sample_driver = '''from PyICe.lab_instruments.hameg_4040 import hameg_4040

def populate(self):
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
    new_example_script = f'from {project_name}.infrastructure.plugin_dependencies.test_template import Test_Template\n'
    new_example_script += '''from PyICe import LTC_plot

class Test(Test_Template):
    def retrieve_database(self):
        self.database = self.get_database()
        self.table_name = self.get_table_name()

'''
    if 'evaluate_tests' in plugins_to_add:
        new_example_script+='''
    def evaluate_results(self):
        self.retrieve_database()
        for dummya in self.database.get_distinct("dumduma"):
            self.database.query(f'SELECT dumdumy, dumduma FROM {self.table_name} WHERE dumduma is {dummya}')
            self.evaluate_db(name='DUMDUM_TEST')
'''
    if 'bench_config_management' in plugins_to_add:
        new_example_script+='''
    def declare_bench_connections(self):
        connections = self.pm.test_connections.get_connections()
        components = self.pm.test_components.get_components()
        
        ####################################### Add TARGET BOARD #############################################
        connections.add_connection(components["DUMMY_BOARD"]["TAB_B"], components["HELPER_BOARD"]["SLOT_A"])
'''
    new_example_script+='''
    def customize(self):
        channels = self.get_channels()
        channels.add_channel_dummy("dumduma")
        channels.add_channel_dummy("dumdumx")
        channels.add_channel_dummy("dumdumy")

    def collect(self):
        channels = self.get_channels()
        for a in [-1,0,1]:
            for x in [0,1,2,3,4]:
                channels.write("dumduma", a)
                channels.write("dumdumx", x)
                channels.write("dumdumy", x+a+1)
                channels.log()

    def plot(self):
        self.retrieve_database()
        table_name = self.table_name
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
    new_run_script = ''
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
            with open(k, 'w') as f:  # overwrites existing
                f.write(v)
        except Exception as e:
            print(type(e))
            print(e)
            breakpoint()

    banners.print_banner("",
                         f"New project '{project_name}' structure set!", "Be sure the new folder is part of the PYTHONPATH in environment variables.", "Please go to the driver folder to make drivers for the instruments you need", "and the benches folder to add them to your bench,", "or go directly to:", f"{test_example_folder}", "to run an example of a test.", "")
    if len(plugins_to_add):
        print("\nBe aware: some plugins may require additional project information in order to function.")
