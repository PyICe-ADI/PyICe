"""Tests for scpi inst."""
from PyICe import lab_core
from PyICe.lab_instruments.a3497x_instruments import agilent_3497xa_chassis
from PyICe.lab_utils.ticker import ticker

m = lab_core.master()
a34972 = agilent_3497xa_chassis(
    m.get_visa_tcp_ip_interface(
        '192.168.0.10', port=5025, timeout=5))
print(a34972.get_errors())
a34972.beep()
print(a34972.identify())


t = ticker()
t.tick(display_function=a34972.display_text)
