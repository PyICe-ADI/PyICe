import socket, os
from PyICe.lab_utils import banners, select_string_menu
from PyICe.refid_modules.plugin_module.wizard_helpers import refid_import_script_maker, bench_connection_script_maker, die_traceability_script_maker, board_traceability_script_maker

if __name__ == '__main__':
    ''' Hokay, all we really need to set up is a project name '''
    banners.print_banner("", "Welcome to the PyICE Project Creator Wizard!",
                           "This will help you get started with a basic folder structure for your new Project!",
                           "Good luck and enjoy!", "", length=90)
    project_name = input('Project name? ')
    this_machine = input(f'Setting up on what machine? [default {socket.gethostname().replace("-", "_")}] ')
    if not len(this_machine):
        this_machine = socket.gethostname().replace("-", "_")
    # this_user = input(f'Primary user? [default {os.getlogin().lower()}] ')
    # if not len(this_user):
        # this_user = os.getlogin().lower()
    project_folder = input(f"Project folder location? [default {os.path.join(os.path.dirname(os.path.abspath(__file__))[:os.path.dirname(os.path.abspath(__file__)).index('pyice-adi')],project_name)}] ")
    if not len(project_folder):
        project_folder = os.path.join(os.path.dirname(os.path.abspath(__file__))[:os.path.dirname(os.path.abspath(__file__)).index('pyice-adi')],project_name)

    new_test_module = ''
    new_bench = ''
    new_driver_init = ''
    new_user_file = ''
    new_example_script = ''
    script_creator_dict = {}
    dir_to_make = []

    dir_to_make.append(project_folder)
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
        try:
            os.mkdir(folder)
        except FileExistsError:
            print(f'{folder} name already exists. Please pick another name.')
            breakpoint()

    ###
    # PLUGINS MODULES
    ###
    plugin_util_dict = {
                        'evaluate_tests':{'plugin_file_maker':refid_import_script_maker.refid_import_script_maker,
                                        'list_str':f' # Add the refid information in {project_name}.modules.{project_name}_plugins.{project_name}_refid_import_plugin',
                                        'ready':'# ',
                                        'import_str':f'\nfrom {project_name}.modules.{project_name}_plugins.{project_name}_refid_import_plugin import {project_name}_refid_import_plugin',
                                        },
                        'bench_config_management':{'plugin_file_maker':bench_connection_script_maker.bench_connection_script_maker,
                                            'import_str':f'\nfrom {project_name}.modules.{project_name}_plugins.{project_name}_bench_connections_plugin import {project_name}_bench_connections_plugin',
                                            'list_str':f' # Add the default connection file and the image locations to modules. Templates can be found here: \\PyICe\\refid_modules\\plugin_module\\bench_connections_plugin',
                                            'ready':'# ',
                                            },
                        'traceability':{'plugin_file_maker':die_traceability_script_maker.die_traceability_script_maker,
                                            'import_str':f'\nfrom {project_name}.infrastructure.plugin_dependencies import metadata_gathering_fns',
                                            'list_str':f' # Add alternative identification procedure here if desired: {project_name}.modules.{project_name}_plugins.{project_name}_die_traceability_plugin',
                                            'ready':'',
                                            },
                        'archive':{'plugin_file_maker':None,
                                              'import_str':None,
                                              'list_str':'',
                                              'ready':'',
                                              },
                        'notifications':{'plugin_file_maker':None,
                                              'import_str':None,
                                              'list_str':f' # Add the board information in {project_name}.modules.{project_name}_plugins.{project_name}_board_traceability_plugin',
                                              'ready':'# ',
                                              },
                        'bench_image_creation':{'plugin_file_maker':None,
                                           'import_str':f'\nfrom PyICe.refid_modules.plugin_module.traceability_plugins.p4_traceability_plugin import p4_traceability_plugin',
                                           'list_str':f' # {project_name} must first be a workspace in perforce on this computer.',
                                           'ready':'# ',
                                           },
                        }
    print('\n\nPLUGINS\nPlugins add additional features to the default test module.\nThey can help with traceability and streamline evaluation.')
    plugins_to_add = []
    while True:
        if not len(plugins_to_add):
            plugin_check = input('Would you like to add a ready made plugin to your test module? ')
        else:
            plugin_check = input('Would you like to add another plugin to your test module? ')
        if plugin_check.upper() in ['NO', 'N']:
            break
        plugin_list = ['refid_import', 'bench_connections','die_traceability','bench_traceability','board_traceability', 'p4_traceability']
        to_add = select_string_menu.select_string_menu('Which plugin would you like to add?', [z for z in plugin_list if z not in plugins_to_add])
        if to_add is None:
            break
        print(f"{to_add} has been added!\n")
        plugins_to_add.append(to_add)
    for plugin in plugins_to_add:
        try:
            plugin_module = plugin_util_dict[plugin]['plugin_file_maker'](project_name)
        except TypeError:
            continue
        script_creator_dict[os.path.join(plugin_folder, f"{project_name}_{plugin}_plugin.py")] = plugin_module

    ###
    # TEST MODULE
    ###
    new_test_module += 'from PyICe.plugins.master_test_template import Master_Test_Template'
    if not len(plugins_to_add):
        new_test_module += '\n#from PyICe.refid_modules.plugin_module.traceability_plugins.p4_traceability_plugin.p4_traceability_plugin import p4_traceability_plugin as p4p'
    else:
        for plugin in plugins_to_add:
            new_test_module += plugin_util_dict[plugin]['import_str']
    new_test_module += f'\n\nclass {project_name}_test_module(tm):'
    new_test_module += f"\n\tproject_folder_name='{project_name}'"
    new_test_module += f"\n\tdef __init__(self,debug=False):"
    if not len(plugins_to_add):
        new_test_module += f"\n\t\tplugin_list = []"
        new_test_module += f"\n\t\t#plugin_list = [p4p]"
        new_test_module += f"\n\t\tfor plugin in plugin_list:"
        new_test_module += f"\n\t\t\tself.register_plugin(plugin)"
    else:
        new_test_module += f"\n\t\tplugin_list = ["
        for plugin in plugins_to_add:
            new_test_module += f"\n\t\t\t{plugin_util_dict[plugin]['ready']}{plugin_util_dict[plugin]['import_str'][plugin_util_dict[plugin]['import_str'].index('import ')+7:]}(test_mod=self),{plugin_util_dict[plugin]['list_str']}"
        new_test_module += f"\n\t\t]"
        new_test_module += f"\n\t\tfor plugin in plugin_list:"
        new_test_module += f"\n\t\t\tself.register_plugin(plugin)"
    new_test_module += f"\n\t\tsuper().__init__(debug)"
    script_creator_dict[os.path.join(modules_folder, f"{project_name}_test_module.py")] = new_test_module

    ###
    # BENCH FILE
    ###
    new_bench += 'from ..hardware_drivers import *'
    new_bench += '\n\ndef init(self,master):'
    new_bench += f'\n\tpass'
    new_bench += f'\n\t#master.add({project_name}_bk8500.bk8500(bench=self, interface=master.get_raw_serial_interface("put comport here", baudrate= 38400, timeout=1), channel_name="iout0_force, for example"))'
    script_creator_dict[os.path.join(bench_folder, f"{this_machine}.py")] = new_bench

    ###
    # USER FILE
    ###
    new_user_file += 'from PyICe import lab_utils'
    new_user_file += '\n\ndef init(self, master):'
    new_user_file += "\n\tpass"
    new_user_file += "\n\t#self.alerted_mail_address = lab_utils.email('your.email@analog.com')"
    new_user_file += "\n\t#self.add_notification(lambda msg, subject=None, attachment_filenames=[], attachment_MIMEParts=[]: self.alerted_mail_address.send(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts))"
    script_creator_dict[os.path.join(bench_folder, f"{this_user}.py")] = new_user_file

    ###
    # SAMPLE DRIVER
    ###
    new_sample_driver =  '''from PyICe import lab_instruments
                            def bk8500(bench, interface, channel_name):
                                loadbox = lab_instruments.bk8500(interface, remote_sense=True)
                                channel = loadbox.add_channel(channel_name, add_extended_channels=True)
                                loadbox.add_channel_voltage(f'{channel_name}_vforce')
                                loadbox.add_channel_remote_sense(f'{channel_name}_remote_sense')
                                bench.add_cleanup(lambda : channel.write(0))
                                return loadbox'''
    script_creator_dict[os.path.join(driver_folder, f"{project_name}_bk8500.py")] = new_sample_driver

    ###
    # DRIVER INIT
    ###
    new_driver_init += 'import os'
    new_driver_init += '\n\n__all__ = [os.path.splitext(module)[0] for module in os.listdir(os.path.dirname(__file__))]'
    new_driver_init += '\n__all__.remove("__init__")'
    script_creator_dict[os.path.join(driver_folder, f"__init__.py")] = new_driver_init

    ###
    # EXAMPLE SCRIPT
    ###
    new_example_script += f'from {project_name}.modules.{project_name}_test_module                 import {project_name}_test_module as test_module'
    new_example_script += f'\nfrom PyICe import LTC_plot'
    new_example_script += '\n\nclass test_example(test_module):'
    new_example_script += '\n\tdef setup(self, channels):\n\t\tchannels.add_channel_dummy("dumduma")\n\t\tchannels.add_channel_dummy("dumdumx")\n\t\tchannels.add_channel_dummy("dumdumy")'
    new_example_script += '\n\n\tdef collect(self, channels,debug):'
    new_example_script += '\n\t\tfor a in [-1,0,1]:'
    new_example_script += '\n\t\t\tfor x in [0,1,2,3,4]:'
    new_example_script += '\n\t\t\t\tchannels.write("dumduma", a)'
    new_example_script += '\n\t\t\t\tchannels.write("dumdumx", x)'
    new_example_script += '\n\t\t\t\tchannels.write("dumdumy", x+a+1)'
    new_example_script += '\n\t\t\t\tchannels.log()'
    new_example_script += '\n\n\tdef plot(self, database, table_name, plot_filepath, skip_output=False):'
    new_example_script += '\n\t\tplotlist=[]'
    new_example_script += '\n\t\tG0 = LTC_plot.plot( plot_title  = f"Sample Plot",'
    new_example_script += '\n\t\t                    plot_name   = f"Plot Name",'
    new_example_script += '\n\t\t                    xaxis_label = "X-Axis",'
    new_example_script += '\n\t\t                    yaxis_label = "Y-Axis",'
    new_example_script += '\n\t\t                    xlims       = (-1, 5),'
    new_example_script += '\n\t\t                    ylims       = (0,6),'
    new_example_script += '\n\t\t                    xminor      = 0,'
    new_example_script += '\n\t\t                    xdivs       = 6,'
    new_example_script += '\n\t\t                    yminor      = 0,'
    new_example_script += '\n\t\t                    ydivs       = 6,'
    new_example_script += '\n\t\t                    logx        = False,'
    new_example_script += '\n\t\t                    logy        = False)'
    new_example_script += '\n\t\tG0.add_horizontal_line(value=3, xrange=G0.xlims)'
    new_example_script += '\n\t\tcolors = LTC_plot.color_gen()'
    new_example_script += '\n\t\tfor a in database.get_distinct("dumduma"):'
    new_example_script += "\n\t\t\tdatabase.query(f'SELECT dumdumx, dumdumy FROM {table_name} WHERE dumduma is {a}')"
    new_example_script += '\n\t\t\tG0.add_trace(   axis        = 1,'
    new_example_script += '\n\t\t\t                data        = database.to_list(),'
    new_example_script += '\n\t\t\t                color       = colors(),'
    new_example_script += "\n\t\t\t                marker      = '.',"
    new_example_script += '\n\t\t\t                markersize  = 2,'
    new_example_script += "\n\t\t\t                legend      = f'EXAMPLE {a}')"
    new_example_script += '\n\t\tG0.add_legend(axis=1, location=(1, 0), use_axes_scale=False, fontsize=5)'
    new_example_script += '\n\t\tplotlist.append(G0)'
    new_example_script += '\n\t\tPage = LTC_plot.Page(plot_count=len(plotlist))'
    new_example_script += '\n\t\t[Page.add_plot(plot) for plot in plotlist]'
    new_example_script += '\n\t\tPage.create_svg(file_basename=self.get_name(), filepath=plot_filepath)'
    new_example_script += '\n\t\tPage.create_pdf(file_basename=self.get_name(), filepath=plot_filepath)'
    new_example_script += '\n\t\treturn plotlist'
    new_example_script += "\n\nif __name__ == '__main__':"
    new_example_script += "\n\t test_example.run(collect_data=True, temperatures=None, debug=True, lab_bench_constructor=None)"
    script_creator_dict[os.path.join(test_example_folder, f"test_example.py")] = new_example_script

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

    print(
        f"\nNew project {project_name} structure set!\nPlease go to the driver folder to make drivers for the instruments you'll be using, and the benches folder to add them \nto your bench, or go directly to {test_example_folder} to run an example of a test.")
    if len(plugins_to_add):
        print(f"\nSome plugins may require additional project information in order to function. \nCheck their files here for more information: {plugin_folder}")
