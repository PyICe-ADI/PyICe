from . import virtual_instruments
from . import lab_core
from . import twi_instrument
import PyICe
master = lab_core.master("Demonstration GUI")
master.add_channel_delta_timer('time_d')
timer = virtual_instruments.timer()
timer.add_channel_total_seconds('seconds')
timer.add_channel_total_minutes('minutes')
master.add(timer)

twii = master.get_twi_dummy_interface()
twi = PyICe.twi_instrument.twi_instrument(twii)
json_path = "../../morpheus_eval/infrastructure/yoda/output/pyice"
twi.populate_from_yoda_json_bridge(filename=f"{json_path}/morpheus_pyice.json",i2c_addr7=0x69,extended_addressing=False)
twi.populate_from_yoda_json_bridge(filename=f"{json_path}/morpheus_pyice_fuse.json",i2c_addr7=0x69,extended_addressing=False)
twi.populate_from_yoda_json_bridge(filename=f"{json_path}/morpheus_pyice_tm.json",i2c_addr7=0x69,extended_addressing=False)
master.add(twi)

import cProfile
PROFILING = False
profiler = None
if PROFILING:
    profiler = cProfile.Profile()
    profiler.enable()
master.gui()
if PROFILING:
    profiler.disable()
    profiler.dump_stats("lab_gui.profile")
    print("GUI performance logged in lab_gui.profile.")
