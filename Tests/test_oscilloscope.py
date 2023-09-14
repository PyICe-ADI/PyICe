
import PyICe.lab_core as lab_core
# from PyICe.lab_instruments import oscilloscope
from PyICe.lab_instruments import agilent_3034a



m = lab_core.master()

oscope_if = m.get_visa_interface('USB0::0x2A8D::0x1764::MY58493119::0::INSTR', timeout=90) #sales DSOX3034T
scope = agilent_3034a(oscope_if, reset=True)
for i in range(1,5):
    scope.add_Ychannel(name=f'scope_ch{i}', number=i)
scope.add_Xchannels(prefix="scope")
m.add(scope)
scope.trigger_force()
print(m.read('scope_ch1'))
m.gui()