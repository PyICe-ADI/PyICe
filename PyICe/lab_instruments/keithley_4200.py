"""Keithley 4200 instrument driver.

>>> from PyICe.lab_instruments.keithley_4200 import keithley_4200

"""
from ..lab_core import *  # noqa: F403
from .semiconductor_parameter_analyzer import semiconductor_parameter_analyzer


class keithley_4200(semiconductor_parameter_analyzer):
    """Keithley Model 4200-SCS Semiconductor Characterization System."""

    def __init__(self, interface_visa):
        """Interface_visa".
        Initializes 12 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 12 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'keithley_4200-scs'
        scpi_instrument.__init__(self, f"keithley_4200-scs @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write(("EM 1,0"))
        # reset smu mapping; Andrea Clary FAE email exchange
        self.get_interface().write(("DE;CH1;CH2;CH3;CH4;CH5;CH6"))
        self._set_user_mode()
        self._smu_voltage_force_channels = {
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8}
        self._smu_voltage_measure_channels = {
            1: 1, 2: 2, 3: 3, 4: 4, 5: 7, 6: 8, 7: 9, 8: 10}
        self._smu_current_measure_channels = {
            1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8}
        self._vm_voltage_measure_channels = {
            1: 5, 2: 6, 3: 11, 4: 12, 5: 13, 6: 14, 7: 15, 8: 16}
        self._smu_voltage_range = {20: 1, 200: 2}  # 'AUTO':0
        self._smu_current_range = {
            1e-9: 1,
            10e-9: 2,
            100e-9: 3,
            1e-6: 4,
            10e-6: 5,
            100e-6: 6,
            1e-3: 7,
            10e-3: 8,
            100e-3: 9,
            1: 10,
            10e-12: 11,
            100e-12: 12}  # 'AUTO':0
        self._voltage_measure_channels = {
            'A': 'SMU1',
            'B': 'SMU2',
            'C': 'SMU3',
            'D': 'SMU4',
            'E': 'VM1',
            'F': 'VM2',
            'G': 'SMU5',
            'H': 'SMU6',
            'I': 'SMU7',
            'J': 'SMU8',
            'K': 'VM3',
            'L': 'VM4',
            'M': 'VM5',
            'N': 'VM6',
            'O': 'VM7',
            'P': 'VM8'}
        self._current_measure_channels = {
            'A': 'SMU1',
            'B': 'SMU2',
            'C': 'SMU3',
            'D': 'SMU4',
            'E': 'SMU5',
            'F': 'SMU6',
            'G': 'SMU7',
            'H': 'SMU8'}
        self.smu_numbers = []
        self.vs_numbers = []
        self._smu_configuration = {}
        self.get_slot_configuration()
        # self._smu_voltage_compliance = 210 #+/-
        # self._smu_current_compliance = 0.105 #4200-SMU
        # self._smu_current_compliance = 1.05 #4210-SMU

    def get_slot_configuration(self):
        # only works in EM 1 (4200 extended command mode)
        """Return the slot configuration.
        Sends the ``:`` SCPI command to the instrument.
        Queries the instrument for its current slot configuration and returns
        the parsed response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self.slot_conf = self.get_interface().ask("*OPT?").strip('"').split(",")
        self.smu_numbers = []
        self.vs_numbers = []
        for slot in range(8):
            print(f"Slot {slot + 1}", end=' ')
            if self.slot_conf[slot].startswith('SMU'):
                # what about 10 having 2 digits???
                self.smu_numbers.append(int(self.slot_conf[slot][3]))
                print(
                    f'{self.slot_conf[slot]}: Medium Power SMU without preamp')
            elif self.slot_conf[slot].startswith('HPSMU'):
                self.smu_numbers.append(int(self.slot_conf[slot][5]))
                print(f'{self.slot_conf[slot]}: High Power SMU without preamp')
            elif self.slot_conf[slot].startswith('SMUPA'):
                self.smu_numbers.append(int(self.slot_conf[slot][5]))
                print(f'{self.slot_conf[slot]}: Medium Power SMU with preamp')
            elif self.slot_conf[slot].startswith('HPSMUPA'):
                self.smu_numbers.append(int(self.slot_conf[slot][7]))
                print(f'{self.slot_conf[slot]}: High Power SMU with preamp')
            elif self.slot_conf[slot].startswith('VS'):
                self.vs_numbers.append(int(self.slot_conf[slot][2]))
                print(f'{self.slot_conf[slot]}: Voltage Source')
            elif self.slot_conf[slot].startswith('VM'):
                print('f{self.slot_conf[slot]}: Voltage Meter')
            elif self.slot_conf[slot] == '':
                print('Empty Slot')
            else:
                raise Exception(
                    f'Problem parsing Keithley 4200 slot {slot} configuration: {self.slot_conf}')

    def configure_slot_smu(self, slot_number, smu_number):
        """Reconfigure smu instrument in slot_number to act as an smu.

        Applies the specified configuration to the object or hardware.

        Args:
            slot_number: Slot number to use.
            smu_number: Source-measure unit channel number (1-based).
        """
        assert slot_number >= 1
        assert slot_number <= 8
        # empty slot shouldn't be configured
        assert self.slot_conf[slot_number - 1] != ''
        assert smu_number >= 1
        assert smu_number <= 8
        self.get_interface().write((f"MP {slot_number}, SMU{smu_number}"))
        self.get_slot_configuration()

    def configure_slot_vs(self, slot_number, vsource_number):
        """Reconfigure smu instrument in slot_number to act as a vs.

        Applies the specified configuration to the object or hardware.

        Args:
            slot_number: Slot number to use.
            vsource_number: Vsource number to use.
        """
        assert slot_number >= 1
        assert slot_number <= 8
        # empty slot shouldn't be configured
        assert self.slot_conf[slot_number - 1] != ''
        assert vsource_number >= 1
        assert vsource_number <= 8
        self.get_interface().write((f"MP {slot_number}, VS{vsource_number}"))
        self.get_slot_configuration()

    def configure_slot_vm(self, slot_number, vmeter_number):
        """Reconfigure smu instrument in slot_number to act as a vm.

        Applies the specified configuration to the object or hardware.

        Args:
            slot_number: Slot number to use.
            vmeter_number: Vmeter number to use.
        """
        assert slot_number >= 1
        assert slot_number <= 8
        # empty slot shouldn't be configured
        assert self.slot_conf[slot_number - 1] != ''
        assert vmeter_number >= 1
        assert vmeter_number <= 8
        self.get_interface().write((f"MP {slot_number}, VM{vmeter_number}"))
        self.get_slot_configuration()

    def add_channels_smu_voltage(
            self, smu_number, voltage_force_channel_name, current_compliance_channel_name):
        # check smu_number is valid
        """Add a channels smu voltage.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            current_compliance_channel_name: Current compliance channel name to use.
            smu_number: Source-measure unit channel number (1-based).
            voltage_force_channel_name: Voltage force channel name to use.

        Returns:
            The newly created channel object.
        """
        return self._add_channels_smu_voltage(
            smu_number, voltage_force_channel_name, current_compliance_channel_name)

    def add_channel_smu_voltage_output_range(
            self, smu_number, output_range_channel_name):
        # check smu_number is valid
        """Add a channel smu voltage output range.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            output_range_channel_name: Output range channel name to use.
            smu_number: Source-measure unit channel number (1-based).

        Returns:
            The newly created channel object.
        """
        return self._add_channel_smu_voltage_output_range(
            smu_number, output_range_channel_name)

    def add_channels_smu_current(
            self, smu_number, current_force_channel_name, voltage_compliance_channel_name):
        # check smu_number is valid
        """Add a channels smu current.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            current_force_channel_name: Current force channel name to use.
            smu_number: Source-measure unit channel number (1-based).
            voltage_compliance_channel_name: Voltage compliance channel name to use.

        Returns:
            The newly created channel object.
        """
        return self._add_channels_smu_current(
            smu_number, current_force_channel_name, voltage_compliance_channel_name)

    def add_channel_smu_current_output_range(
            self, smu_number, output_range_channel_name):
        # check smu_number is valid
        """Add a channel smu current output range.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            output_range_channel_name: Output range channel name to use.
            smu_number: Source-measure unit channel number (1-based).

        Returns:
            The newly created channel object.
        """
        return self._add_channel_smu_current_output_range(
            smu_number, output_range_channel_name)

    def add_channel_smu_voltage_sense(
            self, smu_number, voltage_sense_channel_name):
        # check smu_number is valid
        """Add a channel smu voltage sense.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            smu_number: Source-measure unit channel number (1-based).
            voltage_sense_channel_name: Voltage sense channel name to use.

        Returns:
            The newly created channel object.
        """
        return self._add_channel_smu_voltage_sense(
            smu_number, voltage_sense_channel_name)

    def add_channel_smu_current_sense(
            self, smu_number, current_sense_channel_name):
        # check smu_number is valid
        """Add a channel smu current sense.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            current_sense_channel_name: Current sense channel name to use.
            smu_number: Source-measure unit channel number (1-based).

        Returns:
            The newly created channel object.
        """
        return self._add_channel_smu_current_sense(
            smu_number, current_sense_channel_name)

    def add_channel_vsource(self, vsource_number, vsource_channel_name):
        # check vsource_number is valid
        """Add a channel vsource.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            vsource_channel_name: Vsource channel name to use.
            vsource_number: Vsource number to use.

        Returns:
            The newly created channel object.
        """
        return self._add_channel_vsource(vsource_number, vsource_channel_name)

    def add_channel_vmeter(self, vmeter_number, vmeter_channel_name):
        # check vmeter_number is valid
        """Add a channel vmeter.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            vmeter_channel_name: Vmeter channel name to use.
            vmeter_number: Vmeter number to use.

        Returns:
            The newly created channel object.
        """
        return self._add_channel_vmeter(vmeter_number, vmeter_channel_name)
