from PyICe.refid_modules import bench_identifier, test_archive
from PyICe import virtual_instruments
from PyICe.lab_utils.banners import print_banner
from PyICe.lab_utils.sqlite_data import sqlite_data
import abc
import collections
import datetime
import functools
import numbers
import os
import inspect
# os.environ['FOR_IGNORE_EXCEPTIONS'] = '1'
# os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'
import socket
import sqlite3
import subprocess
import urllib
import traceback
from email.mime.image import MIMEImage

try:
    import cairosvg
    cairo_ok = True
except Exception as e:
    print(e)
    traceback.print_exc()
    cairo_ok = False
#TODO rebuild sweep finding infrastructure?


#Intercept Fortran ctrl-c handling:
# https://stackoverflow.com/questions/15457786/ctrl-c-crashes-python-after-importing-scipy-stats
try:
    import win32api
    import _thread
    def sig_handler(dwCtrlType, hook_sigint=_thread.interrupt_main):
        if dwCtrlType == 0: # CTRL_C_EVENT
            print("Here I am")
            hook_sigint()
            return 1 # don't chain to the next handler
        return 0 # chain to the next handler
    win32api.SetConsoleCtrlHandler(sig_handler, 1)
except Exception as e:
    #os error on Linux?!?!
    print(type(e))
    print(e)
    traceback.print_exc()
    
def ctrlc(sig, frame):
    raise KeyboardInterrupt("CTRL-C!")
    
import signal
# # signal.signal(signal.SIGINT, signal.default_int_handler)
signal.signal(signal.SIGINT, ctrlc)

# import win32api
# def doSaneThing(sig, func=None):
    # print("Here I am")
    # raise KeyboardInterrupt
# win32api.SetConsoleCtrlHandler(doSaneThing, 1)





