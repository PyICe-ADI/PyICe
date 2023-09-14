123
from PyICe.refid_modules.plugin_module.plugin import plugin
from types import MappingProxyType
import importlib, os, inspect, sqlite3, sys, abc

class die_traceability(plugin):
    desc = "Creates columns in the datalog to store identifying information of the dut. Right now it's actually reading the traceability hash from within the part, but expect that to be generalized soon."
    def __init__(self, test_mod, project_die_traceability):
        super().__init__(test_mod)
        self.tm.interplugs['die_traceability_begin_collect']=[]
        self.tm.interplugs['die_traceability_set_traceability']=[]
        self._file_locations(project_die_traceability)

    def __str__(self):
        return "Creates columns in the datalog to store identifying information of the dut. Right now it's actually reading the traceability hash from within the part, but expect that to be generalized soon."

    def _file_locations(self,project_die_traceability):
        """
        Assigns provided file to an instance attribute.
        
        Args:
            project_die_traceability - project file.
        """
        sys.path.append(os.path.dirname(inspect.getsourcefile(type(self.tm))))
        project_file=project_die_traceability
        from . import die_traceability as die_tra
        self.die_tra=die_tra
        self.dt = die_tra.die_traceability

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                    'get_die_traceability_hash_table':self.get_die_traceability_hash_table,
                    '_get_traceability_info':self._get_traceability_info,
                    'establish_traceability':self.establish_traceability,
                    'set_traceability':self.set_traceability,
                    'initial_check':self.initial_check,
                    })
    def get_atts(self):
        return self.att_dict

    def get_hooks(self):

        plugin_dict={
                    'begin_collect':[self.initial_check],
                    'tm_plot_from_table':[self._get_traceability_info],
                    'post_collect':[self.set_traceability,self.get_die_traceability_hash_table],
                     }
        return plugin_dict

    def set_interplugs(self):
        try:
            self.tm.interplugs['register_test__test_from_table'].extend([self.establish_traceability])
            self.tm.interplugs['register_test__compile_test_results'].extend([self.get_die_traceability_hash_table])
            self.tm.interplugs['register_test_tt_compile_test_results'].extend([self.set_traceability])
        except KeyError:    ## Not using the optional other plug
            pass
        try:
            self.tm.interplugs['register_correlation_test_get_correlation_data'].extend([self.get_die_traceability_hash_table])
        except KeyError:    ## Not using the optional other plug
            pass

    def execute_interplugs(self, hook_key, *args, **kwargs):
        for (k,v) in self.tm.interplugs.items():
            if k is hook_key:
                for f in v:
                    f(*args, **kwargs)

####    ####    ####


    def get_db_table_name(self):
        """
        Returns the table name used by the script.
        
        Returns 
           string - name of table from database.
       """
        return self.tm.get_name()

    @abc.abstractmethod
    def initial_check(self):
        '''
        This will check to make sure that the dut can be identified before the data collection begins. Can also be used to pass identification info into the database.
        '''
        pass

    def establish_traceability(self, table_name, db_file):
        self.tm._test_results._set_traceability_info(**self._get_traceability_info(table_name=table_name, db_file=db_file))
        self.tm._correlation_results._set_traceability_info(**self._get_traceability_info(table_name=table_name, db_file=db_file))

    def _get_traceability_info(self, table_name, db_file):
        """
        Reads channels assigned in a project specific folder from the given table from the given database. If a table name and database file are not provided, the script will check self.tm's attributes to draw upon.
        
        Args:
            table_name  - Name of the table to look for.
            db_file     - File of the database. 
        Returns:
            Dictionary of the channels listed in the project specific die_traceability file and their values.
        """
        resp = {}
        #########################
        # Calculate from sqlite #
        #########################
        if table_name is None:
            table_name = self.tm.get_db_table_name()
        if db_file is None:
            db_file=self.tm._db_file

        die_data = self.dt.read_registers_sqlite(   register_list = self.dt.traceability_registers,
                                                    db_file = db_file,
                                                    db_table = table_name
                                                )
        for k,v in die_data.items():
            resp[k] = v
        return resp

    def traceability_json_addon(self, res_dict):
        """
        Add traceability info to the produced json.
        """
        trace_data = self.get_traceability_info()
        res_dict['collection_date'] = trace_data['datetime']
        res_dict['traceability'] = {k:v for k,v in trace_data.items() if k not in ['datetime']}

    def set_traceability(self,test=None):
        self._set_traceability(test=test)
        self.execute_interplugs('die_traceability_set_traceability', test)

    @abc.abstractmethod
    def _set_traceability(self,test):
        pass