#!/usr/bin/env python

import os
import sqlite3
import re
# from . import p4_traceability

class database_archive():
    def __init__(self, db_source_file): #, db_dest_file=None, db_source_table=None, db_dest_table=None):
        self.db_source_file = os.path.abspath(db_source_file)
        (self.db_source_abspath, self.db_source_filename) = os.path.split(self.db_source_file)
        self.db_source_folder = os.path.basename(self.db_source_abspath)
        self.source_conn = sqlite3.connect(self.db_source_file)
    def copy_table(self, db_source_table, db_dest_table, db_dest_file, db_indices):
        # p4_info = p4_traceability.get_fstat(db_dest_file)
        # # Basic OS writability check???
        if False:
            pass
        # if p4_info['depotFile'] is not None and p4_info['action'] is None:
            # # TODO: Ask to p4 check out
            # print('Skipping copy. Destination database checked in')
            # return False
        else:
            # attach_schema = '__dest_db__'
            
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
                print(e) # table already exists?
                # Abort
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
                        print(f"You done goofed. One or more of {columns_str} do not exist. Now think about what you've done.")
                        breakpoint()
                    else:
                        print(e)
                        print('This is unexpected. Please email trace above to PyICe-developers@analog.com.')
                        breakpoint()
                        pass
            ###########
            # Wrap up #
            ###########
            conn.commit()
            conn.execute(f'DETACH DATABASE {attach_schema}')
            # print('copy')
            # print(db_source_table)
            # print(db_dest_table)
            # print(db_dest_file)
            return True #Probably ok, if we made it this far
    def delete_table(self, db_source_table, commit=True):
        # p4_info = p4_traceability.get_fstat(db_source_table)
        # #Basic OS writability check???
        if False:
            pass
        # if p4_info['depotFile'] is not None and p4_info['action'] is None:
            # # TODO: Ask to p4 check out
            # print('Skipping delete. Source database checked in')
        else:
            self.source_conn.execute(f'DROP TABLE {db_source_table}')
            self.source_conn.execute(f'DROP VIEW IF EXISTS {db_source_table}_formatted')
            self.source_conn.execute(f'DROP VIEW IF EXISTS {db_source_table}_all')
            if commit:
                self.source_conn.commit()
        # print("delete", db_source_table)
    def get_table_names(self):
        table_query = "SELECT name FROM sqlite_master WHERE type ='table'"
        return [row[0] for row in self.source_conn.execute(table_query)]
    @classmethod
    def ask_archive_folder(cls, suggestion=None):
        while True:
            suggestion_str = '' if suggestion is None else f'[{suggestion}]'
            archive_folder = input(f'Destination archive folder? {suggestion_str}: ')
            if len(archive_folder):
                break
            elif suggestion is not None:
                return suggestion
        return archive_folder
    def compute_db_destination(self, archive_folder):
        db_dest_folder = os.path.join(self.db_source_abspath, 'archive', archive_folder)
        db_dest_file = os.path.join(db_dest_folder, self.db_source_filename)
        os.makedirs(db_dest_folder, exist_ok=True)
        return db_dest_file
    def copy_interactive(self, archive_folder=None, project_folder_name=None):
        copied_tables_files = []
        table_names = self.get_table_names()
        if len(table_names):
            print("Database tables:")
            for table in table_names:
                # Give wold view before start of inquisition.
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
                        import_file += '\\'
                        import_file=import_file.replace('\\',".")
                        import_file += os.path.basename(os.getcwd())
                        self.write_plot_script(test_module= import_file, test_class=os.path.basename(os.getcwd()), db_table=resp[0], db_file=resp[1])
            self.source_conn.commit()
        return copied_tables_files
    def disposition_table(self, table_name, db_dest_file, db_indices):
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
    def write_plot_script(cls, test_module, test_class, db_table, db_file):
        # TODO: allow list of modules/databases to plot? How?
        (dest_folder, f) = os.path.split(os.path.abspath(db_file))
        dest_file = os.path.join(dest_folder, f"plot_{test_class}.py")
        db_rel = os.path.relpath(db_file, start=os.path.commonpath((dest_file, db_file)))
        plot_script_src = "if __name__ == '__main__':\n"
        plot_script_src += f"    from {test_module} import {test_class}\n"
        plot_script_src += f"    {test_class}.plot_from_table(table_name=r'{db_table}', db_file=r'{db_rel}')\n"
        try:
            with open(dest_file, 'a') as f: #exists, overwrite, append?
                f.write(plot_script_src)
        except Exception as e:
            #write locked? exists?
            print(type(e))
            print(e)
        else:
            return dest_file


if __name__ == '__main__':
    db_arch = database_archive('./data_log.sqlite')
    db_arch.copy_interactive()
