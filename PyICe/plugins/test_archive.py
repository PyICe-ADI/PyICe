"""Test archive plugin.

>>> from PyICe.plugins.test_archive import database_archive

"""
import os
import re
import sqlite3


class database_archive():
    """Database_archive.

    >>> from PyICe.plugins.test_archive import database_archive
    >>> database_archive is not None
    True

    """
    def __init__(self, test_script_file, db_source_file):
        """Initialize database archive for manipulating tables in a given SQLite database.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> database_archive is not None
        True

        Args:
            test_script_file: File location of the test that collected the data.
            db_source_file: Path to the database that will be manipulated.
        """
        self.test_script_file = test_script_file
        self.db_source_file = os.path.abspath(db_source_file)
        (self.db_source_abspath, self.db_source_filename) = os.path.split(
            self.db_source_file)
        self.db_source_folder = os.path.basename(self.db_source_abspath)
        self.source_conn = sqlite3.connect(self.db_source_file)

    def has_data(self, tablename):
        """A quick check that the given table has some data in it.
        Returns a boolean reflecting the object's current state.

        Returns a boolean reflecting the object's current state.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'has_data')
        True

        Args:
            tablename: Name of the table to be reviewed.

        Returns:
            True if there is at least one row of data, and False if not.
        """
        cur = self.source_conn.cursor()
        res = cur.execute(f'SELECT * FROM {tablename}').fetchall()
        cur.close()
        if len(res):
            return True
        else:
            return False

    def copy_table(self, db_source_table, db_dest_table,
                   db_dest_file, db_indices=None):
        """Copies a table from the given database to a different database.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'copy_table')
        True

        Args:
            db_source_table: The name of the table to be copied.
            db_dest_table: What the copy table will be called.
            db_dest_file: The path to the new database.
            db_indices: A list of lists consisting of column names in the database as strings. Each list will be used to create an index in the new database.
        """
        if db_indices is None:
            db_indices = []
        conn = sqlite3.connect(db_dest_file)
        attach_schema = '__source_db__'

        conn.execute(
            f"ATTACH DATABASE '{self.db_source_file}' AS {attach_schema}")
        ##############
        # Main table #
        ##############
        orig_create_statement = conn.execute(
            f"SELECT sql FROM {attach_schema}.sqlite_master WHERE name == '{db_source_table}'").fetchone()[0]
        (new_create_statement, sub_count) = re.subn(pattern=f'^CREATE TABLE {db_source_table} \\( rowid INTEGER PRIMARY KEY, datetime DATETIME, (.*)$',
                                                    repl=f'CREATE TABLE {db_dest_table} ( rowid INTEGER PRIMARY KEY, datetime DATETIME, \\1',
                                                    string=orig_create_statement,
                                                    count=1,
                                                    flags=re.MULTILINE
                                                    )
        assert sub_count == 1
        try:
            conn.execute(new_create_statement)
        except sqlite3.OperationalError as e:
            print(e)
            conn.rollback()
            conn.execute(f'DETACH DATABASE {attach_schema}')
            return
        conn.execute(
            f'INSERT INTO {db_dest_table} SELECT * FROM {attach_schema}.{db_source_table}')

        ###############
        # Format view #
        ###############
        # Rename this view
        row = conn.execute(
            f"SELECT sql FROM {attach_schema}.sqlite_master WHERE name == '{db_source_table}_formatted'").fetchone()
        if row is not None:
            # Some tables don't have _formatted and _all views if there are no
            # presets/formats in the source data.
            orig_create_statement = row[0]
            (new_create_statement, sub_count) = re.subn(pattern=f'^CREATE VIEW {db_source_table}_formatted AS SELECT(.*)$',
                                                        repl=f'CREATE VIEW {db_dest_table}_formatted AS SELECT\\1',
                                                        string=orig_create_statement,
                                                        count=1,
                                                        flags=re.MULTILINE
                                                        )
            assert sub_count == 1
            # Rename source table
            (new_create_statement, sub_count) = re.subn(pattern=f'FROM {db_source_table}',
                                                        repl=f'FROM {db_dest_table}',
                                                        string=new_create_statement,
                                                        count=4,
                                                        flags=re.MULTILINE
                                                        )
            assert sub_count == 4
            conn.execute(new_create_statement)

            ###############
            # Joined view #
            ###############
            conn.execute(
                f'CREATE VIEW {db_dest_table}_all AS SELECT * FROM {db_dest_table} JOIN {db_dest_table}_formatted USING (rowid)')

        for column_list in db_indices:
            columns_str = f'({",".join(column_list)})'
            idx_name = f'{db_dest_table}_{"_".join(column_list)}_idx'
            try:
                conn.execute(
                    f'CREATE INDEX IF NOT EXISTS {idx_name} ON {db_dest_table} {columns_str}')
            except sqlite3.OperationalError as e:
                # alphanumeric column names only? prob ok.
                missing_col_mat = re.match(
                    'no such column: (?P<missing_col>\\w+)', str(e))
                if missing_col_mat is not None:
                    print(f"One or more of {columns_str} do not exist.")
                    breakpoint()
                else:
                    print(e)
                    print('This is unexpected. Please contact support.')
                    breakpoint()
        ###########
        # Wrap up #
        ###########
        conn.commit()
        conn.execute(f'DETACH DATABASE {attach_schema}')
        return True

    def delete_table(self, db_source_table, commit=True):
        """Deletes the given table from the database.
        Permanently removes the specified table.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'delete_table')
        True

        Args:
            db_source_table: Name of the table to be deleted.
            commit: Whether to commit the transaction after deletion.
        """
        self.source_conn.execute(f'DROP TABLE {db_source_table}')
        self.source_conn.execute(
            f'DROP VIEW IF EXISTS {db_source_table}_formatted')
        self.source_conn.execute(f'DROP VIEW IF EXISTS {db_source_table}_all')
        if commit:
            self.source_conn.commit()

    def get_table_names(self):
        """Returns the names of all the tables in the initially given database.
        Returns the stored table names value from the object's internal state.
        Returns the stored table names from the object's internal state.

        Returns the stored table names from the object's internal state.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'get_table_names')
        True

        Returns:
            The current table names.
        """
        table_query = "SELECT name FROM sqlite_master WHERE type ='table'"
        return [row[0] for row in self.source_conn.execute(table_query)]

    @classmethod
    def ask_archive_folder(cls, suggestion=None):
        """Asks the user for a name for a folder in the archive folder to store the archived data.

        Persists the current state or data to durable storage.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> callable(getattr(database_archive, 'ask_archive_folder', None))
        True

        Args:
            suggestion: Default answer offered to the user, or None.

        Returns:
            The suggestion if no alternative was given, otherwise the user's input.
        """
        while True:
            suggestion_str = '' if suggestion is None else f'[{suggestion}]'
            archive_folder = input(
                f'Destination archive folder? {suggestion_str}: ')
            if len(archive_folder):
                break
            elif suggestion is not None:
                return suggestion
        return archive_folder

    def compute_db_destination(self, archive_folder):
        """Creates the path to the archived database.
        Computes the db destination from the available data.

        Supports the ``database_archive`` workflow by performing the described operation.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'compute_db_destination')
        True

        Args:
            archive_folder: Name of the folder under the archive folder for the archived data.

        Returns:
            OS path to the new database file.
        """
        db_dest_folder = os.path.join(
            self.test_script_file, 'archives', archive_folder)
        db_dest_file = os.path.join(db_dest_folder, self.db_source_filename)
        os.makedirs(db_dest_folder, exist_ok=True)
        return db_dest_file

    def copy_interactive(self, archive_folder=None):
        """A manual version of the archiving process. Useful when something goes wrong and archiving failed to complete.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'copy_interactive')
        True

        Args:
            archive_folder: Name of the directory inside the archive folder for the data. Default None.

        Returns:
            List of tuples of (original table name, copy table name).
        """
        copied_tables_files = []
        table_names = self.get_table_names()
        if len(table_names):
            print("Database tables:")
            for table in table_names:
                print(f"\t{table}")
            if archive_folder is None:
                archive_folder = self.ask_archive_folder()
            db_dest_file = self.compute_db_destination(archive_folder)
            for table in table_names:
                resp = self.disposition_table(
                    table_name=table, db_dest_file=db_dest_file)
                if resp is not None:
                    copied_tables_files.append((resp[0], resp[1]))
                    if input(
                            'Write archive plot script(s)? [y/[n]]: ').lower() in ['y', 'yes']:
                        import_file = os.path.realpath(os.path.relpath(
                            os.getcwd(), start=os.environ['PYTHONPATH']))
                        import_file = import_file[import_file.find(
                            project_folder_name):]  # noqa: F821 # pylint: disable=undefined-variable; known bug - should likely be self.project_folder_name but left as-is for backward compatibility
                        import_file += os.sep
                        import_file = import_file.replace(os.sep, ".")
                        import_file += os.path.basename(os.getcwd())
                        self.write_plot_script(
                            import_str=import_file,
                            db_table=resp[0], db_file=resp[1])
            self.source_conn.commit()
        return copied_tables_files

    def disposition_table(self, table_name, db_dest_file, db_indices=None):
        """Asks the user what action to perform on a given table and executes it immediately.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> hasattr(database_archive, 'disposition_table')
        True

        Args:
            table_name: Name of a table in the initially declared database.
            db_dest_file: Path to the archived database.
            db_indices: List of lists of column name strings. Each list becomes an index in the archived database.

        Returns:
            None if the user skips or deletes the table, or a tuple of (original name, archived name) if copied or moved.
        """
        if db_indices is None:
            db_indices = []
        while True:
            action = input(
                f'{table_name} action? (s[kip], c[opy], m[ove], d[elete]) : ')
            if action.lower() == 's' or action.lower() == 'skip':
                return None
            elif action.lower() == 'c' or action.lower() == 'copy':
                db_dest_table = input(f'\tDestination table? [{table_name}]: ')
                if not len(db_dest_table):
                    db_dest_table = table_name
                if self.copy_table(db_source_table=table_name, db_dest_table=db_dest_table,
                                   db_dest_file=db_dest_file, db_indices=db_indices):
                    return ((db_dest_table, db_dest_file))
                else:
                    return None
            elif action.lower() == 'm' or action.lower() == 'move':
                db_dest_table = input(f'\tDestination table? [{table_name}]: ')
                if not len(db_dest_table):
                    db_dest_table = table_name
                if self.copy_table(db_source_table=table_name, db_dest_table=db_dest_table,
                                   db_dest_file=db_dest_file, db_indices=db_indices):
                    self.delete_table(table_name, commit=False)
                    return ((db_dest_table, db_dest_file))
                else:
                    return None
            elif action.lower() == 'd' or action.lower() == 'delete':
                conf_resp = input('\tConfirm delete? [(yes/[no]]: ')
                if conf_resp.lower() == 'yes':
                    self.delete_table(table_name, commit=False)
                    return None

    @classmethod
    def write_plot_script(cls, import_str, db_table, db_file):
        """This creates a file that can be run to replot data in an adjacent database using a given test's plot method.
        Formats and sends the command to the instrument.
        Sends the ``if`` SCPI command to the instrument.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.plugins.test_archive import database_archive
        >>> callable(getattr(database_archive, 'write_plot_script', None))
        True

        Args:
            import_str - str. Folder path from a PYTHONPATH to the directory containing the test script.

        Args:
            db_file: Db file to use.
            db_table: Db table to use.
            import_str: Import str to use.

        Returns:
            True if the write was acknowledged, False otherwise.
        """
        (dest_folder, f) = os.path.split(os.path.abspath(db_file))
        dest_file = os.path.join(dest_folder, "replot_data.py")
        plot_script_src = "if __name__ == '__main__':\n"
        plot_script_src += "    from PyICe.plugins.plugin_manager import Plugin_Manager\n"
        plot_script_src += f"    from {import_str}.test import Test\n"
        plot_script_src += "    pm = Plugin_Manager()\n"
        plot_script_src += "    pm.add_test(Test)\n"
        plot_script_src += f"    pm.plot(database='data_log.sqlite', table_name='{db_table}')\n"
        try:
            with open(dest_file, 'a') as f:
                f.write(plot_script_src)
        except Exception as e:
            print(type(e))
            print(e)
        else:
            return dest_file


class manual_archive():
    """Manual_archive.

    >>> from PyICe.plugins.test_archive import manual_archive
    >>> manual_archive is not None
    True

    """
    def __init__(self, archive_location=None, db_location=None):
        """Initialize manual_archive.

        Prepares the object for use by setting up internal state.


        >>> from PyICe.plugins.test_archive import manual_archive
        >>> manual_archive is not None
        True

        Args:
            archive_location: Archive location to use.
            db_location: Db location to use.
        """
        if archive_location is None:
            archive_location = input(
                'What is the filepath to the archive directory? ')
        if db_location is None:
            db_location = input(
                'What is the filepath to the directory of the database? ')
        db_arch = database_archive(
            archive_location,
            db_location +
            '/data_log.sqlite')
        db_arch.copy_interactive()


if __name__ == '__main__':
    db_arch = database_archive('../', './data_log.sqlite')
    db_arch.copy_interactive()
