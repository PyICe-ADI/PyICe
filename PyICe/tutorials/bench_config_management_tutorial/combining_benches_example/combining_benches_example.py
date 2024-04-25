from PyICe.bench_configuration_management   import bench_configuration_management, lab_components


if __name__ == "__main__":

    # ~~~~~~~~~~~~~~~~~~~ Mock User #1 File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    def configure_bench1(components, connections):
        connections.add_connection(components["AGILENT_3497x"]["BAY1"],             components["AGILENT_34908A"]["BAY"])
        connections.add_connection(components["AGILENT_3497x"]["BAY2"],             components["AGILENT_34901A_2"]["BAY"])
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



    # ~~~~~~~~~~~~~~~~~~~ Mock User #2 File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    def configure_bench2(components, connections):
        connections.add_connection(components["AGILENT_3497x"]["BAY1"],             components["AGILENT_34908A"]["BAY"])
        connections.add_connection(components["AGILENT_3497x"]["BAY3"],             components["AGILENT_34901A_3"]["BAY"])

    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # ~~~~~~~~~~~~~~~~~~~ Mock User #3 File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    def configure_bench3(components, connections):
        connections.block_connection(components["AGILENT_3497x"]["BAY2"])
        connections.add_connection(components["CONFIGURATORXT"]["POWER1_MEAS"],     components["AGILENT_34901A_2"]["DIFF_1-4"])
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # ~~~~~~~~~~~~~~~~~~~ Mock Infrastructure Setup File ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #
    #
    bench_components = bench_configuration_management.component_collection()
    bench_components.add_component(lab_components.Agilent_3497x("AGILENT_3497x"))
    bench_components.add_component(lab_components.Agilent_34901A("AGILENT_34901A_2"))
    bench_components.add_component(lab_components.Agilent_34901A("AGILENT_34901A_3"))
    bench_components.add_component(lab_components.Agilent_34908A("AGILENT_34908A"))
    bench_components.add_component(lab_components.ConfiguratorXT("CONFIGURATORXT"))
    components_dict = bench_components.get_components()
    all_connections = {}
    ### SUCCESS!
    for configure_bench in [configure_bench1, configure_bench2]:
        connection_collection = bench_configuration_management.connection_collection(name=type(configure_bench).__name__)
        configure_bench(components_dict, connection_collection)
        all_connections[configure_bench] = connection_collection
    connections = bench_configuration_management.connection_collection.distill(all_connections.values())
    diagram = connections.print_connections()
    print("Bench 1 and 2")
    print(diagram)
    
    ### CONFLICT!
    all_connections2 = {}
    for configure_bench in [configure_bench1, configure_bench2, configure_bench3]:
        connection_collection = bench_configuration_management.connection_collection(name=type(configure_bench).__name__)
        configure_bench(components_dict, connection_collection)
        all_connections2[configure_bench] = connection_collection
    try:
        connections = bench_configuration_management.connection_collection.distill(all_connections2.values())
    except Exception as e:
        print("Bench 1, 2, and 3")
        print(e)
    #
    #
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~