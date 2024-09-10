import socket, os
from PyICe.lab_utils import banners, select_string_menu

if __name__ == '__main__':
    ''' Hokay, all we really need to set up is a project name '''
    banners.print_banner("", "Welcome to the PyICE Project Creator Wizard!",
                           "This will help you get started with a basic folder structure for your new Project!",
                           "Good luck and enjoy!", "", length=90)
    project_name = input('Enter project name: ')
    this_machine = socket.gethostname().replace("-", "_")
    banners.print_banner(f'Creating a bench file for "{this_machine}".','*** Users on other benches will need to make their own bench files. ***')
    project_folder = ''
    while not len(project_folder):
        project_folder = input(f'Enter project folder location (e.g. D:\\users\\{os.getlogin().lower()}\\projects\\{project_name}): ')
        if not len(project_folder):
            print("Please enter a filepath to your project folder.")
            continue
        try:
            os.mkdir(project_folder)
        except FileExistsError:
            print(f'{project_folder} already exists. Please pick another location.\n')
            project_folder = ''

    script_creator_dict = {}
    dir_to_make = []

    project_test_folder = os.path.join(project_folder, f'tests')
    dir_to_make.append(project_test_folder)
    test_example_folder = os.path.join(project_test_folder, f'example')
    dir_to_make.append(test_example_folder)
    infrastructure_folder = os.path.join(project_folder, f'infrastructure')
    dir_to_make.append(infrastructure_folder)
    bench_folder = os.path.join(infrastructure_folder, f'benches')
    dir_to_make.append(bench_folder)
    driver_folder = os.path.join(infrastructure_folder, f'hardware_drivers')
    dir_to_make.append(driver_folder)
    plugin_folder = os.path.join(infrastructure_folder, f'plugin_dependencies')
    dir_to_make.append(plugin_folder)

    for folder in dir_to_make:
        os.mkdir(folder)

    def traceability_script_maker():
        script_str = '''from PyICe.plugins.traceability_items import traceability_items
import os

def add_bench_operator(test):
    return os.getlogin()

def get_traceability_items(test):
    our_traceability = traceability_items(test=test)
    our_traceability.add(channel_name='bench_operator', func=add_bench_operator)
    return our_traceability'''
        return script_str

    def bench_connection_addon():
        bench_method = '''
    def _declare_bench_connections(self):
        #Here user has the option to add project specific components to self.pm.test_components and default connections to self.pm.test_connections before adding the test's changes.
        self.declare_bench_connections()'''
        return bench_method

    def user_script_maker():
        user_script_str='''def get_notification_targets():
    targets =   {   
                # 'emails':['your.email@analog.com'],
                # 'texts' :[('yourphonenumber', 'yourservicecarrier')]
                }
    return targets'''
        return user_script_str

    print('\n\nPLUGINS\nPlugins add additional features to the default test template.\nThey can help with traceability and streamline evaluation.')
    plugins_to_add = []
    os.system("")
    plugin_check = input('Would you like to add plugins to your test module [\033[4mY\033[0m/N]? ')
    if not len(plugin_check) or plugin_check.upper() not in ['NO', 'N']:
        while True:
            plugin_list = ["evaluate_tests","traceability","archive","notifications","bench_config_management","bench_image_creation"]
            to_add = select_string_menu.select_string_menu('Select plugins to add, then select exit.', [(' ' if z not in plugins_to_add else '•')+z for z in plugin_list])
            if to_add is None:  ## The menu returns a None when default menu item 'exit' is selected.
                break
            elif to_add[1:] in plugins_to_add:
                plugins_to_add.remove(to_add[1:])
            else:
                plugins_to_add.append(to_add[1:])
    if 'notifications' in plugins_to_add:
        os.mkdir(os.path.join(plugin_folder, 'user_notifications'))
        script_creator_dict[os.path.join(plugin_folder, 'user_notifications', f"example_user.py")] = user_script_maker()
    if 'traceability' in plugins_to_add:
        script_creator_dict[os.path.join(plugin_folder, f"traceability.py")] = traceability_script_maker()
    plugin_str = '['
    for x in plugins_to_add:
        plugin_str+=f'"{x}",'
    plugin_str = plugin_str[:-1]
    plugin_str += ']'
    script_creator_dict[os.path.join(plugin_folder, f"plugins.json")] = plugin_str

    ###
    # TEST TEMPLATE
    ###
    new_test_template = f'from PyICe.plugins.master_test_template import Master_Test_Template'
    if 'traceability' in plugins_to_add:
        new_test_template += f'\nfrom {project_name}.infrastructure.plugin_dependencies.traceability import get_traceability_items'
    new_test_template += f'''

class Test_Template(Master_Test_Template):
    def __init__(self):
        self.project_folder_name="{project_name}"
        self.verbose=True'''
    if 'traceability' in plugins_to_add:
        new_test_template+='\n        self.traceability_items = get_traceability_items(test=self)'
    if 'bench_image_creation' in plugins_to_add:
        new_test_template+='\n        self.bench_image_locations = {} # User must add instrument images and their locations. See https://github.com/PyICe-ADI/PyICe/blob/main/docs/tutorials/tutorial_8_bench_config_management.rst'
    if 'evaluate_tests' in plugins_to_add:
        new_test_template+="\n    def get_test_limits(self, test_name):\n        #User code to determine limits of given test.\n        return {'lower_limit':None, 'upper_limit':None}"
    if 'bench_config_management' in plugins_to_add:
        new_test_template+=bench_connection_addon()
    script_creator_dict[os.path.join(plugin_folder, "test_template.py")] = new_test_template

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
    script_creator_dict[os.path.join(bench_folder, f"{this_machine}.py")] = new_bench

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
    script_creator_dict[os.path.join(driver_folder, f"example_HAMEG.py")] = new_sample_driver

    ###
    # EXAMPLE SCRIPT
    ###
    new_example_script = f'from {project_name}.infrastructure.plugin_dependencies.test_template import Test_Template\n'
    new_example_script += '''from PyICe import LTC_plot

class Test(Test_Template):
    def customize(self):
        channels = self.get_channels()
        channels.add_channel_dummy("dumduma")
        channels.add_channel_dummy("dumdumx")
        channels.add_channel_dummy("dumdumy")

    def collect(self):
        channels = self.get_channels()
        debug = self.debug
        for a in [-1,0,1]:
            for x in [0,1,2,3,4]:
                channels.write("dumduma", a)
                channels.write("dumdumx", x)
                channels.write("dumdumy", x+a+1)
                channels.log()

    def plot(self):
        database = self.db
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
        for a in database.get_distinct("dumduma"):
            database.query(f'SELECT dumdumx, dumdumy FROM {table_name} WHERE dumduma is {a}')
            G0.add_trace(   axis        = 1,
                            data        = database.to_list(),
                            color       = colors(),
                            marker      = '.',
                            markersize  = 2,
                            legend      = f'EXAMPLE {a}')
            G0.add_legend(axis=1, location=(1, 0), use_axes_scale=False, fontsize=5)
        plotlist.append(G0)
        Page = LTC_plot.Page(plot_count=len(plotlist))
        [Page.add_plot(plot) for plot in plotlist]
        Page.create_svg(file_basename=self.name, filepath=self.plot_filepath)
        Page.create_pdf(file_basename=self.name, filepath=self.plot_filepath)
        return plotlist'''
    script_creator_dict[os.path.join(test_example_folder, f"test.py")] = new_example_script

    ###
    # RUN SCRIPT
    ###
    new_run_script = '''from PyICe.plugins.plugin_manager import Plugin_Manager
from test import Test

pm = Plugin_Manager()
pm.add_test(Test)
pm.run()'''
    script_creator_dict[os.path.join(test_example_folder, f"run.py")] = new_run_script

    for (k, v) in script_creator_dict.items():
        try:
            with open(k, 'w') as f:  # overwrites existing
                f.write(v)
                f.close()
        except Exception as e:
            print(type(e))
            print(e)
            breakpoint()
            pass

    banners.print_banner("",
        f"New project '{project_name}' structure set!","Be sure the new folder is part of the PYTHONPATH in environment variables.","Please go to the driver folder to make drivers for the instruments you need","and the benches folder to add them to your bench,","or go directly to",f"{test_example_folder}","to run an example of a test.","")
    if len(plugins_to_add):
        print(f"\nBe aware: some plugins may require additional project information in order to function.")
