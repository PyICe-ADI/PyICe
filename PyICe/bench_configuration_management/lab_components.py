from PyICe.bench_configuration_management.bench_configuration_management import bench_config_component

class thru_terminator(bench_config_component):
    def add_terminals(self):
        self.add_terminal("M", instrument=self)
        self.add_terminal("F", instrument=self)

class four_channel_oscilloscope(bench_config_component):
    def add_terminals(self):
        self.add_terminal("CH1", instrument=self)
        self.add_terminal("CH2", instrument=self)
        self.add_terminal("CH3", instrument=self)
        self.add_terminal("CH4", instrument=self)
        
class AGILENT_3034x(four_channel_oscilloscope):
    '''AKO Two Channel Pulse Generator'''
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = four_channel_oscilloscope
        self.add_terminal("EXT_TRIG_IN", instrument=self)
        self.add_terminal("TRIG_OUT", instrument=self)

class voltage_probe(bench_config_component):
    def add_terminals(self):
        self.add_terminal("BNC", instrument=self)
        self.add_terminal("TIP", instrument=self)

class current_probe(bench_config_component):
    def add_terminals(self):
        self.add_terminal("SIGNAL", instrument=self)
        self.add_terminal("LOOP", instrument=self)

class two_channel_pulse_generator(bench_config_component):
    def add_terminals(self):
        self.add_terminal("CH1", instrument=self)
        self.add_terminal("CH2", instrument=self)
        
class SDG1032X(two_channel_pulse_generator):
    '''AKO Two Channel Pulse Generator'''
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = two_channel_pulse_generator
        self.add_terminal("AUX_IN_OUT", instrument=self)

class single_channel_electronic_load(bench_config_component):
    def add_terminals(self):
        self.add_terminal("IIN", instrument=self)
    
class HTX9000(single_channel_electronic_load):
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load
        
class HTX9000_5AMP(single_channel_electronic_load):
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load
        
class BK8500(single_channel_electronic_load):
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load

class one_channel_power_supply(bench_config_component):
    def add_terminals(self):
        self.add_terminal("VOUT1", instrument=self)

class four_channel_power_supply(bench_config_component):
    def add_terminals(self):
        self.add_terminal("VOUT1", instrument=self)
        self.add_terminal("VOUT2", instrument=self)
        self.add_terminal("VOUT3", instrument=self)
        self.add_terminal("VOUT4", instrument=self)
        
class HAMEG_HMP4040(four_channel_power_supply):
    def add_terminals(self):
        self.add_terminal("FRONTPANEL1", instrument=self)
        self.add_terminal("FRONTPANEL2", instrument=self)
        self.add_terminal("FRONTPANEL3", instrument=self)
        self.add_terminal("FRONTPANEL4", instrument=self)

class ConfiguratorXT(bench_config_component):
    def add_terminals(self):
        self.add_terminal("POWER1", instrument=self)
        self.add_terminal("POWER2", instrument=self)
        self.add_terminal("POWER3", instrument=self)
        self.add_terminal("POWER4", instrument=self)
        self.add_terminal("POWER5", instrument=self)
        self.add_terminal("POWER6", instrument=self)
        self.add_terminal("POWER7", instrument=self)
        self.add_terminal("POWER8", instrument=self)
        self.add_terminal("POWER1_MEAS", instrument=self)
        self.add_terminal("POWER2_MEAS", instrument=self)
        self.add_terminal("POWER3_MEAS", instrument=self)
        self.add_terminal("POWER4_MEAS", instrument=self)
        self.add_terminal("POWER5_MEAS", instrument=self)
        self.add_terminal("POWER6_MEAS", instrument=self)
        self.add_terminal("POWER7_MEAS", instrument=self)
        self.add_terminal("POWER8_MEAS", instrument=self)
        self.add_terminal("MEAS_A", instrument=self)
        self.add_terminal("MEAS_B", instrument=self)
        self.add_terminal("MEAS_C", instrument=self)
        self.add_terminal("MEAS_D", instrument=self)
        self.add_terminal("MEAS_E", instrument=self)
        self.add_terminal("FORCE_A1", instrument=self)
        self.add_terminal("FORCE_A2", instrument=self)
        self.add_terminal("FORCE_A3", instrument=self)
        self.add_terminal("FORCE_A4", instrument=self)
        self.add_terminal("FORCE_B1", instrument=self)
        self.add_terminal("FORCE_B2", instrument=self)
        self.add_terminal("FORCE_B3", instrument=self)
        self.add_terminal("FORCE_B4", instrument=self)
        self.add_terminal("FORCE_C1", instrument=self)
        self.add_terminal("FORCE_C2", instrument=self)
        self.add_terminal("FORCE_C3", instrument=self)
        self.add_terminal("FORCE_C4", instrument=self)
        self.add_terminal("FORCE_D1", instrument=self)
        self.add_terminal("FORCE_D2", instrument=self)
        self.add_terminal("FORCE_D3", instrument=self)
        self.add_terminal("FORCE_D4", instrument=self)
        self.add_terminal("FORCE_E1", instrument=self)
        self.add_terminal("FORCE_E2", instrument=self)
        self.add_terminal("FORCE_E3", instrument=self)
        self.add_terminal("FORCE_E4", instrument=self)
        self.add_terminal("FORCE_F1", instrument=self)
        self.add_terminal("FORCE_F2", instrument=self)
        self.add_terminal("FORCE_F3", instrument=self)
        self.add_terminal("FORCE_F4", instrument=self)
        self.add_terminal("DZ", instrument=self)
        self.add_terminal("PCIEX", instrument=self)
        self.add_terminal("UEXT", instrument=self)

