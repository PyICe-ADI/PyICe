from PyICe.labcomm import packet, SMBUS_module_id
demoboard_connection = ("serial", "COM8")  # Use serial port
# demoboard_connection = ("tcp", 4510)  # Use TCP socket with port number
baudrate = 115200

def try_out_dc2709a_4021(comport, src_id, xml_file, debug=False):
    from PyICe import lab_core, twi_instrument, lab_instruments
    m = lab_core.master()
    twi = m.get_twi_labcomm_raw_serial(serial_port_name=comport, src_id=src_id)
    ltc4021 = twi_instrument.twi_instrument(interface_twi = twi,
                                            except_on_i2cInitError = True,
                                            except_on_i2cCommError = False,
                                            retry_count = 2,
                                            PEC = True)
    ltc4021.populate_from_file(xml_file, access_list = ['user', 'rtl', 'test_hook'], use_case = "bench")
    m.add(ltc4021)
    # if self.make_ARA_channel:
        # ARAch = self.master.add_channel_virtual("ARA", read_function = self.twi.alert_response)
        # ARAch.set_category("Alerts")
    vtimer = lab_instruments.timer()
    vtimer.add_channel_delta_seconds("delta_secs")
    m.add(vtimer)
    while not debug or 'q' not in input("Press ENTER to launch PyICe GUI or 'q' then ENTER to exit. ").lower():
        m.gui()
        print("Type 'c' then ENTER to launch the PyICe GUI again, or enter any Python debugger command.")
        import pdb; pdb.set_trace()
    return m

#
# Main
#
if demoboard_connection[0] == "serial":
    print("I will connect to a DC2709A on serial port {}...".format(demoboard_connection[1]))
    input("Press ENTER to continue. ")
    from ltc4021.Register_Definitions import XMLFILE
    # xml_file="../../ltc4021/Register_Definitions/LTC4021.xml"
    master = try_out_dc2709a_4021(comport=demoboard_connection[1], src_id=0xabcd, xml_file=XMLFILE)
