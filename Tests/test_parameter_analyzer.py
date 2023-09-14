import sys
sys.path.append('../..')
import PyICe.lab_core as lab_core
import PyICe.lab_instruments as lab_instruments
import time


if __name__ == '__main__':
    m = lab_core.master()
    
    #kiface = m.get_visa_keithley_kxci_interface('10.163.10.74',1225)
    #bar = lab_instruments.keithley_4200(kiface)
    #bar.configure_slot_vm(5,1)
    #bar.configure_slot_smu(1,1)
    
    #m.set_gpib_adapter_rl1009(0,"COM26")
    m.set_gpib_adapter_rl1009(0)
    hiface = m.get_visa_gpib_interface(gpib_adapter_number=0,gpib_address_number=17)
    bar = lab_instruments.hp_4155b(hiface)
    
    bar.add_channels_smu_voltage(1,'voltage','current_compliance')
    bar.add_channel_smu_voltage_sense(1,'readback_voltage')
    bar.add_channel_smu_current_sense(1,'readback_current')
    bar.add_channel_smu_voltage_output_range(1,'range')
    #  bar.add_channel_smu_current_output_range(1,'irange')
    bar.add_channel_integration_time('tm')
    bar.add_channel_vsource(1,'v')
    bar.add_channel_vmeter(1,'m')
    m.add(bar)
    def counter():
        if counter.count is None:
            counter.start_time = time.time()
            counter.count = 1
        else:
            counter.count += 1
        return counter.count
    counter.count = None

    def timer():
        if timer.start is None:
            timer.start = time.time()
        return time.time()-timer.start
    timer.start = None
    def cycle_timer():
        return timer()/counter.count
    
    m.add_channel_virtual('count',read_function=counter)
    m.add_channel_virtual('time',read_function=timer)
    m.add_channel_virtual('cycle_time',read_function=cycle_timer)
    m.gui()