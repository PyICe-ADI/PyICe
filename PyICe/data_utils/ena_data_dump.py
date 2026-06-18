"""ENA network analyzer data dump utility.

Dumps trace data and instrument conditions from a Keysight E5061B ENA
to an SQLite database, using the instrument's own channel read methods
and a PyICe logger.

Usage:
    from PyICe.data_utils.ena_data_dump import ena_data_dump

    # With an already-configured instrument:
    dump = ena_data_dump(my_ena_instrument)
    dump.data_to_sqlite()

    # Or run standalone:
    python -m PyICe.data_utils.ena_data_dump
"""
from PyICe.lab_instruments.ENA import keysight_e5061b_base
from PyICe import lab_core


class ena_data_dump:
    """Dump ENA trace data and instrument state to SQLite via a logger.

    The instrument's registered channels (frequency data, trace data,
    sweep settings, etc.) are read using their channel.read() methods
    and logged to an SQLite database.

    Args:
        instrument: An instantiated keysight_e5061b or keysight_e5061b_impedance
            object with traces already configured via add_channel_* methods.
    """

    def __init__(self, instrument):
        assert isinstance(instrument, keysight_e5061b_base), \
            f"Expected keysight_e5061b_base instance, got {type(instrument)}"
        self._instrument = instrument

    def data_to_sqlite(self, db_filename='ena_data.sqlite', table_name=None):
        """Read all instrument channels and log to SQLite.

        Creates a logger from the instrument's registered channels,
        sets list/array channels to PyICeBLOB affinity, and logs one row
        containing all current channel values.

        Args:
            db_filename: SQLite database filename.
            table_name: Table name in the database. If None, prompts the user.

        Returns:
            The table name used.
        """
        logger = lab_core.logger(database=db_filename, use_threads=False)
        logger.add(self._instrument)
        for ch in logger:
            if ch.get_attribute('channel_type') in ('x_data', 'y_data'):
                ch._set_type_affinity('PyICeBLOB')
        if table_name is None:
            table_name = ''
            while not len(table_name):
                table_name = input("Enter a table name for this measurement: ")
        logger.new_table(table_name)
        logger.log()
        logger.stop()
        print(f'ENA data logged to {db_filename}, table: {table_name}')
        return table_name


if __name__ == '__main__':
    import sys
    from PyICe import lab_interfaces

    if len(sys.argv) > 1:
        visa_address = sys.argv[1]
    else:
        visa_address = input("Enter VISA address for ENA (e.g. TCPIP0::192.168.1.1::inst0::INSTR): ")

    interface_factory = lab_interfaces.interface_factory()
    interface = interface_factory.get_visa_interface(visa_address)

    from PyICe.lab_instruments.ENA import keysight_e5061b
    ena = keysight_e5061b(interface)

    print("ENA connected.")
    print(f"Configured traces: {ena._configured_traces}")
    print(f"Registered channels: {ena.get_all_channel_names()}")

    if not any(ena._configured_traces.values()):
        print("No traces configured. Configure at least one trace before dumping.")
        print("Example: ena.add_channel_TR_mag('my_trace', trace_number=1, channel_number=1)")
        sys.exit(1)

    dump = ena_data_dump(ena)
    dump.data_to_sqlite()
    print("Done.")
