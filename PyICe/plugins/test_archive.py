import os, re, sqlite3

class database_archive():
    def __init__(self, test_script_file, db_source_file):
        '''This class is part of the archive plugin for the PyICe Infrastructure Extensions and manipulates tables in a given SQlite database. Specifically, it can copy, move, or delete a table.
        args:
            test_script_file - str. File location of the test that collected the data.
            db_source_file - str. Path to the database that will be manipulated.'''
        self.test_script_file = test_script_file
        self.db_source_file = os.path.abspath(db_source_file)
        (self.db_source_abspath, self.db_source_filename) = os.path.split(self.db_source_file)
        self.db_source_folder = os.path.basename(self.db_source_abspath)
        self.source_conn = sqlite3.connect(self.db_source_file)

    def has_data(self, tablename):
        '''A quick check that the given table has some data in it.
        args:
            tablename - str. Name of the table to be reviewed.
        Returns:
            True if there is at least one row of data, and False if not.'''
        cur = self.source_conn.cursor()
        res = cur.execute(f'SELECT * FROM {tablename}').fetchall()
        cur.close()
        if len(res): 
            return True
        else:
            return False
        
    def copy_table(self, db_source_table, db_dest_table, db_dest_file, db_indices=[]):
        '''Copies a table from the given database to a different.
        args:
            db_source_table - str. The name of the table to be copied.
            db_dest_table - str. What the copy table will be called.
            db_dest_file - str. The path to the new database.
            db_indices - list. A list of lists consisting of column names in the database as strings. Each list will be used to create an index in the new database.'''
        conn = sqlite3.connect(db_dest_file)
        attach_schema = '__source_db__'
        
        conn.execute(f"ATTACH DATABASE '{self.db_source_file}' AS {attach_schema}")
        ##############
        # Main table #
        ##############
        orig_create_statement = conn.execute(f"SELECT sql FROM {attach_schema}.sqlite_master WHERE name == '{db_source_table}'").fetchone()[0]
        (new_create_statement, sub_count) = re.subn(pattern = f'^CREATE TABLE {db_source_table} \( rowid INTEGER PRIMARY KEY, datetime DATETIME, (.*)$',
                                                    repl = f'CREATE TABLE {db_dest_table} ( rowid INTEGER PRIMARY KEY, datetime DATETIME, \\1',
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
        conn.execute(f'INSERT INTO {db_dest_table} SELECT * FROM {attach_schema}.{db_source_table}')

        ###############
        # Format view #
        ###############
        # Rename this view
        row = conn.execute(f"SELECT sql FROM {attach_schema}.sqlite_master WHERE name == '{db_source_table}_formatted'").fetchone()
        if row is not None:
            # Some tables don't have _formatted and _all views if there are no presets/formats in the source data.
            orig_create_statement = row[0]
            (new_create_statement, sub_count) = re.subn(pattern = f'^CREATE VIEW {db_source_table}_formatted AS SELECT(.*)$',
                                                        repl = f'CREATE VIEW {db_dest_table}_formatted AS SELECT\\1',
                                                        string=orig_create_statement,
                                                        count=1,
                                                        flags=re.MULTILINE
                                                        )
            assert sub_count == 1
            # Rename source table
            (new_create_statement, sub_count) = re.subn(pattern = f'FROM {db_source_table}',
                                                        repl = f'FROM {db_dest_table}',
                                                        string=new_create_statement,
                                                        count=4,
                                                        flags=re.MULTILINE
                                                        )
            assert sub_count == 4
            conn.execute(new_create_statement)
            
            ###############
            # Joined view #
            ###############
            conn.execute(f'CREATE VIEW {db_dest_table}_all AS SELECT * FROM {db_dest_table} JOIN {db_dest_table}_formatted USING (rowid)')
        
        for column_list in db_indices:
            columns_str = f'({",".join(column_list)})'
            idx_name = f'{db_dest_table}_{"_".join(column_list)}_idx'
            try:
                conn.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {db_dest_table} {columns_str}')
            except sqlite3.OperationalError as e:
                missing_col_mat = re.match('no such column: (?P<missing_col>\w+)', str(e)) #alphanumeric column names only? prob ok.
                if missing_col_mat is not None:
                    print(f"One or more of {columns_str} do not exist.")
                    breakpoint()
                else:
                    print(e)
                    print('This is unexpected. Please contact support.')
                    breakpoint()
                    pass
        ###########
        # Wrap up #
        ###########
        conn.commit()
        conn.execute(f'DETACH DATABASE {attach_schema}')
        return True
    def delete_table(self, db_source_table, commit=True):
        '''Deletes the given table from the database.
        args:
            db_source_table - str. Name of the table to be deleted.'''
        self.source_conn.execute(f'DROP TABLE {db_source_table}')
        self.source_conn.execute(f'DROP VIEW IF EXISTS {db_source_table}_formatted')
        self.source_conn.execute(f'DROP VIEW IF EXISTS {db_source_table}_all')
        if commit:
            self.source_conn.commit()
    def get_table_names(self):
        '''Returns the names of all the tables in the initially given database.'''
        table_query = "SELECT name FROM sqlite_master WHERE type ='table'"
        return [row[0] for row in self.source_conn.execute(table_query)]
    @classmethod
    def ask_archive_folder(cls, suggestion=None):
        '''Asks the user for a name for a folder in the archive folder to store the archived data.
        args:
            suggestion - str.Default None. A default answer that will be offered to the user.
        Returns:
            If a suggestion was provided and no alternative was given by the user, the suggestion is returned. Otherwise, returns the input provided by the user.'''
        while True:
            suggestion_str = '' if suggestion is None else f'[{suggestion}]'
            archive_folder = input(f'Destination archive folder? {suggestion_str}: ')
            if len(archive_folder):
                break
            elif suggestion is not None:
                return suggestion
        return archive_folder
    def compute_db_destination(self, archive_folder):
        '''Creates the path to the archived database.
        args:
            archive_folder - str. The name for the folder that will house the archived data under the archive folder.
        Returns:
            Returns an os path to the new database.'''
        db_dest_folder = os.path.join(self.test_script_file, 'archive', archive_folder)
        db_dest_file = os.path.join(db_dest_folder, self.db_source_filename)
        os.makedirs(db_dest_folder, exist_ok=True)
        return db_dest_file
    def copy_interactive(self, archive_folder=None):
        '''A manual version of the archiving process automatically used after a test has finished collecting data. Useful for when something goes catastrophically wrong in a test and the archiving failed to complete.
        args:
            archive_folder - str. Default None. The name of the directory inside the archive folder where data in question will be stored.
        Returns:
            A list of tuples is returned consisting of the names of original tables and the names of their copies.'''
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
                resp = self.disposition_table(table_name=table, db_dest_file=db_dest_file)
                if resp is not None:
                    copied_tables_files.append((resp[0], resp[1]))
                    if input('Write archive plot script(s)? [y/[n]]: ').lower() in ['y', 'yes']:
                        import_file=os.path.realpath(os.path.relpath(os.getcwd(), start = os.environ['PYTHONPATH']))
                        import_file=import_file[import_file.find(project_folder_name):]
                        import_file += os.sep
                        import_file=import_file.replace(os.sep,".")
                        import_file += os.path.basename(os.getcwd())
                        self.write_plot_script(test_module= import_file, test_class=os.path.basename(os.getcwd()), db_table=resp[0], db_file=resp[1])
            self.source_conn.commit()
        return copied_tables_files
    def disposition_table(self, table_name, db_dest_file, db_indices=[]):
        '''This asks the user what action is to be performed on a given table, and executes that action immediately.
        args:
            table_name - str. Name of a table in the initially declared database.
            db_dest_file - str. Path to the archived database.
            db_indices - list. Default []. A list of lists comprising string names of columns. Each list becomes an index in the archived database.
        Returns:
            If the user elects to skip or delete a table, None is returned. If a copy is instead either copied or outright moved, a tuple is returned of the original name and the name given to the new archived table.'''
        while True:
            action = input(f'{table_name} action? (s[kip], c[opy], m[ove], d[elete]) : ')
            if action.lower() == 's' or action.lower() == 'skip':
                return None
            elif action.lower() == 'c' or action.lower() == 'copy':
                db_dest_table = input(f'\tDestination table? [{table_name}]: ')
                if not len(db_dest_table):
                    db_dest_table = table_name
                if self.copy_table(db_source_table=table_name, db_dest_table=db_dest_table, db_dest_file=db_dest_file, db_indices=db_indices):
                    return ((db_dest_table, db_dest_file))
                else:
                    return None
            elif action.lower() == 'm' or action.lower() == 'move':
                db_dest_table = input(f'\tDestination table? [{table_name}]: ')
                if not len(db_dest_table):
                    db_dest_table = table_name
                if self.copy_table(db_source_table=table_name, db_dest_table=db_dest_table, db_dest_file=db_dest_file, db_indices=db_indices):
                    self.delete_table(table_name, commit=False)
                    return ((db_dest_table, db_dest_file))
                else:
                    return None
            elif action.lower() == 'd' or action.lower() == 'delete':
                conf_resp = input(f'\tConfirm delete? [(yes/[no]]: ')
                if conf_resp.lower() == 'yes':
                    self.delete_table(table_name, commit=False)
                    return None
    @classmethod
    def write_plot_script(cls, import_str, db_table, db_file):
        '''This creates a file that can be run to replot data in an adjacent database using a given test's plot method.
        args:
            import_str - str. Folder path from a PYTHONPATH to the directory containing the test script.'''
        (dest_folder, f) = os.path.split(os.path.abspath(db_file))
        dest_file = os.path.join(dest_folder, f"replot_data.py")
        plot_script_src = "if __name__ == '__main__':\n"
        plot_script_src += f"    from PyICe.plugins.plugin_manager import Plugin_Manager\n"
        plot_script_src += f"    from {import_str}.test import Test\n"
        plot_script_src += f"    pm = Plugin_Manager()\n"
        plot_script_src += f"    pm.add_test(Test)\n"
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
    def __init__(self, archive_location=None, db_location=None):
        if archive_location is None:
            archive_location = input('What is the filepath to the archive directory? ')
        if db_location is None:
            db_location = input('What is the filepath to the directory of the database? ')
        db_arch = database_archive(archive_location, db_location+'/data_log.sqlite')
        db_arch.copy_interactive()

if __name__ == '__main__':
    db_arch = database_archive('../', './data_log.sqlite')
    db_arch.copy_interactive()