class Rampinator(bench_config_component):
    def add_terminals(self):
        self.add_terminal("INPUT", instrument=self)
        self.add_terminal("OUTPUT", instrument=self)
        self.add_terminal("GATE_IN", instrument=self)
        self.add_terminal("VOUT_SENSE_UFL", instrument=self)
        self.add_terminal("VOUT_SENSE_SMA", instrument=self)

class Agilent_3497x(bench_config_component):
    def add_terminals(self):
        self.add_terminal("BAY1", instrument=self)
        self.add_terminal("BAY2", instrument=self)
        self.add_terminal("BAY3", instrument=self)

class Agilent_34901A(bench_config_component):
    '''20 Channel Differential Plugin'''
    def add_terminals(self):
        self.add_terminal("BAY", instrument=self)
        self.add_terminal("DIFF_1-4", instrument=self)
        self.add_terminal("DIFF_5-8", instrument=self)
        self.add_terminal("DIFF_9-12", instrument=self)
        self.add_terminal("DIFF_13-16", instrument=self)
        self.add_terminal("DIFF_17-20", instrument=self)

class Agilent_34908A(bench_config_component):
    '''40 Channel Single Ended Plugin'''
    def add_terminals(self):
        self.add_terminal("BAY", instrument=self)
        self.add_terminal("SINGLE_1-8", instrument=self)
        self.add_terminal("SINGLE_9-16", instrument=self)
        self.add_terminal("SINGLE_17-24", instrument=self)
        self.add_terminal("SINGLE_25-32", instrument=self)
        self.add_terminal("SINGLE_33-40", instrument=self)
        self.add_terminal("DZ", instrument=self)

class Agilent_U2300_DAQ(bench_config_component):
    '''40 Channel Differential Plugin'''
    def add_terminals(self):
        self.add_terminal("CONNECTOR1", instrument=self)
        self.add_terminal("CONNECTOR2", instrument=self)

class Agilent_U2300_TO_CAT5(bench_config_component):
    def add_terminals(self):
        self.add_terminal("VHDCI", instrument=self)
        self.add_terminal("CAT5A", instrument=self)
        self.add_terminal("CAT5B", instrument=self)
        self.add_terminal("SENSE(-)", instrument=self)
        self.add_terminal("GND", instrument=self)

class Y_Connector(bench_config_component):
    def add_terminals(self):
        self.add_terminal("A", instrument=self) # All terminals interchangable
        self.add_terminal("B", instrument=self) # All terminals interchangable
        self.add_terminal("C", instrument=self) # All terminals interchangable
        
class ConfigXT_Power_Breakout(bench_config_component):
    def add_terminals(self):
        self.add_terminal("POWER_IN", instrument=self)
        self.add_terminal("POWER_OUT", instrument=self)
        self.add_terminal("SCOPE_BNC", instrument=self)
        self.add_terminal("R_INJ", instrument=self)
        self.add_terminal("C_INJ", instrument=self)
        
class HTX9016(bench_config_component):
    def add_terminals(self):
        self.add_terminal("RFIN1", instrument=self)
        self.add_terminal("RFIN2", instrument=self)
        self.add_terminal("RFIN3", instrument=self)
        self.add_terminal("RFIN4", instrument=self)
        self.add_terminal("RFIN5", instrument=self)
        self.add_terminal("RFOUT", instrument=self)
    
class HTX9016_DC(HTX9016):
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = HTX9016

class E4446A_PSA(bench_config_component):
    def add_terminals(self):
        self.add_terminal("RFIN", instrument=self)
        
class E5061B_ENA(bench_config_component):
    def add_terminals(self):
        self.add_terminal("T", instrument=self)
        self.add_terminal("R", instrument=self)
        self.add_terminal("LFOUT", instrument=self)
        self.add_terminal("PORT1", instrument=self)
        self.add_terminal("PORT2", instrument=self)
        
class PICOTEST_J2111B(bench_config_component):
    def add_terminals(self):
        self.add_terminal("MOD", instrument=self)
        self.add_terminal("OUT", instrument=self)
        self.add_terminal("I_MONITOR", instrument=self)
        
class HTX9015_DC_BLOCKER(bench_config_component):
    def add_terminals(self):
        self.add_terminal("SMA_M", instrument=self)
        self.add_terminal("SMA_F", instrument=self)
