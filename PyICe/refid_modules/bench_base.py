import abc
import atexit
import inspect
import os
from PyICe import lab_core, lab_utils

class bench_base(abc.ABC):
    def __init__(self, **kwargs):
        atexit.register(self.cleanup)
        self._notification_functions    = []
        self._cleanup_registry          = []
        self._master                    = lab_core.master()
        self._kwargs                    = kwargs
        self._master.add_channel_dummy('comment')
        self._master.add_channel_dummy('device_num')
        self.init(self._master)
        if 'tdegc' not in self._master.get_all_channel_names():
            def dummy_oven_write(value):
                if value is not None:
                    msg = "*** ERROR: Wrote dummy oven temperature.\nThis channel only exists to facilitate plotting before moving a test to the oven.\nTemperatures are meaningless, and you risk corrupting your databse with improperly collected data!\nSet 'temperatures=None' next time.***"
                    self.notify(msg)
                    raise Exception(msg)
            self._master.add_channel_virtual('tdegc', write_function=dummy_oven_write)
            self._master['tdegc'].set_description("Dummy Oven. Don't write to anything other than 'None'.")
        if 'tdegc_sense' not in self._master.get_all_channel_names():
            self._master.add_channel_dummy('tdegc_sense')
            self._master['tdegc_sense'].write(None) #Doesn't pretend to read temperatures. Just to facilitate plotting.
            self._master['tdegc_sense'].set_description('''Dummy Oven Temp Readback. Will only ever read 'None'. Suggest SQL query like: """SELECT ifnull(tdegc_sense, 27) AS tdegc_sense, foo FROM {table_name}"""''')
            self._master['tdegc_sense'].set_write_access(False)
        self.add_traceability_channels()
        self._master.write_html(file_name='project.html', verbose=True, sort_categories=True)   # Don't like the general name "project"
        #####################################################
        # HACK HACK HACK HACK HACK HACK HACK HACK HACK HACK #
        #####################################################
        # PyICe has developed some kind of threading problem
        # which crashes 34970 with HTX9011 imeas channels.
        # This will slow everything down until resolved!!!
        self.get_master().set_allow_threading(False)
        #####################################################
    @abc.abstractmethod
    def init(master, virtual_oven):
        ''''make this gun work'''
    def add_traceability_channels(self):
        ch_cat = 'eval_traceability'
        self._master.add_channel_dummy('bench').write(str(inspect.getmodule(type(self))))
        self._master['bench'].set_category(ch_cat)
        self._master['bench'].set_write_access(False)
        self._master.add_channel_dummy('bench_operator').write(os.getlogin())
        self._master['bench_operator'].set_category(ch_cat)
        self._master['bench_operator'].set_write_access(False)
        # module_file = inspect.getsourcefile(type(self))                   ### Part of p4_traceability_plugin now.
        # fileinfo = p4_traceability.get_fstat(module_file)
        # for property in fileinfo:
            # self._master.add_channel_dummy(f'bench_{property}').write(fileinfo[property])
            # self._master[f'bench_{property}'].set_category(ch_cat)
            # self._master[f'bench_{property}'].set_write_access(False)
        # if fileinfo['depotFile'] is None:
            # print("********* WARNING *********")
            # print("* Lab bench unversioned.  *")
            # print(f"* {self._master['bench'].read()}")
            # print("***************************")
            # resp = input('Press "y" to continue: ')
            # if resp.lower() != 'y':
                # raise Exception('Unversioned bench module.')
        # elif fileinfo['action'] is not None:
            # print("************* WARNING *************")
            # print("* Lab bench uncommitted changes.  *")
            # print(f"* {self._master['bench'].read()}")
            # print("***********************************")
            # resp = input('Press "y" to continue: ')
            # if resp.lower() != 'y':
                # raise Exception('Uncommitted bench module working copy.')
        def get_ch_group_info(ch_group, ident_level=0):
            ret_str = ''
            tabs = '\t' * ident_level
            try:
                idn = ch_group.identify()
            except AttributeError:
                idn = "No Information Available."
            ret_str = f'{tabs}{ch_group.get_name()}:  {idn}\n'
            for ch_subgrp in ch_group.get_channel_groups():
                ret_str += get_ch_group_info(ch_subgrp, ident_level+1)
            return ret_str
        self._master.add_channel_dummy('bench_instruments').write(get_ch_group_info(self._master))
        self._master['bench_instruments'].set_category(ch_cat)
        self._master['bench_instruments'].set_write_access(False)
    def get_master(self):
        return self._master
    def add_notification(self, fn):
        self._notification_functions.append(fn)
    def add_cleanup(self, fn):
        self._cleanup_registry.append(fn)
    def notify(self, msg, subject=None, attachment_filenames=[], attachment_MIMEParts=[]):
        if not len(attachment_filenames) and not len(attachment_MIMEParts):
            #Just a plain message
            print(msg)
        for fn in self._notification_functions:
            try:
                fn(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
            except TypeError:
                # Function probably doesn't accept subject or attachments
                try:
                    fn(msg)
                except Exception as e:
                    # Don't let a notiffication crash a more-important cleanup/shutdown.
                    print(e)
            except Exception as e:
                # Don't let a notiffication crash a more-important cleanup/shutdown.
                print(e)
    def cleanup_oven(self):
        try:
            if self._master.read('tdegc_enable'):
                self._master.write('tdegc_soak', 1)
                # self._master.write('tdegc', 25) # Autonics has non-volatile memory
                self._master.write('tdegc_enable', False)
            else:
                # Oven wasn't used or is already cleaned up
                pass
        except lab_core.ChannelAccessException as e:
            # Expected. Channel just might not exist.
            pass
        except IOError as e:
            print('Oven off???', e)
            pass
        except Exception as e:
            # What happened?
            print("Something unexpected happened in oven cleanup. Please Contact PyICe Support at PyICe-developers@analog.com.")
            breakpoint()
            raise e
        else:
            # Oven successfully disabled. Now for powerdown...
            pass
        finally:
            try:
                # Might not have these channels defined??
                self._master.write('tdegc_power_relay', False)
            except lab_core.ChannelAccessException as e:
                # Expected. Channel just might not exist.
                pass
            except Exception as e:
                print(f'Oven cleanup {type(e)}')
    # @atexit.register
    def cleanup(self):
        for cleanup in self._cleanup_registry:
            cleanup()
    def close_ports(self):
        m = self.get_master()
        delegator_list = [ch.resolve_delegator() for ch in self.get_master()]
        delegator_list = list(set(delegator_list))
        interfaces = []
        for delegator in delegator_list:
            for interface in delegator.get_interfaces():
                interfaces.append(interface)
        interfaces = list(set(interfaces))
        for iface in interfaces:
            try:
                iface.close()
            except AttributeError as e:
                pass
            except Exception as e:
                print(e)
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        # TODO atexit.register?
        # https://docs.python.org/3/library/atexit.html
        self.cleanup()
        self.cleanup_oven()
        self.close_ports()
        lab_utils.print_banner('All cleaned up, Outa Here!')
        return False
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
