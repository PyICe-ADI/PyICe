from PyICe import lab_core
import importlib, socket, os

class Bench_maker():
    def __init__(self, project_folder_path):
        self.path = project_folder_path

    def make_bench(self):
        '''In this method, a master is created and returned.
        A file in the "benches" folder found anywhere under the head project folder should have the name of the computer associated with the current bench, and contains the get_instruments function.
        The name of the file should have underscores where the computer name may use dashes.
        Then, all the minidrivers are imported and the master is populated using the instruments from the bench file.
        The minidrivers (found in a "hardware_drivers" folder) define which instrument is expected and what channels names will be added for those instruments.
        The drivers also return "cleanup functions" that put the instruments in safe states once the test is complete.
        The cleanup functions are run in the order in which the instruments appear in the bench file.
        The special channel actions are functions that are run on each logging of data '''

        self.master = lab_core.master()
        self.cleanup_fns = []
        self.temperature_channel = None
        self.special_channel_actions = {}
        thismachine = socket.gethostname().replace("-","_")
        for (dirpath1, dirnames, filenames) in os.walk(self.path):
            if 'benches' not in dirpath1 or self.path not in dirpath1: continue
            try:
                benchpath = dirpath1.replace('\\', '.')
                benchpath = benchpath[benchpath.index(self.path.split('\\')[-1]):]
                module = importlib.import_module(name=benchpath+'.'+thismachine, package=None)
                break
            except ImportError as e:
                print(e)
                raise Exception(f"Can't find bench file {thismachine}. Note that dashes must be replaced with underscores.")
        instruments = module.get_instruments()
        for (dirpath, dirnames, filenames) in os.walk(self.path):
            if 'hardware_drivers' not in dirpath: continue
            driverpath = dirpath.replace('\\', '.')
            driverpath = driverpath[driverpath.index(self.path.split('\\')[-1]):]
            for driver in filenames:
                driver_mod = importlib.import_module(name=driverpath+'.'+driver[:-3], package=None)
                instrument_dict = driver_mod.populate(instruments)
                if instrument_dict['instrument'] is not None:
                    self.master.add(instrument_dict['instrument'])
                    if 'cleanup_list' in instrument_dict:
                        for fn in instrument_dict['cleanup_list']:
                            self.cleanup_fns.append(fn)
                    if 'temp_control_channel' in instrument_dict:
                        if self.temperature_channel == None:
                            self.temperature_channel = instrument_dict['temp_control_channel']
                            temp_instrument = instrument_dict['instrument']
                        else:
                            raise Exception(f'BENCH MAKER: Multiple channels have been declared the temperature control! One from {temp_instrument} and one from {instrument_dict["instrument"]}.')
                    if 'special_channel_action' in instrument_dict:
                        overwrite_check = [i.get_name() for i in instrument_dict['special_channel_action'] if i in self.special_channel_actions]
                        if overwrite_check:
                            raise Exception(f'BENCH MAKER: Multiple actions have been declared for channel(s) {overwrite_check}.')
                        self.special_channel_actions.update(instrument_dict['special_channel_action'])
                    
            break
        
        self.temperature_channel = self.master.add_channel_dummy('dummy_temp')
            
    
