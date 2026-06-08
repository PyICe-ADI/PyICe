"""Bench configuration management plugin.

>>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import Diagram_Reconstructor

"""
from PyICe.lab_utils.banners import print_banner
import abc

ARROW_STRING = "◄――――――――►"
BLOCKED_STRING = "◄――――――――■ [BLOCKED]"


class Diagram_Reconstructor():
    """Diagram_ reconstructor.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import Diagram_Reconstructor
    >>> Diagram_Reconstructor is not None
    True

    """
    def __init__(self, connections, blocked_terminals):
        """Initialize diagram_ reconstructor.
        Stores configuration in ``blocked_terminals``, ``connections`` for use
        by other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import Diagram_Reconstructor
        >>> Diagram_Reconstructor is not None
        True

        Args:
            blocked_terminals: Blocked terminals to use.
            connections: Connections to use.
        """
        self.connections = connections
        self.blocked_terminals = blocked_terminals

    def get_connection_diagram(self):
        """Returns a presentable diagram centrally aligned. Becomes difficult to read if not enough window width is provided.
        Returns the stored connection diagram from the object's internal
        state.

        Returns the stored connection diagram from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import Diagram_Reconstructor
        >>> hasattr(Diagram_Reconstructor, 'get_connection_diagram')
        True

        Returns:
            The current connection diagram.
        """
        connection_diagram = ""
        for connection in self.connections:
            connection_diagram += (35 - len(f"{connection[0][0]}:{connection[0][1]}")) * " " + \
                f"{connection[0][0]}:{connection[0][1]}" + " " + \
                ARROW_STRING + " " + f"{connection[1][0]}:{connection[1][1]}\n"
        for blocked_terminal in self.blocked_terminals:
            connection_diagram += (35 - len(f"{blocked_terminal[0]}:{blocked_terminal[1]}")) * \
                " " + \
                f"{blocked_terminal[0]}:{blocked_terminal[1]}" + \
                " " + BLOCKED_STRING + "\n"
        return connection_diagram


class terminal():
    """A terminal object represents a potential port of a component to which a single connection can be made. A component will typically have one or more terminals. Terminals will likely be paired with connections once the bench wiring is defined. A terminal can only have a single connection. Any more will cause an error. A terminal represents a single port, regardless of pin count.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import terminal
    >>> terminal is not None
    True

    """

    def __init__(self, type, owner, instrument):
        """Initialize terminal.
        Stores configuration in ``instrument``, ``owner``, ``type`` for use by
        other methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import terminal
        >>> terminal is not None
        True

        Args:
            instrument: Instrument object providing hardware access.
            owner: Owner to use.
            type: Type specifier string.
        """
        self.type = type
        self.owner = owner
        self.instrument = instrument

    def get_type(self):
        """Return the current type.
        Returns the stored type value from the object's internal state.
        Returns the stored type from the object's internal state.

        Returns the stored type from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import terminal
        >>> hasattr(terminal, 'get_type')
        True

        Returns:
            The current type.
        """
        return self.type

    def get_owner(self):
        """Return the current owner.
        Returns the stored owner value from the object's internal state.
        Returns the stored owner from the object's internal state.

        Returns the stored owner from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import terminal
        >>> hasattr(terminal, 'get_owner')
        True

        Returns:
            The current owner.
        """
        return self.owner

    def get_ownerclass(self):
        """Return the current ownerclass.
        Returns the stored ownerclass value from the object's internal state.
        Returns the stored ownerclass from the object's internal state.

        Returns the stored ownerclass from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import terminal
        >>> hasattr(terminal, 'get_ownerclass')
        True

        Returns:
            The current ownerclass.
        """
        return self.instrument


class bench_configuration_error(ValueError):
    """This is the parent class of all configuration errors.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_configuration_error
    >>> raise bench_configuration_error("test")
    Traceback (most recent call last):
        ...
    PyICe.plugins.bench_configuration_management.bench_configuration_management.bench_configuration_error: test

    """


class generic_instrument_class():
    """Generic Instrument, has no peers.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import generic_instrument_class
    >>> generic_instrument_class is not None
    True

    """


