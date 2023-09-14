from PyICe.refid_modules.plugin_module.plugin       import plugin
from PyICe import lab_utils
from types import MappingProxyType
import inspect
import collections
import re
import subprocess
import sys

class results_dict(collections.OrderedDict):
    '''Ordered dictionary with pretty print addition.'''
    def __str__(self):
        s = ''
        max_key_name_length = 0
        for k,v in self.items():
            max_key_name_length = max(max_key_name_length, len(k))
            s += '{}:\t{}\n'.format(k,v)
        s = s.expandtabs(max_key_name_length+2)
        return s

fstat_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
edit_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
client_pat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
describe_zpat = re.compile(r'^\.\.\. (?P<f_name>\w+) (?P<f_val>.*?)\s*?$', re.MULTILINE)
class p4_traceability_plugin(plugin):
    def __init__(self, test_mod):
        super().__init__(test_mod)
        from .p4_traceability_plugin import results_dict

    def __str__(self):
        return "Adds columns to the database that records revision info on the test script and allows for checking out files before editting them via the script."

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                   'DB_unversioned_check':self.DB_unversioned_check,
                   'add_p4_traceability_channels':self.add_p4_traceability_channels,
                   'get_client_info':self.get_client_info,
                   'get_describe':self.get_describe,
                   'p4_edit':self.p4_edit,
                    })
    def get_atts(self):
        return self.att_dict

    def get_hooks(self):
        plugin_dict={
                    'tm_set':[self._set_variables],
                    'tm_logger_setup': [self.DB_unversioned_check, self.add_p4_traceability_channels, self.add_bench_p4_traceability_channels],
                    'tm_plot':[self._p4_plot_armor],
                    }
        return plugin_dict
    def set_interplugs(self):
        pass
    def execute_interplugs(self, hook_key, *args, **kwargs):
        for (k,v) in self.tm.interplugs.items():
            if k is hook_key:
                for f in v:
                    f(*args, **kwargs)

    def _p4_plot_armor(self, *args, **kwargs):
        """
        Makes a copy of the script's plot method, then replaces it with the plugin's own, which is just the script's plot method but with a decorator.
        """
        self.tm.regular_plot = self.tm.plot
        bound_method = p4_traceability_plugin.plot.__get__(self.tm, self.tm.__class__)              ## Hokay, this takes an unbound version of the plugin method and binds a particular instance to the test_module. 
        setattr(self.tm,'plot',bound_method)

    def _set_variables(self, *args, **kwargs):
        """
        Simply cookies to keep repeat calls to function under control.
        """
        self.auto_checkout=False
        self.already_asked=False
        self.tm.tt._once_is_enough=True

    def add_p4_traceability_channels(self, logger):
        """
        Adds the perforce information of the script to the logger.
        
        Args:
            logger - The logger that will get the perforce channels.
        """
        ch_cat = 'eval_traceability'
        module_file = inspect.getsourcefile(type(self.tm))
        fileinfo = self.get_fstat(module_file)
        if fileinfo['depotFile'] is None:
            lab_utils.print_banner(f"{self.tm.get_name()} is not checked in.")
        for property in fileinfo:
            logger.add_channel_dummy(f'test_{property}').write(fileinfo[property])
            logger[f'test_{property}'].set_category(ch_cat)
            logger[f'test_{property}'].set_write_access(False)
        if type(self.tm)._archive_enabled == False: #Class variable
            # Don't nag. Asked and answered.
            pass
        elif not self.tm._debug and fileinfo['depotFile'] is None:
            lab_utils.print_banner(f"Test module unversioned: {self.tm.get_name()}")
            resp = input('You will not be able to archive results. Press "y" to continue: ')
            if resp.lower() != 'y':
                raise Exception('Unversioned test module.')
            else:
                type(self.tm)._archive_enabled = False # Added strangely late?! 2020/09/01 DJS.
        elif not self.tm._debug and fileinfo['action'] is not None:
            lab_utils.print_banner("*** WARNING ***", f"Test module uncommitted changes: {self.tm.get_name()}")
            resp = input('You will not be able to archive results. Press "y" to continue: ')
            if resp.lower() != 'y':
                raise Exception('Uncommitted test module working copy.')
            else:
                type(self)._archive_enabled = False
        try:
            for child_module in self.tm._multitest_units:
                multitest_module_file = inspect.getsourcefile(type(child_module))
                fileinfo = self.get_fstat(multitest_module_file)
                if fileinfo['depotFile'] is None:
                    lab_utils.print_banner(f"{child_module.get_name()} is not checked in.")
                # print(fileinfo)
                # Todo: Actual checks and datalogging????
        except AttributeError as e:
            # Not a multitest parent module
            pass

    def add_bench_p4_traceability_channels(self, logger):
        """
        Adds the perforce information about the bench file to the logger.
        
        Args:
            logger - The logger that will get the perforce channels.
        """
        ch_cat = 'eval_traceability'
        module_file = inspect.getsourcefile(self.tm.get_lab_bench().get_bench_file())
        fileinfo = self.get_fstat(module_file)
        module_name=module_file[-1*module_file[::-1].index('\\'):]
        for property in fileinfo:
            logger.add_channel_dummy(f'bench_{property}').write(fileinfo[property])
            logger[f'bench_{property}'].set_category(ch_cat)
            logger[f'bench_{property}'].set_write_access(False)
        if fileinfo['depotFile'] is None:
            lab_utils.print_banner(f"Lab bench {module_name} unversioned.")
            resp = input('Press "y" to continue: ')
            if resp.lower() != 'y':
                raise Exception('Unversioned bench module.')
        elif fileinfo['action'] is not None and self.tm.tt._once_is_enough:
            lab_utils.print_banner(f"WARNING: Lab bench {module_name} has uncommitted changes.")
            resp = input('Press "y" to continue: ')
            if resp.lower() != 'y':
                raise Exception('Uncommitted bench module working copy.')
            self.tm.tt._once_is_enough = False

    def DB_unversioned_check(self, logger):
        """
        Raises an error if a database is checked in. 
        """
        log_info = self.get_fstat(logger.get_database())
        if log_info['depotFile'] is not None and log_info['action'] is None and log_info['headAction'] not in ['delete','move/delete']:
            # TODO: Ask to p4 check out
            raise Exception(f'DB File is checked in!!! ({logger.get_database()})')

    def perforce_checkout_check(func):
        """
        Decorator used on a script's plot function to allow for a perforce checkout if a plot is attempting to be rewritten.
        
        Args:
            func    - The plot function created in the plugin.
        Returns:
            The plots generated by the script.
        """
        def wrapper(self, database, table_name, plot_filepath, skip_output=False):
            try:
                plts = func(self, database, table_name, plot_filepath, skip_output)                     ### Houston, we have a problem with those that fell behind.
                return plts
            except PermissionError as e:
                if table_name is not None and database is not None:
                    #re-plot. Files might be checked in.
                    if not self.auto_checkout and not self.already_asked:
                        self.auto_checkout = input(f'{e.filename} is not writeable. Attempt p4 checkout of this and all files that follow? [y/n]: ').lower() in ['y', 'yes']
                        self.already_asked=True
                    if not self.auto_checkout:
                        do_it = input(f'{e.filename} is not writeable. Attempt p4 checkout of just this file? [y/n]: ').lower() in ['y', 'yes']
                    if self.auto_checkout or do_it:
                        if self.p4_edit(e.filename):
                            plts = self.plot(database, table_name, plot_filepath, skip_output)
                            return plts
                        else:
                            raise
                    else:
                        raise
                else:
                    raise
        return wrapper
    @perforce_checkout_check
    def plot(self, database=None, table_name=None, plot_filepath=None, skip_output=False):
        """
        This plot replaces the script's plot method. It has a decorator that will allow a user to perforce checkout a file (plot) being modified instead of crashing immediately.
        """
        try:
            plts = self.regular_plot(database, table_name, plot_filepath, skip_output)
        except TypeError as e:
            print(f'WARNING: Test {self.get_name()} plot method does not support skip_output argument.')
            plts = self.regular_plot(database, table_name, plot_filepath)
        return plts

    
    def get_fstat(self, local_file):
        """
        Returns perforce infomation of a given file.
        
        Args:
            local_file - String or binary. Name of the local file to be read.
        Returns:
            Dictionary of fstat fields and values.
        """
        # TODO: Consider switching to Helix Python API? https://www.perforce.com/downloads/helix-core-api-python
        p4proc = subprocess.run(["p4", "fstat", local_file], capture_output=True)
        fstat_fields = {'depotFile': None,
                        'clientFile': None,
                        'headAction': None,
                        'headChange': None,
                        'headRev': None,
                        'haveRev': None,
                        'action': None,
                        'diff': None,
                        'swarmLink': None,
                        }
        if p4proc.returncode:
            pass
            # print(f"Perforce fstat for {local_file} returned: {p4proc.returncode}!")                      ## CHECK WITH DAVE! RHM 4/20/2023
        elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - no such file(s).':
            pass #not versioned!
        elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - file(s) not in client view.':
            pass #not versioned!
        elif p4proc.stderr != b'':
            print(f"Perforce fstat sent: {p4proc.stderr.decode(sys.stdout.encoding)} to stderr!")
            #Match stowe_eval.html - no such file(s)?
        else:
            for match in fstat_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
                if match.group('f_name') in fstat_fields:
                    fstat_fields[match.group('f_name')] = match.group('f_val')
            if fstat_fields['action'] == 'edit':
                diffproc = subprocess.run(['p4', 'diff', local_file], capture_output=True, check=True)
                fstat_fields['diff'] = diffproc.stdout.decode(sys.stdout.encoding)
            if fstat_fields['depotFile'] is not None:
                swarm_prefix = 'https://swarm.adsdesign.analog.com/files/'
                swarm_fpath = fstat_fields['depotFile'][2:] #remove '//'
                swarm_revision = f"?v={fstat_fields['haveRev']}" if fstat_fields['haveRev'] is not None else ''
                fstat_fields['swarmLink'] = f'{swarm_prefix}{swarm_fpath}{swarm_revision}'
        return fstat_fields

    def p4_edit(self,filename):
        """
        Checks out a file from perforce for editting.
        
        Args:
            filename - String. The name of the local file to be checked out.
        Returns:
            Boolean. True if checkout was successful, else False.
        """
        p4proc = subprocess.run(["p4", "-ztag", "edit", filename], capture_output=True)
        edit_fields = results_dict({'depotFile':  None,
                                    'clientFile': None,
                                    'workRev':    None,
                                    'action':     None,
                                    'type':       None,
                                    })
        if p4proc.returncode:
            print(f"Perforce client returned: {p4proc.returncode}!")
        else:
            for match in client_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
                if match.group('f_name') in edit_fields:
                    edit_fields[match.group('f_name')] = match.group('f_val')
        if edit_fields['action'] == 'edit':
            return True
        else:
            print(f'Checkout of {filename} failed.')
            print(edit_fields)
            return False

    def get_client_info(self):
        """
        Returns a dictionary containing information on the current perforce workspace.
        
        Returns:
            A dictionary containing information on the current perforce workspace.
        """
        p4proc = subprocess.run(["p4", "-ztag", "client", "-o"], capture_output=True)
        client_fields = results_dict({'Client':      None,
                                      'Owner':       None,
                                      'Description': None,
                                      'Root':        None,
                                      'Options':     None,
                                    })
        if p4proc.returncode:
            print(f"Perforce client returned: {p4proc.returncode}!")
        else:
            for match in client_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
                if match.group('f_name') in client_fields:
                    client_fields[match.group('f_name')] = match.group('f_val')
        return client_fields

    def get_describe(self,change_number):
        """
        Returns a dictionary containing information regarding a particualr change in perforce.
        
        Args:
            change_number   - Int. The perforce ID number of the submission in question.
        Returns:
            A dictionary with info pertaining to a submission in perforce. E.g. user, client, and time.
        """
        # TODO: Consider switching to Helix Python API? https://www.perforce.com/downloads/helix-core-api-python
        p4proc = subprocess.run(["p4", "-ztag", "describe", f"{change_number}"], capture_output=True)
        describe_fields = {'change':     None,
                        'user':       None,
                        'client':     None,
                        'time':       None,
                        'desc':       None,
                        'status':     None,
                        'changeType': None,
                        'path':       None,
                        'depotFile0': None,
                        'action0':    None,
                        'type0':      None,
                        'rev0':       None,
                        'fileSize0':  None,
                        'digest0':    None,
                       }
    # ... change 1656161
    # ... user dsimmons
    # ... client stowe_eval--dsimmons--DSIMMONS-L01
    # ... time 1613009815
    # ... desc mistake with TST_TEMP datatype. According to official spec, this should be a character string. COnverted back to number layer by Python/SQLite.

    # ... status submitted
    # ... changeType public
    # ... path //adi/stowe/evaluation/TRUNK/modules/*
    # ... depotFile0 //adi/stowe/evaluation/TRUNK/modules/stdf_utils.py
    # ... action0 edit
    # ... type0 text
    # ... rev0 14
    # ... fileSize0 33359
    # ... digest0 15AD23C1FD1BF6F4FE5669838FD94449

        if p4proc.returncode:
            print(f"Perforce describe returned: {p4proc.returncode}!")
        # elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - no such file(s).':
            # pass #not versioned!
        # elif p4proc.stderr.decode(sys.stdout.encoding).strip() == f'{local_file} - file(s) not in client view.':
            # pass #not versioned!
        elif p4proc.stderr != b'':
            print(f"Perforce describe sent: {p4proc.stderr.decode(sys.stdout.encoding)} to stderr!")
            #Match stowe_eval.html - no such file(s)?
        else:
            for match in fstat_pat.finditer(p4proc.stdout.decode(sys.stdout.encoding)):
                if match.group('f_name') in describe_fields:
                    describe_fields[match.group('f_name')] = match.group('f_val')
        return describe_fields