"""Lab components plugin.

>>> from PyICe.plugins.bench_configuration_management.lab_components import thru_terminator

"""
from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component


class thru_terminator(bench_config_component):
    """Thru_terminator (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import thru_terminator
    >>> thru_terminator is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import thru_terminator
        >>> hasattr(thru_terminator, 'add_terminals')
        True

        """
        self.add_terminal("M", instrument=self)
        self.add_terminal("F", instrument=self)


class four_channel_oscilloscope(bench_config_component):
    """Four_channel_oscilloscope (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import four_channel_oscilloscope
    >>> four_channel_oscilloscope is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import four_channel_oscilloscope
        >>> hasattr(four_channel_oscilloscope, 'add_terminals')
        True

        """
        self.add_terminal("CH1", instrument=self)
        self.add_terminal("CH2", instrument=self)
        self.add_terminal("CH3", instrument=self)
        self.add_terminal("CH4", instrument=self)


class AGILENT_3034x(four_channel_oscilloscope):
    """AKO Two Channel Pulse Generator.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import AGILENT_3034x
    >>> AGILENT_3034x is not None
    True

    """

    def __init__(self, name):
        """Initialize a g i l e n t_3034x.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import AGILENT_3034x
        >>> AGILENT_3034x is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = four_channel_oscilloscope
        self.add_terminal("EXT_TRIG_IN", instrument=self)
        self.add_terminal("TRIG_OUT", instrument=self)


class voltage_probe(bench_config_component):
    """Voltage_probe (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import voltage_probe
    >>> voltage_probe is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import voltage_probe
        >>> hasattr(voltage_probe, 'add_terminals')
        True

        """
        self.add_terminal("BNC", instrument=self)
        self.add_terminal("TIP", instrument=self)


class current_probe(bench_config_component):
    """Current_probe (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import current_probe
    >>> current_probe is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import current_probe
        >>> hasattr(current_probe, 'add_terminals')
        True

        """
        self.add_terminal("SIGNAL", instrument=self)
        self.add_terminal("LOOP", instrument=self)


class two_channel_pulse_generator(bench_config_component):
    """Two_channel_pulse_generator (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import two_channel_pulse_generator
    >>> two_channel_pulse_generator is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import two_channel_pulse_generator
        >>> hasattr(two_channel_pulse_generator, 'add_terminals')
        True

        """
        self.add_terminal("CH1", instrument=self)
        self.add_terminal("CH2", instrument=self)


class SDG1032X(two_channel_pulse_generator):
    """AKO Two Channel Pulse Generator.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import SDG1032X
    >>> SDG1032X is not None
    True

    """

    def __init__(self, name):
        """Initialize s d g1032 x.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import SDG1032X
        >>> SDG1032X is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = two_channel_pulse_generator
        self.add_terminal("AUX_IN_OUT", instrument=self)


class single_channel_electronic_load(bench_config_component):
    """Single_channel_electronic_load (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import single_channel_electronic_load
    >>> single_channel_electronic_load is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Appends a new terminals entry to the object's internal collection.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import single_channel_electronic_load
        >>> hasattr(single_channel_electronic_load, 'add_terminals')
        True

        """
        self.add_terminal("IIN", instrument=self)


class HTX9000(single_channel_electronic_load):
    """H t x9000 (single_channel_electronic_load subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9000
    >>> HTX9000 is not None
    True

    """
    def __init__(self, name):
        """Initialize h t x9000.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9000
        >>> HTX9000 is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load


class HTX9000_5AMP(single_channel_electronic_load):
    """H t x9000_5 a m p (single_channel_electronic_load subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9000_5AMP
    >>> HTX9000_5AMP is not None
    True

    """
    def __init__(self, name):
        """Initialize h t x9000_5 a m p.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9000_5AMP
        >>> HTX9000_5AMP is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load


class BK8500(single_channel_electronic_load):
    """B k8500 (single_channel_electronic_load subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import BK8500
    >>> BK8500 is not None
    True

    """
    def __init__(self, name):
        """Initialize b k8500.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import BK8500
        >>> BK8500 is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = single_channel_electronic_load


class one_channel_power_supply(bench_config_component):
    """One_channel_power_supply (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import one_channel_power_supply
    >>> one_channel_power_supply is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Appends a new terminals entry to the object's internal collection.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import one_channel_power_supply
        >>> hasattr(one_channel_power_supply, 'add_terminals')
        True

        """
        self.add_terminal("VOUT1", instrument=self)


class two_channel_power_supply(bench_config_component):
    """Two_channel_power_supply (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import two_channel_power_supply
    >>> two_channel_power_supply is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import two_channel_power_supply
        >>> hasattr(two_channel_power_supply, 'add_terminals')
        True

        """
        self.add_terminal("CHANNELA", instrument=self)
        self.add_terminal("CHANNELB", instrument=self)


class four_channel_power_supply(bench_config_component):
    """Four_channel_power_supply (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import four_channel_power_supply
    >>> four_channel_power_supply is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import four_channel_power_supply
        >>> hasattr(four_channel_power_supply, 'add_terminals')
        True

        """
        self.add_terminal("VOUT1", instrument=self)
        self.add_terminal("VOUT2", instrument=self)
        self.add_terminal("VOUT3", instrument=self)
        self.add_terminal("VOUT4", instrument=self)


class HAMEG_HMP4040(four_channel_power_supply):
    """H a m e g_ h m p4040 (four_channel_power_supply subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HAMEG_HMP4040
    >>> HAMEG_HMP4040 is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import HAMEG_HMP4040
        >>> hasattr(HAMEG_HMP4040, 'add_terminals')
        True

        """
        self.add_terminal("FRONTPANEL1", instrument=self)
        self.add_terminal("FRONTPANEL2", instrument=self)
        self.add_terminal("FRONTPANEL3", instrument=self)
        self.add_terminal("FRONTPANEL4", instrument=self)


class ConfiguratorXT(bench_config_component):
    """Configurator x t (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import ConfiguratorXT
    >>> ConfiguratorXT is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import ConfiguratorXT
        >>> hasattr(ConfiguratorXT, 'add_terminals')
        True

        """
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


class Uext_Accelerator(bench_config_component):
    """Uext_ accelerator (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Uext_Accelerator
    >>> Uext_Accelerator is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Appends a new terminals entry to the object's internal collection.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Uext_Accelerator
        >>> hasattr(Uext_Accelerator, 'add_terminals')
        True

        """
        self.add_terminal("UEXT", instrument=self)


class Rampinator(bench_config_component):
    """Rampinator (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Rampinator
    >>> Rampinator is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Rampinator
        >>> hasattr(Rampinator, 'add_terminals')
        True

        """
        self.add_terminal("INPUT", instrument=self)
        self.add_terminal("OUTPUT", instrument=self)
        self.add_terminal("GATE_IN", instrument=self)
        self.add_terminal("VOUT_SENSE_UFL", instrument=self)
        self.add_terminal("VOUT_SENSE_SMA", instrument=self)


class Agilent_3497x(bench_config_component):
    """Agilent_3497x (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_3497x
    >>> Agilent_3497x is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_3497x
        >>> hasattr(Agilent_3497x, 'add_terminals')
        True

        """
        self.add_terminal("BAY1", instrument=self)
        self.add_terminal("BAY2", instrument=self)
        self.add_terminal("BAY3", instrument=self)


class Agilent_34901A(bench_config_component):
    """20 Channel Differential Plugin.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_34901A
    >>> Agilent_34901A is not None
    True

    """

    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_34901A
        >>> hasattr(Agilent_34901A, 'add_terminals')
        True

        """
        self.add_terminal("BAY", instrument=self)
        self.add_terminal("DIFF_1-4", instrument=self)
        self.add_terminal("DIFF_5-8", instrument=self)
        self.add_terminal("DIFF_9-12", instrument=self)
        self.add_terminal("DIFF_13-16", instrument=self)
        self.add_terminal("DIFF_17-20", instrument=self)


class Agilent_34908A(bench_config_component):
    """40 Channel Single Ended Plugin.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_34908A
    >>> Agilent_34908A is not None
    True

    """

    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_34908A
        >>> hasattr(Agilent_34908A, 'add_terminals')
        True

        """
        self.add_terminal("BAY", instrument=self)
        self.add_terminal("SINGLE_1-8", instrument=self)
        self.add_terminal("SINGLE_9-16", instrument=self)
        self.add_terminal("SINGLE_17-24", instrument=self)
        self.add_terminal("SINGLE_25-32", instrument=self)
        self.add_terminal("SINGLE_33-40", instrument=self)
        self.add_terminal("DZ", instrument=self)


class Agilent_U2300_DAQ(bench_config_component):
    """40 Channel Differential Plugin.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_U2300_DAQ
    >>> Agilent_U2300_DAQ is not None
    True

    """

    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_U2300_DAQ
        >>> hasattr(Agilent_U2300_DAQ, 'add_terminals')
        True

        """
        self.add_terminal("CONNECTOR1", instrument=self)
        self.add_terminal("CONNECTOR2", instrument=self)


class Agilent_U2300_TO_CAT5(bench_config_component):
    """Agilent_ u2300_ t o_ c a t5 (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_U2300_TO_CAT5
    >>> Agilent_U2300_TO_CAT5 is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Agilent_U2300_TO_CAT5
        >>> hasattr(Agilent_U2300_TO_CAT5, 'add_terminals')
        True

        """
        self.add_terminal("VHDCI", instrument=self)
        self.add_terminal("CAT5A", instrument=self)
        self.add_terminal("CAT5B", instrument=self)
        self.add_terminal("SENSE(-)", instrument=self)
        self.add_terminal("GND", instrument=self)


class Y_Connector(bench_config_component):
    """Y_ connector (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import Y_Connector
    >>> Y_Connector is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import Y_Connector
        >>> hasattr(Y_Connector, 'add_terminals')
        True

        """
        self.add_terminal("A", instrument=self)  # All terminals interchangable
        self.add_terminal("B", instrument=self)  # All terminals interchangable
        self.add_terminal("C", instrument=self)  # All terminals interchangable


class ConfigXT_Power_Breakout(bench_config_component):
    """Config x t_ power_ breakout (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import ConfigXT_Power_Breakout
    >>> ConfigXT_Power_Breakout is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import ConfigXT_Power_Breakout
        >>> hasattr(ConfigXT_Power_Breakout, 'add_terminals')
        True

        """
        self.add_terminal("POWER_IN", instrument=self)
        self.add_terminal("POWER_OUT", instrument=self)
        self.add_terminal("SCOPE_BNC", instrument=self)
        self.add_terminal("R_INJ", instrument=self)
        self.add_terminal("C_INJ", instrument=self)


class HTX9016(bench_config_component):
    """H t x9016 (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9016
    >>> HTX9016 is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9016
        >>> hasattr(HTX9016, 'add_terminals')
        True

        """
        self.add_terminal("RFIN1", instrument=self)
        self.add_terminal("RFIN2", instrument=self)
        self.add_terminal("RFIN3", instrument=self)
        self.add_terminal("RFIN4", instrument=self)
        self.add_terminal("RFIN5", instrument=self)
        self.add_terminal("RFOUT", instrument=self)


class HTX9016_DC(HTX9016):
    """H t x9016_ d c.

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9016_DC
    >>> HTX9016_DC is not None
    True

    """
    def __init__(self, name):
        """Initialize h t x9016_ d c.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9016_DC
        >>> HTX9016_DC is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = HTX9016


class E4446A_PSA(bench_config_component):
    """E4446 a_ p s a (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import E4446A_PSA
    >>> E4446A_PSA is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Appends a new terminals entry to the object's internal collection.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import E4446A_PSA
        >>> hasattr(E4446A_PSA, 'add_terminals')
        True

        """
        self.add_terminal("RFIN", instrument=self)


class E5061B_ENA(bench_config_component):
    """E5061 b_ e n a (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import E5061B_ENA
    >>> E5061B_ENA is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import E5061B_ENA
        >>> hasattr(E5061B_ENA, 'add_terminals')
        True

        """
        self.add_terminal("T", instrument=self)
        self.add_terminal("R", instrument=self)
        self.add_terminal("LFOUT", instrument=self)
        self.add_terminal("PORT1", instrument=self)
        self.add_terminal("PORT2", instrument=self)


class HP8110A(bench_config_component):
    """H p8110 a (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HP8110A
    >>> HP8110A is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import HP8110A
        >>> hasattr(HP8110A, 'add_terminals')
        True

        """
        self.add_terminal("OUTPUT1", instrument=self)
        self.add_terminal("OUTPUT2", instrument=self)
        self.add_terminal("STROBE_OUT", instrument=self)
        self.add_terminal("EXT_INPUT", instrument=self)
        self.add_terminal("TRIGGER_OUT", instrument=self)


class PICOTEST_J2111B(bench_config_component):
    """P i c o t e s t_ j2111 b (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import PICOTEST_J2111B
    >>> PICOTEST_J2111B is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import PICOTEST_J2111B
        >>> hasattr(PICOTEST_J2111B, 'add_terminals')
        True

        """
        self.add_terminal("MOD", instrument=self)
        self.add_terminal("OUT", instrument=self)
        self.add_terminal("I_MONITOR", instrument=self)


class HTX9015_DC_BLOCKER(bench_config_component):
    """H t x9015_ d c_ b l o c k e r (bench_config_component subclass).

    >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9015_DC_BLOCKER
    >>> HTX9015_DC_BLOCKER is not None
    True

    """
    def add_terminals(self):
        """Add a terminals.

        Creates and registers a new terminals.

        >>> from PyICe.plugins.bench_configuration_management.lab_components import HTX9015_DC_BLOCKER
        >>> hasattr(HTX9015_DC_BLOCKER, 'add_terminals')
        True

        """
        self.add_terminal("SMA_M", instrument=self)
        self.add_terminal("SMA_F", instrument=self)