class bench_config_component():
    """Parent of all components.

    A component represents a physical instrument on the bench that can have connections, like a piece of test equipment, circuit board with connectors, or probes.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
    >>> bench_config_component is not None
    True

    """
    def __init__(self, name):
        """Initialize bench_config_component.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> bench_config_component is not None
        True

        Args:
            name: Name identifier.
        """
        self.type = type(self)
        self.name = name
        self._terminals = {}
        self.add_terminals()
        self.is_a_kind_of = generic_instrument_class

    def add_terminal(self, name, instrument=None):
        """Add a terminal.
        Creates and registers a new terminal.

        Appends a new terminal entry to the object's internal collection.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, 'add_terminal')
        True

        Args:
            instrument: Instrument object providing hardware access.
            name: Name identifier.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        if name in self._terminals:
            raise ValueError(
                f"\n\n*** ERROR: Bad component definition in {self.type}. Duplicate terminal name: '{name}'.\n")
        self._terminals[name] = terminal(
            type=name, owner=self.name, instrument=instrument)

    @abc.abstractmethod
    def add_terminals(self):
        """Prototype. Make repeated calls to self.add_terminal.

        Appends a new terminals entry to the object's internal collection.

        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, 'add_terminals')
        True

        """

    def get_terminals(self):
        """Return the current terminals.
        Returns the stored terminals value from the object's internal state.
        Returns the stored terminals from the object's internal state.

        Returns the stored terminals from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, 'get_terminals')
        True

        Returns:
            The current terminals.
        """
        return self._terminals

    def get_name(self):
        """Return the current name.
        Returns the stored name value from the object's internal state.
        Returns the stored name from the object's internal state.

        Returns the stored name from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, 'get_name')
        True

        Returns:
            The current name.
        """
        return self.name

    def __getitem__(self, item):
        """Get item by key or index.
        Enables bracket-style indexing (``obj[key]``).

        Supports bracket-style indexing (``obj[key]``) for this container.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, '__getitem__')
        True

        Args:
            item: Item to process or look up.

        Returns:
            The item at the requested position or key.
        """
        return self._terminals[item]

    def __contains__(self, item):
        """Check if item is contained.
        Enables ``in`` membership testing.

        Supports the ``in`` operator for membership testing.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, '__contains__')
        True

        Args:
            item: Item to process or look up.

        Returns:
            True if the item is present, False otherwise.
        """
        return item in self._terminals

    def __iter__(self):
        """Return iterator over items.
        Enables iteration over the object's elements.

        Supports iteration with ``for ... in`` loops.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import bench_config_component
        >>> hasattr(bench_config_component, '__iter__')
        True

        Returns:
            An iterator over the contained items.
        """
        return iter(self._terminals.keys())


class component_collection():
    """A dictionary of all declared components on the bench. Keys are the assigned names provided at creation, and values are the component instances.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
    >>> component_collection is not None
    True

    """

    def __init__(self):
        """Initialize component_collection.

        Stores configuration in ``components`` for use by other methods.

        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
        >>> component_collection is not None
        True

        """
        self.components = {}

    def add_component(self, component):
        """Add a component.

        Appends a new component entry to the object's internal collection.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
        >>> hasattr(component_collection, 'add_component')
        True

        Args:
            component: Component to use.
        """
        self.components[component.get_name()] = component

    def get_components(self):
        """Return the current components.
        Returns the stored components value from the object's internal state.
        Returns the stored components from the object's internal state.

        Returns the stored components from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
        >>> hasattr(component_collection, 'get_components')
        True

        Returns:
            The current components.
        """
        return self.components

    def print_components(self):
        """Perform print components operation.

        Outputs the components to the console or display.

        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
        >>> hasattr(component_collection, 'print_components')
        True

        """
        print("Bench Configuration Components:")
        print("-------------------------------")
        for component in self.components:
            print(component)
        print("\n")

    def print_terminals_by_component(self):
        """Return print terminals by component result.
        Outputs the terminals by component to the console or display.

        Supports the ``component_collection`` workflow by performing the described operation.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import component_collection
        >>> hasattr(component_collection, 'print_terminals_by_component')
        True

        Returns:
            The print terminals by component result.
        """
        text = ''
        for component in self.components:
            text += f'{component}\n'
            for terminal in self.components[component].get_terminals():
                text += f'    components["{component}"]["{terminal}"]\n'
        return text


class connection():
    """A connection represents the physical linking of two different terminals between bench components. The two terminals can be from the same component or between terminals of different components, but only one connection can be assigned to any given terminal. Once a connection is made to a terminal, that terminal is considered "blocked".

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
    >>> connection is not None
    True

    """

    def __init__(self, *terminals, owner=None):
        """Initialize connection.
        Stores configuration in ``owner``, ``terminals`` for use by other
        methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
        >>> connection is not None
        True

        Args:
            *terminals: Additional positional arguments.
            owner: Owner to use.
        """
        # Why is the indexing needed to prevent list of lists?
        self.terminals = terminals[0]
        self.owner = owner

    def get_terminals(self):
        """Return the current terminals.
        Returns the stored terminals value from the object's internal state.
        Returns the stored terminals from the object's internal state.

        Returns the stored terminals from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
        >>> hasattr(connection, 'get_terminals')
        True

        Returns:
            The current terminals.
        """
        return self.terminals

    def get_script_name(self):
        """Return the script name.
        Returns the stored script name value from the object's internal state.
        Returns the stored script name from the object's internal state.

        Returns the stored script name from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
        >>> hasattr(connection, 'get_script_name')
        True

        Returns:
            The current script name.
        """
        return self.owner

    def has_terminals(self, terminal_list):
        """Return whether terminals exists.
        Returns a boolean reflecting the object's current state.

        Returns a boolean reflecting the object's current state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
        >>> hasattr(connection, 'has_terminals')
        True

        Args:
            terminal_list: Terminal list to use.

        Returns:
            True if the terminals condition is met, False otherwise.
        """
        return terminal_list[0] in self.terminals and terminal_list[1] in self.terminals

    def has_terminal(self, terminal):
        """Return whether terminal exists.
        Returns a boolean reflecting the object's current state.

        Returns a boolean reflecting the object's current state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection
        >>> hasattr(connection, 'has_terminal')
        True

        Args:
            terminal: Terminal to use.

        Returns:
            True if the terminal condition is met, False otherwise.
        """
        return terminal in self.terminals


class connection_collection():
    """An unindexed list of all connections made on a test bench. It has the ability to check consistency of all declared connections. If multiple connections are made to a single terminal or a connection is made to a terminal that has been declared "blocked", an error is raised.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
    >>> connection_collection is not None
    True

    """

    def __init__(self, name):
        """Initialize connection_collection.
        Initializes 6 instance attributes that configure the object's
        behavior.

        Initializes 6 instance attributes that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> connection_collection is not None
        True

        Args:
            name: Name identifier.
        """
        self.connections = []
        self.blocked_terminals = []
        self.readable_list = []
        self.readable_blocked = []
        self.name = name
        self._invalid_config = False

    def set_invalid(self):
        """Set the invalid.

        Updates the invalid in the object's internal state.

        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'set_invalid')
        True

        """
        self._invalid_config = True

    def block_connection(self, terminal):
        """Perform block connection operation.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'block_connection')
        True

        Args:
            terminal: Terminal to use.
        """
        if terminal not in self.blocked_terminals:
            self.blocked_terminals.append(terminal)

    def unblock_connection(self, terminal):
        """Perform unblock connection operation.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'unblock_connection')
        True

        Args:
            terminal: Terminal to use.
        """
        if terminal in self.blocked_terminals:
            self.blocked_terminals.remove(terminal)

    def add_connection(self, *terminals):
        """Add a connection.
        Adds a new connection to the object's internal collection.

        Appends a new connection entry to the object's internal collection.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'add_connection')
        True

        Args:
            *terminals: Additional positional arguments.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        if len(terminals) != 2:
            raise ValueError(
                "\nConnections must specify precisely 2 terminals.\n")
        connected_already = False
        for connextion in self.connections:
            connected_already = (
                terminals[0] in connextion.terminals and terminals[1] in connextion.terminals) or connected_already
        if not connected_already:
            self.connections.append(connection(terminals, owner=self.name))

    def remove_connection_by_terminals(self, *terminals):
        """If a connection exists between the given terminal objects, that connection is removed from the list of connections.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'remove_connection_by_terminals')
        True

        Args:
            *terminals: Additional positional arguments.
        """
        for connextion in self.connections:
            if connextion.has_terminals([terminals[0], terminals[1]]):
                self.connections.remove(connextion)
                return
        else:
            print(
                f'\n\n***\n* WARNING\n***\nPYICE BENCH CONFIG MANAGEMENT: Attempt to remove connection between terminals ({terminals[0].owner},{terminals[0].type}) and ({terminals[1].owner},{terminals[1].type}) failed. Such a connection does not exist in the list of connections.\n\n')

    def remove_connection(self, connextion):
        """If the provided connections object exists in the connection list, it shall be removed.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'remove_connection')
        True

        Args:
            connextion: Connextion to use.
        """
        if connextion in self.connections:
            self.connections.remove(connextion)
        else:
            print(
                f'\n\n***\n* WARNING\n***\nPYICE BENCH CONFIG MANAGEMENT: Attempt to remove connection between terminals ({connextion.get_terminals()[0].owner},{connextion.get_terminals()[0].type}) and ({connextion.get_terminals()[1].owner},{connextion.get_terminals()[1].type}) failed. Such a connection does not exist in the list of connections.\n\n')

    def get_connections(self):
        """Returns itself.
        Returns the stored connections value from the object's internal state.
        Returns the stored connections from the object's internal state.

        Returns the stored connections from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'get_connections')
        True

        Returns:
            The current connections.
        """
        return self

    def get_readable_connections(self):
        """Returns a parsable list of instrument terminal connections that is also human readable.
        Returns the stored readable connections value from the object's
        internal state.
        Returns the stored readable connections from the object's internal
        state.

        Returns the stored readable connections from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'get_readable_connections')
        True

        Returns:
            The current readable connections.
        """
        if not self.readable_list:
            for connection in self.connections:
                self.readable_list.append(([connection.get_terminals()[0].owner, connection.get_terminals(
                )[0].type], [connection.get_terminals()[1].owner, connection.get_terminals()[1].type]))
        return self.readable_list

    def get_readable_blocked_terminals(self):
        """Returns a parsable list of instrument terminal connections that is also human readable.
        Returns the stored readable blocked terminals value from the object's
        internal state.
        Returns the stored readable blocked terminals from the object's
        internal state.

        Returns the stored readable blocked terminals from the object's internal state.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'get_readable_blocked_terminals')
        True

        Returns:
            The current readable blocked terminals.
        """
        if not self.readable_blocked:
            for blocked in self.blocked_terminals:
                self.readable_blocked.append((blocked.owner, blocked.type))
        return self.readable_blocked

    def print_connections(self, exclude=None):
        """Returns a presentable diagram centrally aligned. Becomes difficult to read if not enough window width is provided.
        Outputs the connections to the console or display.

        Establishes the connection or prepares the resource for use.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'print_connections')
        True

        Args:
            exclude: Exclude to use.

        Returns:
            The print connections result.
        """
        connection_diagram = ""
        for connextion in self.connections:
            ok = True
            if exclude is not None:
                for excon in exclude:
                    check = (
                        (excon.terminals[0].get_owner(),
                         excon.terminals[0].get_type()),
                        (excon.terminals[1].get_owner(),
                         excon.terminals[1].get_type()))
                    if (connextion.terminals[0].get_owner(), connextion.terminals[0].get_type()) and (
                            connextion.terminals[1].get_owner(), connextion.terminals[1].get_type()) in check:
                        ok = False
            if not ok:
                continue
            connection_diagram += (
                35 - len(
                    f"{connextion.terminals[0].get_owner()}:{connextion.terminals[0].get_type()}")) * " " + f"{connextion.terminals[0].get_owner()}:{connextion.terminals[0].get_type()}" + " " + ARROW_STRING + " " + f"{connextion.terminals[1].get_owner()}:{connextion.terminals[1].get_type()}\n"
        for blocked_terminal in self.blocked_terminals:
            connection_diagram += (35 - len(f"{blocked_terminal.get_owner()}:{blocked_terminal.get_type()}")) * \
                " " + f"{blocked_terminal.get_owner()}:{blocked_terminal.get_type()}" + \
                " " + BLOCKED_STRING + "\n"
        if exclude is not None:
            print_banner("Begin Bench Configuration Connections")
            print(connection_diagram)
            print_banner("End Bench Configuration Connections")
        return connection_diagram

    @classmethod
    def distill(cls, connection_collections):
        """Checks compatibility, assert if conflicts. Vacuums down duplicates.

        Supports the ``connection_collection`` workflow by performing the described operation.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> callable(getattr(connection_collection, 'distill', None))
        True

        Args:
            connection_collections: Connection collections to use.

        Returns:
            The distill result.
        """
        aggregate_collection = connection_collection("aggregate_collection")
        # Make a dictionary whose keys are the connections, and whose values
        # are the names of the scripts that supplied those connections
        connection_source = {}
        for collection in connection_collections:
            if collection._invalid_config:
                pass  # TODO Do something
            for potential_connection in collection.connections:
                connection_poi = potential_connection.terminals[0].get_owner(), potential_connection.terminals[0].get_type(
                ), potential_connection.terminals[1].get_owner(), potential_connection.terminals[1].get_type()
                # Prime the pump...
                if len(aggregate_collection.connections) == 0:
                    aggregate_collection.add_connection(
                        potential_connection.terminals[0], potential_connection.terminals[1])
                    connection_source[connection_poi] = collection.connections[0].get_script_name(
                    )
                for existing_connection in aggregate_collection.connections:
                    if not existing_connection.has_terminals(
                            [potential_connection.terminals[0], potential_connection.terminals[1]]):
                        aggregate_collection.add_connection(
                            potential_connection.terminals[0], potential_connection.terminals[1])
                        connection_source[connection_poi] = collection.connections[0].get_script_name(
                        )
            for blocked_terminal in collection.blocked_terminals:
                if blocked_terminal not in aggregate_collection.blocked_terminals:
                    aggregate_collection.blocked_terminals.append(
                        blocked_terminal)
        aggregate_collection.check_consistency(connection_source)
        return aggregate_collection

    @classmethod
    def reload_from_string(cls, string, components):
        """Recreates the visualizer from the bench_configuration string that is logged in the database.

        Captures data for later analysis or replay.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> callable(getattr(connection_collection, 'reload_from_string', None))
        True

        Args:
            components: Components to use.
            string: String data.

        Returns:
            The reload from string result.
        """
        logged_connections = connection_collection("logged_connections")
        connection_list_w_arrow = string.strip().split('\n')
        connection_list_of_lists = []
        for connection in connection_list_w_arrow:
            remove_spaces = connection.strip()
            goodbye_arrow = remove_spaces.split(' ◄――――――――► ')
            separate_by_colon = [x.split(':') for x in goodbye_arrow]
            # So now we have [[[A,B],[C,D]],[[E,F],[G,H]], ...[[W,X],[Y,Z]]]
            connection_list_of_lists.append(separate_by_colon)
        for x in connection_list_of_lists:
            logged_connections.add_connection(
                components[x[0][0]][x[0][1]], components[x[1][0]][x[1][1]])
        return logged_connections

    def check_consistency(self, connection_source):
        """Perform check consistency operation.
        Validates the consistency and raises an exception if invalid.

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
        >>> hasattr(connection_collection, 'check_consistency')
        True

        Args:
            connection_source: Connection source to use.

        Raises:
            bench_configuration_error: If the bench configuration is invalid or missing.
        """
        def raise_error(terminal1, terminal2a, terminal2b, script1, script2):
            """Perform raise error operation.

            Performs the described operation on the object's internal state.


            >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import connection_collection
            >>> hasattr(connection_collection, 'raise_error')
            True

            Args:
                script1: Script1 to use.
                script2: Script2 to use.
                terminal1: Terminal1 to use.
                terminal2a: Terminal2a to use.
                terminal2b: Terminal2b to use.

            Raises:
                bench_configuration_error: If the bench configuration is invalid or missing.
            """
            print_banner("*** CONNECTION ERROR ***",
                         f'"{terminal1.get_owner()}:{terminal1.get_type()}" is assigned differently in',
                         f'{script1}({terminal2a.get_owner()}:{terminal2a.get_type()})',
                         'and',
                         f'{script2}({terminal2b.get_owner()}:{terminal2b.get_type()}).')
            raise bench_configuration_error()
        delete_connections = []
        for connextion1 in self.connections:
            connection_poi_1 = connextion1.terminals[0].get_owner(), connextion1.terminals[0].get_type(
            ), connextion1.terminals[1].get_owner(), connextion1.terminals[1].get_type()
            for connextion2 in self.connections:
                connection_poi_2 = connextion2.terminals[0].get_owner(), connextion2.terminals[0].get_type(
                ), connextion2.terminals[1].get_owner(), connextion2.terminals[1].get_type()
                if connextion1 is not connextion2 and (connextion1.has_terminal(
                        connextion2.terminals[0]) or connextion1.has_terminal(connextion2.terminals[1])):
                    if connextion2.terminals[0] is connextion1.terminals[0]:
                        if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[
                                1].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[0],
                                connextion1.terminals[1],
                                connextion2.terminals[1],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[1].instrument if connextion2.terminals[
                            1].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[1].instrument
                        specific_instrument = connextion2.terminals[1].instrument if connextion2.terminals[
                            1].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[1].instrument
                        if not isinstance(generic_instrument,
                                          specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[0],
                                connextion1.terminals[1],
                                connextion2.terminals[1],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        else:
                            delete_connections.append(
                                connextion2 if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[0] is connextion1.terminals[1]:
                        if connextion2.terminals[1].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[
                                0].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[0],
                                connextion1.terminals[0],
                                connextion2.terminals[1],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[1].instrument if connextion2.terminals[
                            1].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[0].instrument
                        specific_instrument = connextion2.terminals[1].instrument if connextion2.terminals[
                            1].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[0].instrument
                        if not isinstance(generic_instrument,
                                          specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[0],
                                connextion1.terminals[0],
                                connextion2.terminals[1],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        else:
                            delete_connections.append(
                                connextion2 if connextion2.terminals[1].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[1] is connextion1.terminals[0]:
                        if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[
                                1].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[1],
                                connextion1.terminals[1],
                                connextion2.terminals[0],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[0].instrument if connextion2.terminals[
                            0].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[1].instrument
                        specific_instrument = connextion2.terminals[0].instrument if connextion2.terminals[
                            0].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[1].instrument
                        if not isinstance(generic_instrument,
                                          specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[1],
                                connextion1.terminals[1],
                                connextion2.terminals[0],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        else:
                            delete_connections.append(
                                connextion2 if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1)
                    elif connextion2.terminals[1] is connextion1.terminals[1]:
                        if connextion2.terminals[0].instrument.is_a_kind_of is not generic_instrument_class and connextion1.terminals[
                                0].instrument.is_a_kind_of is not generic_instrument_class:
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[1],
                                connextion1.terminals[0],
                                connextion2.terminals[0],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        generic_instrument = connextion2.terminals[0].instrument if connextion2.terminals[
                            0].instrument.is_a_kind_of is generic_instrument_class else connextion1.terminals[0].instrument
                        specific_instrument = connextion2.terminals[0].instrument if connextion2.terminals[
                            0].instrument.is_a_kind_of is not generic_instrument_class else connextion1.terminals[0].instrument
                        if not isinstance(generic_instrument,
                                          specific_instrument.is_a_kind_of):
                            self.print_connections()
                            raise_error(
                                connextion2.terminals[1],
                                connextion1.terminals[0],
                                connextion2.terminals[0],
                                connection_source[connection_poi_1],
                                connection_source[connection_poi_2])
                        else:
                            delete_connections.append(
                                connextion2 if connextion2.terminals[0].instrument.is_a_kind_of is generic_instrument_class else connextion1)
        [self.remove_connection(connextion)
         for connextion in list(set(delete_connections))]
        # Check for blocked terminals
        for connextion in self.connections:
            for terminal in connextion.get_terminals():
                if terminal in self.blocked_terminals:
                    terminals = [
                        f"{terminal.get_owner()}:{terminal.get_type()}" for terminal in connextion.get_terminals()]
                    print_banner(
                        "*** CONNECTION ERROR *** A Connection blocker blocks a requested connection.",
                        f'"{terminal.get_owner()}:{terminal.get_type()}" blocks connection:',
                        f'{terminals}')
                    raise bench_configuration_error()


class configuration_parser():
    """Can be used to reconstitute an equipment connection and terminal list from a displayable string.

    Not sure what the use model will be.
    Note that the original instrument type is lost as we did not store the actual Python datastructure in sqlite.
    This just returns a list of dictionaries from a bunched up string.

    >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import configuration_parser
    >>> configuration_parser is not None
    True

    """
    def __init__(self, config_string):
        """Initialize configuration_parser.
        Stores configuration in ``config_string`` for use by other methods.

        Initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import configuration_parser
        >>> configuration_parser is not None
        True

        Args:
            config_string: Config string to use.
        """
        self.config_string = config_string

    def parse(self):
        """Return the parse.

        Interprets raw data and returns structured results.


        >>> from PyICe.plugins.bench_configuration_management.bench_configuration_management import configuration_parser
        >>> hasattr(configuration_parser, 'parse')
        True

        Returns:
            The parsed data structure.
        """
        connections = []
        for conn in self.config_string.split(
                "\n")[:-1]:  # last one is always an empty line
            connection = {}
            connection["comp0"], connection["term0"] = conn.split(ARROW_STRING)[
                0].strip().split(":")
            connection["comp1"], connection["term1"] = conn.split(ARROW_STRING)[
                0].strip().split(":")
            connections.append(connection)
        return connections
