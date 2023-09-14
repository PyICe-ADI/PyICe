baudrate = 115200
import os
# import logging                           # No need to do this anymore because
# logging.basicConfig(level=logging.ERROR) # PyICe.lab_core creates the root logging object.

# Global Flag for PyICe native application
PYICE_NATIVE = True


def talk_to_demoboard(connection, src_id, xml_file, debug=False):
    from PyICe import lab_core, twi_instrument, lab_instruments
    m = lab_core.master()
    m._threaded = False   # Useful when debugging.
    if connection[0] == 'serial':
        twi = m.get_twi_labcomm_raw_serial(serial_port_name=connection[1],
                                           src_id=src_id)
    elif connection[0] == 'tcp':
        twi = m.get_twi_labcomm_tcp(dest_ip_address=connection[1][0],
                                    dest_tcp_portnum=connection[1][1],
                                    src_id=src_id,
                                    debug=False)
    elif connection[0] == 'dummy':
        twi = m.get_twi_dummy_interface()

    chip = twi_instrument.twi_instrument(interface_twi=twi,
                                         except_on_i2cInitError=True,
                                         except_on_i2cCommError=False,
                                         retry_count=2,
                                         PEC=True)

    chip.populate_from_file(xml_file, access_list = ['user_i2c_mode', 'rtl', 'test_hook'], use_case = "bench")
#    chip.populate_from_file(xml_file, access_list=['user_i2c_mode'], use_case=None)

    m.add(chip)
    # if self.make_ARA_channel:
        # ARAch = self.master.add_channel_virtual("ARA", read_function = self.twi.alert_response)
        # ARAch.set_category("Alerts")
    vtimer = lab_instruments.timer()
    vtimer.add_channel_delta_seconds("delta_secs")
    m.add(vtimer)
    m['battery_detection_alert'].add_change_callback()
    while not debug or 'q' not in input("Press ENTER to launch PyICe GUI or 'q' then ENTER to exit. ").lower():
        if PYICE_NATIVE is True:
            m.gui()
        else:
            from LTC4162_GUI import ltc4162_gui  # this cannot be imported in the main thread
            gui = ltc4162_gui.ltc_lab_gui_app_client(m,
                                                    passive=False,
                                                    cfg_file='default.guicfg')
            gui.exec_()
        print("Type 'c' then ENTER to launch the PyICe GUI again, or enter any Python debugger command.")
        import pdb; pdb.set_trace()
    return m


#
# Main
#
from serial.tools.list_ports import comports
def test_labcomm():
    """
    Main Test code for labcomm initialization
    :return:
    """
    
    while True:
        comport_list = comports()
        if not len(comport_list):
            print("No serial ports found. I can't see your demoboard.")
            print("Try unplugging and replugging its USB connection.")
            input("Press ENTER to continue. ")
        else:
            break  # Found at least one serial port.
    # Find all serial ports that are USB devices, meaning they have a VID and PID.
    # Only include the ones with LTC's VID=0x1272 and PID=0x8005.
    LTC_usbserialports = [port for port in comport_list if port.vid is not None and int(port.vid) == 0x1272 and int(port.pid) == 0x8005]

    print("Talks to a DC2038A demoboard via Labcomm")
    print()
    print("NOTE: Please be sure to connect the demoboard directly to a USB port on the computer, not through a hub.")
    print()
    connection_type = "serial"  # TODO: add connection type "tcp".

    #connection_type = "dummy"  # TODO: add connection type "tcp".

    if len(LTC_usbserialports) < 1:
        print ("I don't see any DC2038A's connected, or anything matching "
               "VID:PID 0x1272:0x8005 (legacy Linear Tech. demoboards) for that matter")
        input("Press ENTER to exit. ")
        raise SystemExit
    elif len(LTC_usbserialports) == 1:
        # Only found 1 potential demoboard.
        demoboard_port = LTC_usbserialports[0].device
        print(("My scan found one Analog Devices (legacy LTC) demoboard board. "
               "It is on {}.").format(demoboard_port))
    else:
        print("The following serial ports appear to have demoboards connected to them:")
        for port in LTC_usbserialports:
            print(" {:>12s} : vid:pid=0x{:04x}:0x{:04x}".format(port.device, int(port.pid), int(port.vid)))
        demoboard_port = input("Which of these should I use? (e.g. {}) ".format(port.device))
    if isinstance(demoboard_port, str):
        demoboard_port = demoboard_port.encode()

    # Activate while debugging
    the_xml_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LTC4162-BASE-local-copy.xml")
    # Activate while build
    #the_xml_file = "./LTC4162-BASE-local-copy.xml"
    # Dummy without board
    #the_xml_file = "C:/WORK/A_SVN/LTC4162/trunk/Registers/LTC4162-LAD/synthetics/public/XML/LTC4162-LAD.xml"

    print()
    s = input("Press ENTER to accept default XML file {}, or enter the path\n"
                  "/using/forward/slashes/to/the/file.xml: ".format(the_xml_file))
    the_xml_file = s if s else the_xml_file
    import random
    src_id = random.randint(1024, 2**16 - 1)  # Low numbers are reserved.
    print("Choosing random Labcomm Source ID = 0x{:04x}".format(src_id))
    master = talk_to_demoboard((connection_type, demoboard_port), src_id=src_id, xml_file=the_xml_file)

if __name__ == '__main__':
#    from serial.tools.list_ports import comports
    test_labcomm()
