from ..lab_core import *
from .. import visa_wrappers
from .semiconductor_parameter_analyzer import semiconductor_parameter_analyzer
import time

class hp_4155b(semiconductor_parameter_analyzer):
    '''Hewlett Packard Semiconductor Parameter Analyzer speaking HP4145 Command Set
    Set System->MISCELLANEOUS->COMMAND SET = HP4145
    Set System->MISCELLANEOUS->DELIMITER = COMMA
    Set System->MISCELLANEOUS->EOI = ON'''
    def __init__(self,interface_visa):
        '''interface_visa"'''
        self._base_name = 'hewlett_packard_4155B-scs'
        scpi_instrument.__init__(self,f"hewlett_packard_4155B-scs @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._smu_voltage_force_channels = {1:1,2:2,3:3,4:4,5:7,6:8}
        self._smu_voltage_measure_channels = {1:1,2:2,3:3,4:4,5:7,6:8} #PGU1:9,PGU2:10 pulse generator not supported
        self._smu_current_measure_channels = {1:1,2:2,3:3,4:4,5:7,6:8}
        self._vm_voltage_measure_channels = {1:5,2:6}
        self._smu_voltage_range = {20:1,40:2,100:3,200:4,2:-1} #'AUTO':0
        self._smu_current_range = {1e-9:1,10e-9:2,100e-9:3,1e-6:4,10e-6:5,100e-6:6,1e-3:7,10e-3:8,100e-3:9,1:10,10e-12:-2,100e-12:-1} #'AUTO':0
        self._voltage_measure_channels = {'A':'SMU1','B':'SMU2','C':'SMU3','D':'SMU4','E':'VM1','F':'VM2','G':'SMU5','H':'SMU6'}
        self._current_measure_channels = {'A':'SMU1','B':'SMU2','C':'SMU3','D':'SMU4','G':'SMU5','H':'SMU6'}
        self._smu_configuration = {}
        self.smu_numbers = list(range(1,7))
        self.vs_numbers = list(range(1,3))
        #print 'Changing HP4145 Command Set (wait 5 seconds).'
        #self.get_interface().write(('*RST'))
        #time.sleep(3) #wait for restart
        #self.get_interface().write((':SYSTem:LANGuage COMPatibility')) #switch to 4145 command set
        #time.sleep(10) #wait for restart
        #print self.get_interface().ask('CMD?')
        #if int(self.get_interface().ask('CMD?')) != 2: #0=SCPI,1=FLEX,2=4145.  We want 2=4145
        #    raise Exception('Error: HP4155 must be set to HP4145 Command Set in System:Misc menu')
        # try:
            # self.get_interface().ask('*IDN?') #instrument only responds to this query in SCPI command mode
            # raise Exception('Error: HP4155 must be set to HP4145 Command Set in System:Misc menu')
        # except visa_wrappers.visaWrapperException as e:
            # self.get_interface().clear() #normal to not respond; rl1009 locks up with no response
        # except Exception as e:
            # print "Expect timeout error here..."
            # print e #normal to not respond; HP82357 doesn't seem to lock up with no response
            # #self.get_interface().clear()

        self._set_user_mode()
    def add_channels_smu_voltage(self, smu_number, voltage_force_channel_name, current_compliance_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channels_smu_voltage(smu_number, voltage_force_channel_name, current_compliance_channel_name)
    def add_channel_smu_voltage_output_range(self,smu_number,output_range_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channel_smu_voltage_output_range(smu_number,output_range_channel_name)
    def add_channels_smu_current(self,smu_number,current_force_channel_name,voltage_compliance_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channels_smu_current(smu_number,current_force_channel_name,voltage_compliance_channel_name)
    def add_channel_smu_current_output_range(self,smu_number,output_range_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channel_smu_current_output_range(smu_number,output_range_channel_name)
    def add_channel_smu_voltage_sense(self,smu_number,voltage_sense_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channel_smu_voltage_sense(smu_number,voltage_sense_channel_name)
    def add_channel_smu_current_sense(self,smu_number,current_sense_channel_name):
        assert 1 <= smu_number <= 6
        return self._add_channel_smu_current_sense(smu_number,current_sense_channel_name)
    def add_channel_vsource(self,vsource_number,vsource_channel_name):
        assert 1 <= vsource_number <= 2
        return self._add_channel_vsource(vsource_number,vsource_channel_name)
    def add_channel_vmeter(self,vmeter_number,vmeter_channel_name):
        assert 1 <= vmeter_number <= 2
        return self._add_channel_vmeter(vmeter_number,vmeter_channel_name)
