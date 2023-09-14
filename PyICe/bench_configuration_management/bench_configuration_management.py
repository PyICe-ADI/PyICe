from PyICe import lab_utils
import abc

ARROW_STRING = "◄――――――――►"

class terminal():
    def __init__(self, type, owner, instrument):
        self.type = type
        self.owner = owner
        self.instrument = instrument
    def get_type(self):
        return self.type
    def get_owner(self):
        return self.owner
    def get_ownerclass(self):
        return self.instrument

class bench_configuration_error(ValueError):
    '''This is the parent class of all configuration errors'''

class generic_instrument_class():
    '''Generic Instrument, has no peers'''

class bench_config_component():
    '''Parent of all components'''
    def __init__(self, name):
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = generic_instrument_class
    def add_terminal(self, name, instrument=None):
        if name in self._terminals:
            raise ValueError(f"\n\n*** ERROR: Bad component definition in {self.type}. Duplicate terminal name: '{name}'.\n")
        self._terminals[name] = terminal(type=name, owner=self.name, instrument=instrument)
    @abc.abstractmethod    
    def add_terminals(self):
        '''Prototype. Make repeated calls to self.add_terminal.'''
    def get_terminals(self):
        return self._terminals
    def get_name(self):
        return self.name
    def get_terminals(self):
        return self._terminals
    def __getitem__(self, item):
        return self._terminals[item]
    def __contains__(self, item):
        return item in self._terminals
    def __iter__(self):
        return self._terminals.keys()

class component_collection():
    def __init__(self):
        self.components = {}
    def add_component(self, component):
        self.components[component.get_name()] = component
    def get_components(self):
        return self.components
    def print_components(self):
        print("Bench Configuration Components:")
        print("-------------------------------")
        for component in self.components:
            print(component)
        print("\n")
    def print_terminals_by_component(self):
        text = ''
        for component in self.components:
            text += f'{component}\n'
            for terminal in self.components[component].get_terminals():
                text += f'    components["{component}"]["{terminal}"]\n'
        return text

class connection():
    def __init__(self, *terminals, owner=None):
        self.terminals = terminals[0] # Why is the indexing needed to prevent list of lists?
        self.owner = owner
    def get_terminals(self):
        return self.terminals
    def get_script_name(self):
        return self.owner
    def has_terminals(self, terminal_list):
        return terminal_list[0] in self.terminals and terminal_list[1] in self.terminals
    def has_terminal(self, terminal):
        return terminal in self.terminals

