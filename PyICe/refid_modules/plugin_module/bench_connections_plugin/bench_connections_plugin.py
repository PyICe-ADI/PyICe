from PyICe.refid_modules.plugin_module.plugin       import plugin
from PyICe.bench_configuration_management           import bench_configuration_management, bench_visualizer
from types import MappingProxyType
import importlib, os, inspect, sys, types

class bench_connections(plugin):
    desc = "This plugin compares bench setups between tests being run together to verify there are no conflicts, and produces a diagram of the setup."
    def __init__(self, test_mod, default_bench_location, visualizer_locations):
        super().__init__(test_mod)
        self.tm.interplugs['check_bench_connections_pre_amalgamation']=[]
        self.tm.interplugs['check_bench_connections_post_amalgamation']=[]
        self.bc = default_bench_location.default_bench_configuration
        self.file_locations(default_bench_location, visualizer_locations)


    def __str__(self):
        return "This plugin compares bench setups between tests being run together to verify there are no conflicts, and produces a diagram of the setup."

    def file_locations(self, default_bench_location, visualizer_locations):
        '''
        These are files that need to be made per project to make the plugin function. See the templates for an example script of each.
        '''
        self.bc = default_bench_location.default_bench_configuration
        self.locations = visualizer_locations

    def _set_atts_(self):
        self.att_dict = MappingProxyType({
                    '_get_components_dict':self._get_components_dict,
                    '_get_default_connections':self._get_default_connections,
                    '_get_connection_diagram':self._get_connection_diagram,
                    'check_bench_connections':self.check_bench_connections,
                    'add_bench_traceability_channel':self.add_bench_traceability_channel,
                    })
    def get_atts(self):
        return self.att_dict

    def get_hooks(self):
        plugin_dict={
                    'pre_collect':[self._set_one_and_done],
                    'begin_collect':[self.check_bench_connections],
                    'tm_logger_setup': [self.add_bench_traceability_channel, self._set_one_and_done],
                     }
        return plugin_dict
    def set_interplugs(self):
        pass
    def execute_interplugs(self, hook_key, *args, **kwargs):
        for (k,v) in self.tm.interplugs.items():
            if k is hook_key:
                for f in v:
                    f(*args, **kwargs)

    def _set_one_and_done(self, *args):
        self.tm.tt._need_to_benchcheck=True

    def check_bench_connections(self):
        '''
        This only needs to be run once per regression. It combines all the connections listed in the test scripts of the regression and makes sure that
        there are no conflicts. e.g. a single port with two connections or a blocked port with a connection.
        '''
        if self.tm.tt._need_to_benchcheck:
            self.components_dict = self._get_components_dict()
            all_connections = {}
            for test in self.tm.tt:
                self.connection_collection = self._get_connection_collection(test=test)
                if len(self.tm.tt) > 1 and not test.is_included():
                    if input(f'Excluded test {test.get_name()} included in multi-test regression. Reason: {test.get_exclude_reason()} Continue? [y/n]: ').lower() == 'y':
                        continue
                    else:
                        breakpoint()
                test.configure_bench(self.components_dict, self.connection_collection)
                self.execute_interplugs('check_bench_connections_pre_amalgamation')
                all_connections[test] = self.connection_collection
            connections = bench_configuration_management.connection_collection.distill(all_connections.values())
            connections.print_connections(exclude = self._get_default_connections())
            if self.locations is not None:
                visualizer = bench_visualizer.visualizer(connections=connections.connections, locations=self.locations.component_locations().locations)
                visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')
            self.tm.tt.connection_diagram = connections.print_connections()
            
            self.connections = connections
            ###############################################################################
            # This can be used to dump the terminals list for easy reference.
            # Not sure where to put this - Dave - please help if interested.
            ###############################################################################
            # f = open("terminals_reference.txt", "w")
            # print(bench_components.print_terminals_by_component(), file=f)
            # f.close()
            owners = set()
            for x in range(len(self.connections.get_connections())):
                owners.add(self.connections.get_connections()[x].terminals[0].get_owner())
                owners.add(self.connections.get_connections()[x].terminals[1].get_owner())
            # modifiers = board_template_modifiers.board_template_modifiers(owners)
            self.execute_interplugs('check_bench_connections_post_amalgamation')
        self.tm.tt._need_to_benchcheck=False
        
    def _get_components_dict(self):
        return self.bc.component_collection().get_components()
    def _get_connection_collection(self, test):
        return self.bc.default_connections(self.components_dict, name=type(test).__name__)
    def _get_default_connections(self):
        return self.bc.default_connections(self.components_dict, name="default").get_connections()
    def _get_connection_diagram(self):
        return self.connection_diagram
    def add_bench_traceability_channel(self, logger):
        '''
        Adds the sum connections made for the regression into the sql table.
        '''
        logger.add_channel_dummy('bench_configuration')
        logger['bench_configuration'].set_category('eval_traceability')
        logger.write('bench_configuration', self.tm.tt.connection_diagram)
        logger['bench_configuration'].set_write_access(False)
