from PyICe import lab_core, lab_instruments, lab_utils

m = lab_core.master()
a34972 = lab_instruments.agilent_3497xa_chassis(m.get_visa_tcp_ip_interface('192.168.0.10', port = 5025, timeout = 5))
print(a34972.get_errors())
a34972.beep()
print(a34972.identify())


ticker = lab_utils.ticker()
ticker.tick(display_function = a34972.display_text)