class temptroller():
    def __init__(self, temperatures=None, debug=False): # lab_bench=None, temperatures=[25]):
        self._tests = []
        self._debug = debug
        self.plug_instances=[]
        if hasattr(self, 'plugins'):            ## Hokay. Slight issue here. If there's a regression going on, how do we make each test_module get a personal instance of a plugin?.
            self.interplugs={}
            for plugin in self.plugins:
                plug = plugin(temptroller=self)
                self.plug_instances.append(plug)
        if temperatures is None:
            temperatures = (None,)
        else:
            temperatures = tuple(temperatures)
            assert None not in temperatures
            for temp in temperatures:
                assert isinstance(temp, numbers.Number)
                assert temp >= -60
                assert temp <= 171 #What's safe?
        assert len(temperatures)
        self._temperatures = temperatures
        self._plots = []
        # self.set_lab_bench_constructor(self._get_bench_instruments())
        # self.set_lab_bench_constructor(self._get_bench_instruments())
        self._lab_bench_constructor = None
    def get_bench_identity(self): 
        '''just used to differentiate notifications. Not necessarily related to acutal bench in use if overridden.'''
        thismachine = socket.gethostname()
        thisuser = thisbench = os.getlogin()
        return {'host': thismachine,
                'user': thisuser,
               }
    def notify(self, msg, subject=None, attachment_filenames=[], attachment_MIMEParts=[]):
        if not self._debug:
            try:
                self._lab_bench.notify(msg, subject=subject, attachment_filenames=attachment_filenames, attachment_MIMEParts=attachment_MIMEParts)
            except AttributeError as e:
                if not len(attachment_filenames) and not len(attachment_MIMEParts):
                    print(msg)
        else:
            if not len(attachment_filenames) and not len(attachment_MIMEParts):
                print(msg)
    def set_lab_bench_constructor(self, lab_bench_constructor):
        '''override automatic bench lookup mechanism for special equipment setup.
        Usually not necessary
        constructure should be executable with no arguments and return an object with (minimally) channel master and notification function attributes'''
        self._lab_bench_constructor = lab_bench_constructor

    def add_test(self, test_module, repeat_count=1):
        assert repeat_count > 0
        if repeat_count > 1:
            for c in range(repeat_count):
                iter_test = test_module(debug=self._debug)
                iter_test.tt=self
                iter_test.hook_functions('tm_set', iter_test)
                db_filename = f"repeatability_{c:03d}.sqlite" #TODO: common file, different tables?
                iter_test._db_file = os.path.join(iter_test._module_path, db_filename)
                self._tests.append(iter_test)
        else:
            solo_test = test_module(debug=self._debug)
            solo_test.tt=self
            solo_test.hook_functions('tm_set', solo_test)
            self._tests.append(solo_test)
        if self._lab_bench_constructor is None:
            self.set_lab_bench_constructor(bench_identifier.get_bench_instruments(test_module.project_folder_name))
    def __iter__(self):
        return iter(self._tests)
    def __len__(self):
        return len(self._tests)
    @abc.abstractmethod
    def _get_bench_instruments(self):
        '''Returns instruments used on the test bench'''
    def hook_functions(self, hook_key, *args):
        for test in self._tests:
            for plugin in test.plug_instances:
                for (k,v) in plugin.get_hooks().items():
                    if k is hook_key:
                        for f in v:
                            f(*args)
    def collect(self):
        oven_timer = virtual_instruments.timer()
        oven_timer.add_channel_total_minutes('oven_time_tot_min')
        oven_timer.add_channel_delta_minutes('oven_time_delta_min')
        troller_timer = virtual_instruments.timer()
        troller_timer.add_channel_total_minutes('temptroller_time_min')
        troller_timer.resume_timer()
        try:
            # self._lab_bench = self._lab_bench_constructor()()
            self._lab_bench = self._lab_bench_constructor()
            # self._lab_bench.master.background_gui() #TODO dumps core on VDI/Py38!
            if self._debug:
                #Make tests easier to debug by preventing crashes from happening in worker threads.
                self._lab_bench.get_master().set_allow_threading(False)
            self.hook_functions('begin_collect')
            summary_msg = '{user} on {host}\n'.format(**self.get_bench_identity())
            door_heater_exists = True if ('door_heater' in self._lab_bench.get_master().get_all_channel_names() and None not in self._temperatures) else False
            for test in self:
                test._setup(lab_bench=self._lab_bench)
                summary_msg += f'\t* {test.get_name()}*\n'
            for (temp_idx, temperature) in enumerate(self._temperatures):
                test_count = 0
                for test in self:
                    if test.temp_is_included(temperature):
                        test_count += 1
                if test_count == 0:
                    continue
                if temperature is not None:
                    if self._debug:
                        self._lab_bench.get_master()['tdegc_soak'].write(30)
                        print(f'#########WARNING!!!!!This test is running in debug mode. Soak time will be 30s#########')
                        if input('Continue? [y/n] ').lower() not in ['y', 'yes']:
                            raise Exception('Soak time is insufficient')  
                    summary_msg += f"\nSetting temperature to {temperature}°C\n"
                    self.notify(summary_msg, subject='Next Temperature')
                    summary_msg = '{user} on {host}\n'.format(**self.get_bench_identity())
                    while True:
                        try:
                            oven_timer.resume_timer()
                            if door_heater_exists:
                                self._lab_bench.get_master()['door_heater'].write('ON' if temperature <=20 else 'OFF')
                            self._lab_bench.get_master()['tdegc_enable'].write(True)
                            self._lab_bench.get_master()['tdegc'].write(temperature)
                            break
                        except Exception:
                            oven_timer.pause_timer()
                            self._lab_bench.get_master()['tdegc_enable'].write(False)
                            if door_heater_exists:
                                self._lab_bench.get_master()['door_heater'].write('OFF')
                            input(f'Oven failed to settle to {temperature}. Replace the tank and hit Enter to try again.')
                    oven_timer_data = oven_timer.read_all_channels()
                    oven_timer.pause_timer()
                    summary_msg += f'*** {temperature}°C Summary ***\n'
                    summary_msg += f'\t* Oven slew and settle took {oven_timer_data["oven_time_delta_min"]:3.1f} minutes. *\n'
                    cumulative_tests_time = oven_timer_data["oven_time_tot_min"]
                    loop_time = oven_timer_data["oven_time_delta_min"]
                else:
                    cumulative_tests_time = 0 #no oven; no previous temperatures or tests
                    loop_time=0
                test_time_remaining=0
                script_time={}
                # def delete_soon_to_be_rewritten_data(test,temp):
                    # table_name = test.get_db_table_name()
                    # db_file = test._db_file
                    # db = sqlite_data(database_file=db_file, table_name=table_name)
                    # cur=db.conn.cursor()
                    # cur.execute(f'DELETE FROM {table_name} WHERE tdegc is {temp}')
                    # cur.close()
                    # db.conn.commit()
                    # test._crashed=None
                for (test_idx, test) in enumerate(self):
                    if (not test.in_range(temperature)) or (temperature in test.excluded_temperatures):
                        temp_message=f"Skipping {test.get_name()}. " + (f"Temp out of range." if (not test.in_range(temperature)) else f"Excluded temp.")
                        print_banner(temp_message)
                        summary_msg += f'\t* {test.get_name()} skipped due to temperature. 0 minutes at {temperature}°C"'
                        try:
                            summary_msg += f', {script_time[test]:3.1f} minutes total. *\n'
                            test_time_remaining+=len([x for x in self._temperatures[temp_idx+1:] if test.is_included(x)]) * script_time[test]
                        except:
                            summary_msg += f'.\n'
                        continue
                    test.test_timer.resume_timer()
                    timer_data = test.test_timer.read_all_channels()
                    if not test.is_crashed():
                        while True:
                            if door_heater_exists:
                                self._lab_bench.get_master()['door_heater'].write('ON' if temperature <=20 else 'OFF')
                            test._collect()
                            if test.is_crashed():
                                self.notify(test.crash_info(), subject='CRASHED!!!') #First crash
                            if temperature is not None and abs(self._lab_bench.get_master()['tdegc_sense'].read()-temperature)>5:                  # Implies the tank ran out of gas.
                                self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+f'While running {test.get_name()}, the oven failed to maintain its set temperature of {temperature}C. Pausing the regression.', subject='Temperature Walked!')
                                self._lab_bench.get_master()['tdegc_enable'].write(False)
                                if door_heater_exists:
                                    self._lab_bench.get_master()['door_heater'].write('OFF')
                                once_more= input('Oven failed to maintain its temperature. Try again? [y/[n]]: ').lower()
                                if once_more == 'y':
                                    input(f'Replace the tank then hit Enter to try again.')
                                    # delete_soon_to_be_rewritten_data
                                    table_name = test.get_db_table_name()
                                    db_file = test._db_file
                                    db = sqlite_data(database_file=db_file, table_name=table_name)
                                    cur = db.conn.cursor()
                                    cur.execute(f'DELETE FROM {table_name} WHERE tdegc is {temperature}')
                                    cur.close()
                                    db.conn.commit()
                                    test._crashed=None
                                    self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+f'Rerunning {test.get_name()} at {temperature}C, and resuming the regression.', subject='Regression Resumed')
                                    if door_heater_exists:
                                        self._lab_bench.get_master()['door_heater'].write('ON' if temperature <=20 else 'OFF')
                                    self._lab_bench.get_master()['tdegc_enable'].write(True)
                                    self._lab_bench.get_master()['tdegc'].write(temperature)
                                else:
                                    break
                            else:
                                break
                    timer_data = test.test_timer.read_all_channels()
                    test.test_timer.pause_timer()
                    cumulative_tests_time += timer_data["test_time_min"]
                    if test.is_crashed():
                        summary_msg += f'\t* {test.get_name()} crashed/skipped. {timer_data["loop_time_min"]:3.1f} minutes at {temperature}°C, {timer_data["test_time_min"]:3.1f} minutes total. *\n'
                    else:
                        summary_msg += f'\t* {test.get_name()} completed. {timer_data["loop_time_min"]:3.1f} minutes at {temperature}°C, {timer_data["test_time_min"]:3.1f} minutes total. *\n'
                        loop_time+=timer_data["loop_time_min"]
                        script_time[test]=timer_data["loop_time_min"]
                        test_time_remaining+=sum(map(lambda x: test.temp_is_included(x),self._temperatures[temp_idx+1:])) * timer_data["loop_time_min"]
                frac_complete = 1.*(temp_idx+1)/len(self._temperatures)
                frac_incomplete = 1-frac_complete
                # etr = datetime.timedelta(minutes=cumulative_tests_time * frac_incomplete / frac_complete)
                etr = datetime.timedelta(minutes=test_time_remaining + 10*len(self._temperatures[temp_idx+1:]))
                summary_msg += f'{temp_idx+1} of {len(self._temperatures)} temperatures complete in {cumulative_tests_time:.1f} minutes.\n'
                if temp_idx+1 < len(self._temperatures):
                    summary_msg += f'ETR: {etr.total_seconds()/60.:.0f} minutes.\n'
                    summary_msg += f'ETC: {(datetime.datetime.now()+etr).strftime("%a %b %d %H:%M")}.\n'
            troller_time_data = troller_timer.read_all_channels()
            troller_timer.pause_timer()
            finish_msg = summary_msg
            finish_msg += f'\n*** All tests completed. Total time: {troller_time_data["temptroller_time_min"]:3.1f} minutes. ***\n'
            if temperature is not None:
                finish_msg += f'\t* Oven slewing and settling took {oven_timer_data["oven_time_tot_min"]:3.1f} minutes total. (Average {oven_timer_data["oven_time_tot_min"]/len(self._temperatures):3.1f} minutes per temperature.) *\n'
            for test in self:
                test._teardown()
                test._add_db_indices(table_name=None, db_file=None)
                if test.is_crashed():
                    finish_msg += f'\t* {test.crash_info()} *\n'
                else:
                    timer_data = test.test_timer.read_all_channels()
                    finish_msg += f'\t* Test {test.get_name()} completed. {timer_data["test_time_min"]:3.1f} minutes total. *\n'
        except Exception as e:
            # Oven crash, for example
            try:
                self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+str(e), subject='Temptroller crash!')
            except:
                pass
            raise e
        else:
            self.notify(finish_msg, subject='Collection Complete')          # Finish_msg might not be defined in the event of a crash.
        finally:
            try:
                self._lab_bench.cleanup()
            except AttributeError as e:
                # Didn't get far enough to create a _lab_bench before crashing.
                pass
            except Exception as e:
                # Don't let bench problem prevent oven cleanup
                try:
                    self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+str(e), subject='Bench cleanup crash!')
                except:
                    pass
                print(e) #remove?
            try:
                self._lab_bench.cleanup_oven()
            except AttributeError as e:
                # Didn't get far enough to create a _lab_bench before crashing.
                pass
            except Exception as e:
                # Don't let bench problem prevent port close
                try:
                    self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+str(e), subject='Oven cleanup crash!')
                except:
                    pass
                print(e) #remove?
            try:
                self._lab_bench.close_ports()
            except AttributeError as e:
                # Didn't get far enough to create a _lab_bench before crashing.
                pass
            except Exception as e:
                # Not sure if this should crash now or not, or how it might happen
                try:
                    self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+str(e), subject='Port cleanup crash!')
                except:
                    pass
                traceback.print_exc()
                # raise e
    def plot(self):
        for test in self:
            plts = test._plot()
            self._plots.extend(plts)
            if test._plot_crashed is not None:
                (typ, value, trace_bk) = test._plot_crashed
                notify_message = f'{test.get_name()} plot crash! Moving on.\n'
                notify_message += f'{"".join(traceback.format_exception(typ, value, trace_bk))}\n'
                self.notify(f'{self.get_bench_identity()["user"]} on {self.get_bench_identity()["host"]}\n'+notify_message)
        if len(self._plots): #Don't send empty emails
            self.email_plots(self._plots)
        return self._plots
    def email_plots(self, plot_svg_source):
        msg_body = ''
        attachment_MIMEParts=[]
        for (i,plot_src) in enumerate(plot_svg_source):
            if cairo_ok:
                plot_png = cairosvg.svg2png(bytestring=plot_src)
                plot_mime = MIMEImage(plot_png, 'image/png')
                plot_mime.add_header('Content-Disposition', 'inline')
                plot_mime.add_header('Content-ID', f'<plot_{i}>')
                msg_body += f'<img src="cid:plot_{i}"/>'
            else:
                plot_mime = MIMEImage(plot_src, 'image/svg+xml')
                plot_mime.add_header('Content-Disposition', 'attachment', filename=f'G{i:03d}.svg')
                plot_mime.add_header('Content-ID', f'<plot_{i}>')
            attachment_MIMEParts.append(plot_mime)
        self.notify(msg_body, subject='Plot Results', attachment_MIMEParts=attachment_MIMEParts)

    def _archive(self, interactive=True):
        # This method depends on some state collected by successfully completing the collect() method.
        if functools.reduce(lambda a,b: a or b, [True if test._archive_table_name is not None else False for test in self]):
            if interactive:
                archive = input('Manage collected data? [[y]/n]: ').lower() not in ["n", "no"]
            else:
                archive = True
            if archive:
                self.folder_suggestion = datetime.datetime.utcnow().strftime("%Y_%m_%d_%H_%M")
                self.hook_functions('begin_archive')
                for test in self:
                    if test._archive_table_name is None:
                        continue
                    if test._plot_crashed is not None:
                        # Going to solicit input no matter what the interactive setting is. There's not obviously right answer when things have gone this unexpectedly wrong.
                        print(test._plot_crashed)
                        while True:
                            arch_resp = input('Archive data with crashed plotting? [y/[n]]: ').lower()
                            if len(arch_resp):
                                break
                        if arch_resp not in  ['y', 'yes']:
                            continue
                    try:
                        tdegc_conn = sqlite3.connect(test._db_file, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
                        tdegc_conn.row_factory = sqlite3.Row #index row data tuple by column name
                        row = tdegc_conn.execute(f"SELECT tdegc FROM {test._archive_table_name}").fetchone()
                        assert row is not None #Empty table!
                        if row['tdegc'] is None:
                            self.folder_suggestion = f'{self.folder_suggestion}__AMBIENT'
                        else:
                            self.folder_suggestion = f'{self.folder_suggestion}__TEMPERATURE'
                        break
                    except sqlite3.OperationalError as e:
                        print(f'tdegc information not available from {test.get_name()} results database.')
                        continue
                    except Exception as e:
                        print(test.get_name())
                        print(type(e))
                        print(e)
                        traceback.print_exc()
                        print('This is unexpected. Please contact PyICe Support at PyICe-developers@analog.com with this stack trace.')
                        # For whatever reason, this data doesn't seem to be suitable for collecting traceability info. To be revisited later.
                        continue
                if interactive:
                    archive_folder = test_archive.database_archive.ask_archive_folder(suggestion=self.folder_suggestion)
                else:
                    archive_folder = self.folder_suggestion
                archived_tables = []
                for test in self:
                    if test._archive_table_name is not None:
                        # Test completed
                        archiver = test_archive.database_archive(db_source_file=test._db_file)
                        db_dest_file = archiver.compute_db_destination(archive_folder)
                        if interactive:
                            resp = archiver.disposition_table(table_name=test._archive_table_name, db_dest_file=db_dest_file, db_indices=test._column_indices)
                            if resp is not None:
                                archived_tables.append((test, resp[0], resp[1])) #return ((db_dest_table, db_dest_file))
                                test._add_db_indices(table_name=resp[0], db_file=resp[1])
                        else:
                            archiver.copy_table(db_source_table=test._archive_table_name, db_dest_table=test._archive_table_name, db_dest_file=db_dest_file, db_indices=test._column_indices)
                            archived_tables.append((test, test._archive_table_name, db_dest_file))
                            test._add_db_indices(table_name=test._archive_table_name, db_file=db_dest_file)
                if len(archived_tables):
                    arch_plot_scripts = []
                    if interactive:
                        waps = input('Write archive plot script(s)? [[y]/n]: ').lower() not in ["n", "no"]
                    else:
                        waps = True
                    if waps:
                        for (test, db_table, db_file) in archived_tables:
                             arch_plot_script = test_archive.database_archive.write_plot_script(test_module=test.get_import_str(), test_class=test.get_name(), db_table=db_table, db_file=db_file)
                             arch_plot_scripts.append(arch_plot_script)
                    if len(arch_plot_scripts) and (not interactive or input('Generate archive plot(s)? [[y]/n]: ').lower() not in ['n', 'no']):
                        for (test, db_table, db_file) in archived_tables:
                            db = sqlite_data(database_file=db_file, table_name=db_table)
                            plot_filepath = os.path.join(os.path.dirname(db_file), db_table)
                            try:
                                test.plot(database=db, table_name=test._archive_table_name, plot_filepath=plot_filepath, skip_output=False)
                            except TypeError:
                                test.plot(database=db, table_name=test._archive_table_name, plot_filepath=plot_filepath)
                    if len(arch_plot_scripts) > 1 and (not interactive or input('Write summary plots script? [[y]/n]: ').lower() not in ['n', 'no']):
                        os.mkdir(self.folder_suggestion)
                        dest_abs_filepath = os.path.join(self.folder_suggestion,"replot_data.py")
                        summary_str = f"from PyICe.refid_modules.temptroller import replotter\n"
                        for (test, db_table, db_file) in archived_tables:
                            x=inspect.getfile(type(test))
                            x=x.replace("\\" , '.')
                            x=x.replace('.py',"")
                            x= x[x.find(test.project_folder_name):]
                            summary_str += f"from {x} import {test.get_name()}\n"
                        summary_str += f"\nif __name__ == '__main__':\n"
                        summary_str += f'\n    rplt = replotter()\n'
                        for (test, db_table, db_file) in archived_tables:
                            rel_db_file=os.path.relpath(db_file, start =test.project_folder_name)
                            rel_db_file=rel_db_file.replace('\\', '/')
                            summary_str += f'    rplt.add_test_run(test_class={test.get_name()},table_name=r"{db_table}",db_file="{rel_db_file}")\n'
                        summary_str += f'\n    rplt.write_html("summary_plots.html")'
                        try:
                            with open(dest_abs_filepath, 'w') as f: #overwrites existing
                                f.write(summary_str)
                                f.close()
                        except Exception as e:
                            print(type(e))
                            print(e)
                            traceback.print_exc()
                            breakpoint()
                            pass
                    if len(arch_plot_scripts) > 1 and (not interactive or input('Generate summary plots? [[y]/n]: ').lower() not in ['n', 'no']):
                        #Write out summary plot, or write out summary plot maker?!?! TODO!
                        html_plotter = replotter()
                        for (test, db_table, db_file) in archived_tables:
                            html_plotter.add_test_run(test_class=type(test), table_name=db_table, db_file=db_file)
                        try:
                            html_plotter.write_html('regression_summary.html')
                        except PermissionError as e:
                            if input(f'{e.filename} is not writeable. Attempt p4 checkout? [y/[n]]: ').lower() in ['y', 'yes']:
                                if p4_traceability.p4_edit(e.filename):
                                    html_plotter.write_html('regression_summary.html')
                                else:
                                    raise e
                            else:
                                raise e
    def manual_archive(self):
        archive_folder = test_archive.database_archive.ask_archive_folder()
        for test in self:
            archiver = test_archive.database_archive(db_source_file=test._db_file)
            copied_tables_files = archiver.copy_interactive(archive_folder=archive_folder, project_folder=test.project_folder_name)
            for (table, file) in copied_tables_files:
                test._add_db_indices(table_name=table, db_file=file)
    def run(self, collect_data, skip_plot=False, force_archive=False):
        if not len(self):
            raise Exception('ABORT: No tests added to test suite!')
        self.hook_functions('pre_collect')
        if collect_data:
            self.collect()
        self.hook_functions('post_collect')
        if not skip_plot: #an not skip_compile_test_results??? Is there an interdependence?
            self.plot() #Don't want to suppress test results with plot garbage, but might need test results stored data to produce plots!
        self.hook_functions('post_plot')
        self._archive(interactive=not force_archive)
        self.hook_functions('post_archive')
        
class replotter:
    def __init__(self):
        # self.test_run =  collections.namedtuple('test_run', ['test_class', 'table_name', 'db_file'])
        self.test_result =  collections.namedtuple('test_result', ['test_class', 'table_name', 'db_file', 'test_name', 'plots', 'results_array', 'corr_results_array', 'bench_setup_image', 'bench_setup_list', 'bench_instruments', 'refid'])
        # self._test_runs = []
        self._test_results = []
    def add_test_run(self, test_class, table_name, db_file, bench_setup_image=None, bench_setup_list= None, bench_instruments=None, refid=None, skip_plots=False):
        # self._test_runs.append(self.test_run(test_class=test_class, table_name=table_name, db_file=db_file))
        test_inst = test_class()
        if not hasattr(test_inst, '_test_result'):
            test_inst.register_refids()
        test_inst._test_results._set_traceability_info(**test_inst._get_traceability_info(table_name=table_name, db_file=db_file))
        test_inst._correlation_results._set_traceability_info(**test_inst._get_traceability_info(table_name=table_name, db_file=db_file))
        try:
            # breakpoint()            ## Delete the results_str and instead look into test_inst.test_results and look into [test][ch2_vout or whatever]. Ask in a pythonic way for the results.
            results_str = test_inst._test_from_table(table_name=table_name, db_file=db_file)
            results_array = test_inst._test_results
            corr_results_array = test_inst._correlation_results
        except Exception as e:
            # Don't kill whole replot over one broken test, missing column, etc. Log exception in results and move on...
            results_str = f'{e}'
        if not skip_plots:
            plots = test_inst._plot(table_name=table_name, db_file=db_file, skip_output=True) # TODO: try/except??
            if plots is None:
                plots = []
            else:
                assert isinstance(plots, list), "Plot method should return a list of plot objects. Contact PyICe Support at PyICe-developers@analog.com."
        else:
            plots = []
        # breakpoint()
        for tst_name in test_inst._test_results: #These are the keys / refid names now. TODO provide public getter methods to the test results modules.
            for tst_result in test_inst._test_results[tst_name]: #change 2021/12. Now a list of independently tracked results. 
                for tst_plt in tst_result.plot: #Today, there's just plots in the first result, because of a hack over in test_results module. That might change, but this should work either way.
                    plots.append(tst_plt)
        # self._test_results.append(self.test_result(test_class=test_class, table_name=table_name, db_file=db_file, test_name=test_inst.get_name(), plots=plots, results_str=results_str, bench_setup=bench_setup, bench_instruments=bench_instruments, refid=refid))
        self._test_results.append(self.test_result(test_class=test_class, table_name=table_name, db_file=db_file, test_name=test_inst.get_name(), plots=plots, results_array=results_array, corr_results_array=corr_results_array, bench_setup_image=bench_setup_image, bench_setup_list=bench_setup_list, bench_instruments=bench_instruments, refid=refid))
    # def plot(self, html_file=None):
        # assert len(self._test_runs), 'ABORT: No test runs added to replotter suite!'
    def write_html(self, html_file):
        with open(html_file, 'wb') as f:
            f.write(self._html().encode("UTF-8"))
            f.close()
    def _min(self, data):
        if not len(data):
            return None
        return min(data)
    def _max(self, data):
        if not len(data):
            return None
        return max(data)
    def _html(self):
        ret_str = ''
        ret_str += '<html>\n'
        ret_str += '<head>\n'
        ret_str += '<style>\n'
        ret_str += 'body {\n'
        ret_str += '  font-family: "Lucida Console", "Courier New", Courier, monospace;\n'
        ret_str += '}\n'
        ret_str += '</style>\n'
        ret_str += '<title>PyICe Test Result Replotter</title>\n'
        ret_str += '</head>\n'
        ret_str += '<body>\n'
        for test_result in self._test_results:
            ret_str += f'<h1>{test_result.test_name}</h1>\n'
            ret_str += f'<h3>{test_result.db_file} {test_result.table_name}</h3>\n'
            ret_str += f'<p>\n'
            for refid in test_result.results_array._test_results:
                ret_str += f'<h4>{refid}</h4>'
                ret_str += f'&nbsp;&nbsp;RESULTS<br/>'
                for data in test_result.results_array._test_results[refid]:
                    ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;{data.conditions}&nbsp;&nbsp;TRIALS:{len(data.collected_data)}&nbsp;&nbsp;VERDICT:'+(f'PASSES<br/>' if data.passes == True else f'FAILS<br/>')
                    this_min = self._min(data.collected_data)
                    if data.failure_reason != '':
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;FORCED_FAIL: {data.failure_reason}<br/>'
                    elif len(data) > 1:
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;MIN:{f"{this_min:g}" if type(this_min) is int else f"{this_min}" if this_min is not None else "None"}<br/>' if not data else ''
                        this_max = self._max(data.collected_data)
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;MAX:{f"{this_max:g}" if type(this_max) is int else f"{this_max}" if this_max is not None else "None"}<br/>' if not data else ''
                    else:
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;DATA:{f"{min:g}" if type(min) is int else f"{min}" if min is not None else "None"}<br/>' if not data else ''
                ret_str += f'***<br/>* {refid} ' + ('PASSES!<br/>' if all([x.passes for x in test_result.results_array._test_results[refid]]) else 'FAILS!<br/>') + '***<br/>'
            for refid in test_result.corr_results_array._correlation_results:
                ret_str += f'<h4>{refid}</h4>'
                ret_str += f'&nbsp;&nbsp;RESULTS<br/>'
                for data in test_result.corr_results_array._correlation_results[refid]:
                    ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;{data.conditions}&nbsp;&nbsp;ATE DATA:{data.ate_data}&nbsp;&nbsp;ERROR:{data.error}&nbsp;&nbsp;VERDICT:'+(f'PASSES<br/>' if data.passes == True else f'FAILS<br/>')
                    ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;{data.conditions}&nbsp;&nbsp;ATE DATA:{data.ate_data}&nbsp;&nbsp;ERROR:{data.error}&nbsp;&nbsp;VERDICT:'+(f'PASSES<br/>' if data.passes == True else f'FAILS<br/>')
                    if data.failure_reason != '':
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;FORCED_FAIL: {data.failure_reason}<br/>'
                    elif len(data) > 1:
                        this_min = self._min(data.bench_data)
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;ATE DATA:{data.ate_data}&nbsp;&nbsp;MIN:{f"{this_min:g}" if type(this_min) is int else f"{this_min}" if this_min is not None else "None"}<br/>' if not data.passes else ''
                        this_max = self._max(data.bench_data)
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;ATE DATA:{data.ate_data}&nbsp;&nbsp;MAX:{f"{this_max:g}" if type(this_max) is int else f"{this_max}" if this_max is not None else "None"}<br/>' if not data else ''
                    else:
                        ret_str += f'&nbsp;&nbsp;&nbsp;&nbsp;ATE DATA:{data.ate_data}&nbsp;&nbsp;BENCH DATA:{f"{this_min:g}" if type(this_min) is int else f"{this_min}" if this_min is not None else "None"}<br/>' if not data else ''
                ret_str += f'***<br/>* {refid} ' + ('PASSES!<br/>' if all([x.passes for x in test_result.corr_results_array._correlation_results[refid]]) else 'FAILS!<br/>') + '***<br/>'
            ret_str += f'</p>\n'
            for plt in test_result.plots:
                # https://css-tricks.com/lodge/svg/09-svg-data-uris/
                # https://css-tricks.com/using-svg/
                ret_str += f'<img src=data:image/svg+xml,{urllib.parse.quote(plt)} />\n'
            ret_str += '<hr/>\n'
        ret_str += '</body>\n'
        ret_str += '</html>\n'
        return ret_str

    def add_to_markdown(self, refid, indent_level=None):
        ret_str = ''
        for test_result in self._test_results:
            if test_result.refid[0] == refid:
                ret_str += f'<h2>File Location</h2>{test_result.db_file}  \n'
                ret_str += f'<h2>Table Name</h2>{test_result.table_name}'
                try:
                    ret_str += f'<h2>Bench Instruments</h2>{test_result.bench_instruments}'
                    ret_str += f'<h2>Bench Setup</h2>'
                    ret_str += f'{test_result.bench_setup_list}<br/>'
                    ret_str += f'&nbsp;&nbsp;<img src={os.path.abspath(test_result.bench_setup_image.filepath)}.svg />'
                except Exception as e:
                    print(e)
                    breakpoint()
                ret_str += f'<h2>RESULTS</h2>'
                for rslt in test_result.results_array[refid]:
                    ret_str += f'&nbsp;&nbsp;{rslt.conditions}&nbsp;&nbsp;&nbsp;&nbsp;VERDICT:' + ('PASSES<br/>' if rslt.passes else 'FAILS<br/>')
                ret_str += f'</pre>'
                ret_str += f'<h2>PLOTS</h2>'
                for index,plt in enumerate(test_result.plots,1):
                    # https://css-tricks.com/lodge/svg/09-svg-data-uris/
                    # https://css-tricks.com/using-svg/
                    ret_str += f'<img src=data:image/svg+xml,{urllib.parse.quote(plt)} />&nbsp;'
                ret_str += '<hr/>\n'
        ret_str += '</div>\n'
        return ret_str