class connection_collection():
    def __init__(self, name):
        self.connections = []
        self.blocked_terminals = []
        self.name = name
        self._invalid_config = False
    def set_invalid(self):
        self._invalid_config = True
    def block_connection(self, terminal):
        self.blocked_terminals.append(terminal)
    def unblock_connection(self, terminal):
        if terminal in self.blocked_terminals:
            self.blocked_terminals.remove(terminal)
    def add_connection(self, *terminals):
        if len(terminals) != 2:
            raise ValueError("\nConnections must specify precisely 2 terminals.\n")
        connected_already = False
        for connextion in self.connections:
            connected_already = (terminals[0] in connextion.terminals and terminals[1] in connextion.terminals) or connected_already
        if not connected_already:
            self.connections.append(connection(terminals, owner=self.name))
    def remove_connection(self, *terminals):
        for connextion in self.connections:
            if connextion.has_terminals([terminals[0], terminals[1]]):
                self.connections.remove(connextion)
    def delete_connection(self, connextion):
        if connextion in self.connections:
            self.connections.remove(connextion)
    def get_connections(self):
        return self.connections
    def print_connections(self, exclude=None):       
        connection_diagram = ""
        for connextion in self.connections:
            ok=True
            if exclude is not None:
                for excon in exclude:
                    check = ((excon.terminals[0].get_owner(),excon.terminals[0].get_type()),(excon.terminals[1].get_owner(), excon.terminals[1].get_type()))
                    if (connextion.terminals[0].get_owner(),connextion.terminals[0].get_type()) and (connextion.terminals[1].get_owner(),connextion.terminals[1].get_type()) in check:
                        ok=False
            if not ok:
                continue
            connection_diagram += (35-len(f"{connextion.terminals[0].get_owner()}:{connextion.terminals[0].get_type()}"))*" "+f"{connextion.terminals[0].get_owner()}:{connextion.terminals[0].get_type()}" + " " + ARROW_STRING + " " + f"{connextion.terminals[1].get_owner()}:{connextion.terminals[1].get_type()}\n"
        if exclude is not None:
            lab_utils.print_banner("Begin Bench Configuration Connections")
            print(connection_diagram)
            lab_utils.print_banner("End Bench Configuration Connections")
        return connection_diagram
    @classmethod
    def distill(cls, connection_collections):
        '''Checks compatibility, assert if conflicts. Vacuums down duplicates.'''
        aggregate_collection = connection_collection("aggregate_collection")
        # Make a dictionary whose keys are the connections, and whose values are the names of the scripts that supplied those connections
        connection_source={}
        for collection in connection_collections:
            if collection._invalid_config:
                pass # TODO Do something
            for potential_connection in collection.get_connections():
                connection_poi = potential_connection.terminals[0].get_owner(), potential_connection.terminals[0].get_type(), potential_connection.terminals[1].get_owner(), potential_connection.terminals[1].get_type()
                if len(aggregate_collection.get_connections()) == 0: # Prime the pump...
                    aggregate_collection.add_connection(potential_connection.terminals[0], potential_connection.terminals[1])
                    connection_source[connection_poi] = collection.get_connections()[0].get_script_name()
                for existing_connection in aggregate_collection.get_connections():
                    if not existing_connection.has_terminals([potential_connection.terminals[0], potential_connection.terminals[1]]):
                        aggregate_collection.add_connection(potential_connection.terminals[0], potential_connection.terminals[1])
                        connection_source[connection_poi] = collection.get_connections()[0].get_script_name()
            for blocked_terminal in collection.blocked_terminals:
                if blocked_terminal not in aggregate_collection.blocked_terminals:
                    aggregate_collection.blocked_terminals.append(blocked_terminal)
        aggregate_collection.check_consistency(connection_source)
        return aggregate_collection

    @classmethod
    def reload_from_string(cls, string, components):
        '''Recreates the visualizer from the bench_configuration string that is logged in the database'''
        logged_connections = connection_collection("logged_connections")
        connection_list_w_arrow = string.strip().split('\n')
        connection_list_of_lists=[]
        for connection in connection_list_w_arrow:
            remove_spaces = connection.strip()
            goodbye_arrow = remove_spaces.split(' ◄――――――――► ')
            separate_by_colon= [x.split(':') for  x in goodbye_arrow]
            ## So now we have [[[A,B],[C,D]],[[E,F],[G,H]], ...[[W,X],[Y,Z]]]
            connection_list_of_lists.append(separate_by_colon)
        # components = stowe_default_bench_configuration.stowe_component_collection().get_components()
        for x in connection_list_of_lists:
            logged_connections.add_connection(components[x[0][0]][x[0][1]],             components[x[1][0]][x[1][1]])
        return logged_connections

    def check_consistency(self, connection_source):
        def raise_error(terminal1,terminal2a,terminal2b, script1, script2):
            banner_a = lab_utils.build_banner("*** CONNECTION ERROR ***", f'"{terminal1.get_owner()}:{terminal1.get_type()}" is assigned differently in {script1}({terminal2a.get_owner()}:{terminal2a.get_type()}) and {script2}({terminal2b.get_owner()}:{terminal2b.get_type()}).')
            raise bench_configuration_error(banner_a)
        delete_connections = []
        for connextion1 in self.connections:
            connection_poi_1 = connextion1.terminals[0].get_owner(), connextion1.terminals[0].get_type(), connextion1.terminals[1].get_owner(), connextion1.terminals[1].get_type()
            for connextion2 in self.connections:
                connection_poi_2 = connextion2.terminals[0].get_owner(), connextion2.terminals[0].get_type(), connextion2.terminals[1].get_owner(), connextion2.terminals[1].get_type()
                if connextion1 is not connextion2 and (connextion1.has_terminal(connextion2.terminals[0]) or connextion1.has_terminal(connextion2.terminals[1])):
                    if connextion2.terminals[0] is connextion1.terminals[0]:
                        if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[1].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(connextion2.terminals[0],connextion1.terminals[1],connextion2.terminals[1], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[1].instrument if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[1].instrument
                        specific_instrument = connextion2.terminals[1].instrument if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[1].instrument
                        if not isinstance(generic_instrument, specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(connextion2.terminals[0],connextion1.terminals[1],connextion2.terminals[1], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        else:
                            delete_connections.append(connextion2 if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[0] is connextion1.terminals[1]:
                        if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[0].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(connextion2.terminals[0],connextion1.terminals[0],connextion2.terminals[1], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[1].instrument if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[0].instrument
                        specific_instrument = connextion2.terminals[1].instrument if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[0].instrument
                        if not isinstance(generic_instrument, specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(connextion2.terminals[0],connextion1.terminals[0],connextion2.terminals[1], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        else:
                            delete_connections.append(connextion2 if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[1] is connextion1.terminals[0]:
                        if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[1].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(connextion2.terminals[1],connextion1.terminals[1],connextion2.terminals[0], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[0].instrument if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[1].instrument
                        specific_instrument = connextion2.terminals[0].instrument if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[1].instrument
                        if not isinstance(generic_instrument, specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(connextion2.terminals[1],connextion1.terminals[1],connextion2.terminals[0], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        else:
                            delete_connections.append(connextion2 if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[1] is connextion1.terminals[1]:
                        if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[0].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(connextion2.terminals[1],connextion1.terminals[0],connextion2.terminals[0], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[0].instrument if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[0].instrument
                        specific_instrument = connextion2.terminals[0].instrument if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[0].instrument
                        if not isinstance(generic_instrument, specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(connextion2.terminals[1],connextion1.terminals[0],connextion2.terminals[0], connection_source[connection_poi_1], connection_source[connection_poi_2])
                        else:
                            delete_connections.append(connextion2 if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1)
        [self.delete_connection(connextion) for connextion in delete_connections]                    
        # Check for blocked terminals
        for connextion in self.connections:
            for terminal in connextion.get_terminals():
                if terminal in self.blocked_terminals:
                    terminals = [f"{terminal.get_owner()}:{terminal.get_type()}" for terminal in connextion.get_terminals()]
                    banner_b=lab_utils.build_banner("*** CONNECTION ERROR *** A Connection blocker blocks a requested connection.", f'"{terminal.get_owner()}:{terminal.get_type()}" blocks connection:', f'{terminals}')
                    raise bench_configuration_error(banner_b)

class configuration_parser():
    '''Can be used to reconstitute an equipment connection and terminal list from a displayable string.
       Not sure what the use model will be.
       Note that the original instrument type is lost as we did not store the actual Python datastructure in sqlite.
       This just returns a list of dictionaries from a bunched up string.'''
    def __init__(self, config_string):
        self.config_string = config_string
    def parse(self):
        connections = []
        for conn in self.config_string.split("\n")[:-1]: # last one is always an empty line
            connection = {}
            connection["comp0"],connection["term0"] = conn.split(ARROW_STRING)[0].strip().split(":")
            connection["comp1"],connection["term1"] = conn.split(ARROW_STRING)[0].strip().split(":")
            connections.append(connection)
        return connections

##############################################################################################
#                                                                                            #
# Test Code                                                                                  #
#                                                                                            #
##############################################################################################
if __name__ == "__main__":
    
    
    
    
    # ~~~~~~~~~~~~~~~~~~~ Mock User #1 File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    def configure_bench1(components, connections):
        connections.add_connection(components["BASE_BOARD"]["MEZZ_TOP"], components["LT3390_BOARD"]["MEZZ_BOT"])
        connections.block_connection(components["LT3390_BOARD"]["SW0"])
        pass
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



    # ~~~~~~~~~~~~~~~~~~~ Mock User #2 File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    def configure_bench2(components, connections):
        connections.add_connection(components["BASE_BOARD"]["MEZZ_TOP"], components["TARGET_BOARD"]["MEZZ_BOT"])
        connections.add_connection(components["TARGET_BOARD"]["SW0"], components["OSCILLOSCOPE"]["CH1"])
        # connections.add_connection(components["LT3390_BOARD"]["SW0"], components["OSCILLOSCOPE"]["CH2"])
        pass
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



    # ~~~~~~~~~~~~~~~~~~~ Mock Stowe Infrastructure Setup File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    from stowe_eval.stowe_eval_base.modules import stowe_default_bench_configuration
    from PyICe.bench_configuration_management import bench_configuration_management
    bench_components = stowe_default_bench_configuration.stowe_component_collection()
    components_dict = bench_components.get_components()
    all_connections = {}
    for configure_bench in [configure_bench1, configure_bench2]:
        connection_collection = stowe_default_bench_configuration.stowe_default_connections(components_dict, name=type(configure_bench).__name__)
        configure_bench(components_dict, connection_collection)
        all_connections[configure_bench] = connection_collection
    connections = bench_configuration_management.connection_collection.distill(all_connections.values())
    diagram = connections.print_connections()
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


































