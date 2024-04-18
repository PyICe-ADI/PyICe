if __name__ == '__main__':
    from PyICe.bench_configuration_management import bench_configuration_management, lab_components

    test_components = bench_configuration_management.component_collection()
    test_connections = bench_configuration_management.connection_collection(name="test_connections")
    test_components.add_component(lab_components.Agilent_3497x("AGILENT_3497x"))
    test_components.add_component(lab_components.Agilent_34908A("AGILENT_34908A"))
    test_connections.add_connection(test_components.get_components()["AGILENT_3497x"]["BAY1"], test_components.get_components()["AGILENT_34908A"]["BAY"])

    from PyICe import lab_core
    meta_master = lab_core.channel_master()
    meta_master.add_channel_dummy('bench_connections')
    mlogger = lab_core.logger(meta_master)
    mlogger.new_table(table_name='meta_table', replace_table=True)
    mlogger.write("bench_connections", test_connections.get_readable_connections())
    mlogger.log()

    print(test_connections.print_connections())

    from PyICe.bench_configuration_management import bench_visualizer
    from PyICe.tutorials.bench_config_management_tutorial.bench_image_example import visualizer_locations
    visualizer = bench_visualizer.visualizer(connections=test_connections.connections, locations=visualizer_locations.component_locations().locations)
    visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')
