#!/usr/bin/env python

from PyICe import lab_instruments, lab_core, twi_instrument

master = lab_core.master()
twi_interface = master.get_twi_dummy_interface(verbose=True)
twii = twi_instrument.twi_instrument(twi_interface)
master.add(twii)

twii.populate_from_file(xml_file = '../xml_registers/EXAMPLE/smart_battery_charger.xml',
                        access_list = ['user'],
                        use_case = "Smart Battery Charger"
                        )

# twii.populate_from_file(xml_file = '../xml_registers/EXAMPLE/smart_battery_battery.xml',
                        # access_list = ['user'],
                        # use_case = "Smart Battery Battery"
                        # )

twii.add_register(name="test_send_byte",addr7=0x09,command_code=0x99,size=8,offset=0,word_size=0,is_readable=False,is_writable=True)
twii.add_register(name="test_receive_byte",addr7=0x09,command_code=None,size=8,offset=0,word_size=0,is_readable=True,is_writable=False)
                        
master.add_channel_delta_timer('read_time')
master.add_channel_counter('read_count')

master["BATTERY_PRESENT"].add_change_callback()
master["POWER_FAIL"].add_change_callback()

master.gui()

