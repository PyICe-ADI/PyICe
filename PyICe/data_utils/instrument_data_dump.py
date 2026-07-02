"""Instrument data dump utility.

Dumps channel data from one or more PyICe instruments to an SQLite database,
using their registered channel read methods and a PyICe logger. A companion
metadata table (``{table}_channel_meta``) is written alongside the data so
that instrument drivers can later identify their columns and plot them via
their ``plot_from_database`` classmethods.

Usage:
    from PyICe.data_utils.instrument_data_dump import instrument_data_dump

    # With any configured instrument(s):
    dump = instrument_data_dump(my_ena, db_filename='my_data.sqlite', table_name='bode')
    dump.log()   # first measurement
    # ... change conditions ...
    dump.log()   # second measurement
    dump.stop()  # close database

    # Multiple instruments in one dump:
    dump = instrument_data_dump(ena, scope, psu, db_filename='bench.sqlite', table_name='run1')

    # Plot back from database (no instrument connection needed):
    from PyICe.lab_instruments.ENA import keysight_e5061b_base
    keysight_e5061b_base.plot_from_database('my_data.sqlite', 'bode')

    # Or run standalone (interactive collect/plot menu):
    python -m PyICe.data_utils.instrument_data_dump
"""
import sqlite3
from PyICe import lab_core


class instrument_data_dump:
    """Dump instrument channel data to SQLite via a logger.

    Creates a persistent logger that can log multiple rows (one per call
    to log()) before being closed with stop(). Accepts any PyICe instrument
    (or multiple instruments) that has registered channels. Also writes a
    companion ``{table}_channel_meta`` table that records each channel's
    ``channel_type`` and ``measurement`` attributes, enabling instrument
    drivers to later identify and plot their data without a live connection.

    Args:
        *instruments: One or more instantiated PyICe instrument objects
            with channels already configured (e.g. via discover_and_configure).
        db_filename: SQLite database filename.
        table_name: Table name in the database. If None, prompts the user.
    """

    def __init__(self, *instruments, db_filename='data_dump.sqlite', table_name=None):
        assert len(instruments) > 0, "Provide at least one instrument."
        self._instruments = instruments
        self._logger = lab_core.logger(database=db_filename, use_threads=False)
        for inst in self._instruments:
            self._logger.add(inst)
        for ch in self._logger:
            if ch.get_attribute('channel_type') in ('x_data', 'y_data'):
                ch._set_type_affinity('PyICeBLOB')
        if table_name is None:
            table_name = ''
            while not len(table_name):
                table_name = input("Enter a table name for this measurement: ")
        self._table_name = table_name
        self._db_filename = db_filename
        self._logger.new_table(table_name)
        self._write_channel_metadata(table_name)

    def _write_channel_metadata(self, table_name):
        """Write a companion table storing channel attributes and instrument class paths."""
        meta_table = f'{table_name}_channel_meta'
        conn = sqlite3.connect(self._db_filename)
        conn.execute(f'DROP TABLE IF EXISTS [{meta_table}]')
        conn.execute(f'CREATE TABLE [{meta_table}] '
                     '(channel_name TEXT, channel_type TEXT, measurement TEXT,'
                     ' instrument_class TEXT)')
        # Build a map from channel name to instrument class path
        ch_to_class = {}
        for inst in self._instruments:
            cls = type(inst)
            class_path = f'{cls.__module__}.{cls.__qualname__}'
            for ch_name in inst.get_all_channel_names():
                ch_to_class[ch_name] = class_path
        for ch in self._logger:
            attrs = ch.get_attributes()
            ch_type = attrs.get('channel_type')
            measurement = attrs.get('measurement')
            class_path = ch_to_class.get(ch.get_name())
            conn.execute(f'INSERT INTO [{meta_table}] VALUES (?, ?, ?, ?)',
                         (ch.get_name(), ch_type, measurement, class_path))
        conn.commit()
        conn.close()

    def log(self):
        """Read all instrument channels and log one row to the database."""
        self._logger.log()

    def stop(self):
        """Close the database connection and disconnect from all instruments."""
        from PyICe.visa_wrappers import visaWrapperException
        self._logger.stop()
        for inst in self._instruments:
            try:
                inst.get_interface().close()
            except (visaWrapperException, OSError, AttributeError) as e:
                print(f"Warning: could not close {inst.get_name()}: {type(e).__name__}: {e}")
        print(f'Data logged to {self._db_filename}, table: {self._table_name}')


# Keep old name as an alias for backwards compatibility
ena_data_dump = instrument_data_dump


if __name__ == '__main__':
    import sys
    from PyICe.lab_utils import select_string_menu

    try:
        from local.my_instruments import instruments
    except ImportError as e:
        print("Could not import 'instruments' from local/my_instruments.py.")
        print("Create data_utils/local/my_instruments.py with an 'instruments' dict.")
        print(f"  Error: {e}")
        sys.exit(1)

    if not instruments:
        print("No instruments found in local/my_instruments.instruments.")
        sys.exit(1)

    answer = input("(P)lot existing data or (C)ollect new data: ").strip().lower()

    if answer == 'c':
        if len(instruments) == 1:
            name, instrument = next(iter(instruments.items()))
            selected = {name: instrument}
            print(f"Using instrument: {name}")
        else:
            selected_names = []
            while True:
                menu_items = []
                for k in instruments:
                    bullet = '•' if k in selected_names else ' '
                    menu_items.append(f'{bullet}{k}')
                choice = select_string_menu.select_string_menu(
                    'Select instrument(s) to log, then select exit.', menu_items)
                if choice is None:
                    break
                key = choice[1:]
                if key in selected_names:
                    selected_names.remove(key)
                else:
                    selected_names.append(key)
            if not selected_names:
                print("No instruments selected.")
                sys.exit(0)
            selected = {k: instruments[k] for k in selected_names}

        for name, inst in selected.items():
            channel_names = inst.get_all_channel_names()
            if not channel_names:
                print(f"Warning: '{name}' has no registered channels.")
            else:
                print(f"  {name}: {len(channel_names)} channel(s)")

        dump = instrument_data_dump(*selected.values())
        while True:
            resp = input("Press Enter to log a measurement, or 'q' to quit: ").strip().lower()
            if resp == 'q':
                break
            dump.log()
            print("  Logged.")
        dump.stop()
        print("Done.")

        # Plot the just-collected data
        instrument_classes = set(type(inst) for inst in selected.values())
        for cls in instrument_classes:
            if hasattr(cls, 'plot_from_database'):
                try:
                    cls.plot_from_database(dump._db_filename, dump._table_name)
                except (ValueError, KeyError):
                    continue

    elif answer == 'p':
        from PyICe.lab_utils.sqlite_data import sqlite_data

        db_filename = input("Database filename [data_dump.sqlite]: ").strip()
        if not db_filename:
            db_filename = 'data_dump.sqlite'

        db = sqlite_data(database_file=db_filename)
        all_tables = db.get_table_names()
        tables = [t for t in all_tables if not t.endswith('_channel_meta')]
        if not tables:
            print("No data tables found in database.")
            sys.exit(1)

        if len(tables) == 1:
            table_name = tables[0]
            print(f"Using table: {table_name}")
        else:
            print("Available tables:")
            for i, t in enumerate(tables):
                print(f"  {i + 1}. {t}")
            choice = input("Select table number: ").strip()
            table_name = tables[int(choice) - 1]

        # Try each instrument class's plot_from_database; multiple may succeed
        # if the table contains data from more than one instrument type.
        instrument_classes = set(type(inst) for inst in instruments.values())
        plotted = False
        for cls in instrument_classes:
            if hasattr(cls, 'plot_from_database'):
                try:
                    cls.plot_from_database(db_filename, table_name)
                    plotted = True
                except (ValueError, KeyError):
                    continue
        if not plotted:
            print(f"No instrument recognized the data in table '{table_name}'.")

    else:
        print(f"Unknown option: '{answer}'")
        sys.exit(1)
