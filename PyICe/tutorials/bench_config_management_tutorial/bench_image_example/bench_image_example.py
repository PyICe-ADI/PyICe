from PyICe.bench_configuration_management   import bench_configuration_management, bench_visualizer, lab_components
from PyICe.tutorials.bench_config_management_tutorial.bench_image_example import visualizer_locations

if __name__ == "__main__":
    components = bench_configuration_management.component_collection()
    ##############################################################################################
    #                                                                                            #
    # General Purpose Lab Equipment                                                              #
    #                                                                                            #
    ##############################################################################################
    components.add_component(lab_components.ConfiguratorXT("CONFIGURATORXT"))
    components.add_component(lab_components.Agilent_3497x("AGILENT_3497x"))
    components.add_component(lab_components.Agilent_34901A("AGILENT_34901A_2"))
    components.add_component(lab_components.Agilent_34901A("AGILENT_34901A_3"))
    components.add_component(lab_components.Agilent_34908A("AGILENT_34908A"))
    components.add_component(lab_components.four_channel_power_supply("HAMEG"))
    components.add_component(lab_components.HTX9000("HTX9000_ILOAD0"))
    components.add_component(lab_components.HTX9000("HTX9000_ILOAD1"))
    components.add_component(lab_components.HTX9000("HTX9000_ILOAD2"))
    components.add_component(lab_components.HTX9000("HTX9000_ILOAD3"))
    components.add_component(lab_components.HTX9000("HTX9000_ILOAD4"))
    components.add_component(lab_components.BK8500("BK8500_ILOAD0"))
    components.add_component(lab_components.BK8500("BK8500_ILOAD1"))
    components.add_component(lab_components.BK8500("BK8500_ILOAD2"))
    compos = components.get_components()

    test_connections = bench_configuration_management.connection_collection("bench_image_example")
    test_connections.add_connection(compos["AGILENT_3497x"]["BAY1"],             compos["AGILENT_34908A"]["BAY"])
    test_connections.add_connection(compos["AGILENT_3497x"]["BAY2"],             compos["AGILENT_34901A_2"]["BAY"])
    test_connections.add_connection(compos["AGILENT_3497x"]["BAY3"],             compos["AGILENT_34901A_3"]["BAY"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER1_MEAS"],     compos["AGILENT_34901A_2"]["DIFF_1-4"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER2_MEAS"],     compos["AGILENT_34901A_2"]["DIFF_5-8"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER3_MEAS"],     compos["AGILENT_34901A_2"]["DIFF_9-12"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER5_MEAS"],     compos["AGILENT_34901A_2"]["DIFF_13-16"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER6_MEAS"],     compos["AGILENT_34901A_2"]["DIFF_17-20"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER7_MEAS"],     compos["AGILENT_34901A_3"]["DIFF_1-4"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER8_MEAS"],     compos["AGILENT_34901A_3"]["DIFF_5-8"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["MEAS_A"],          compos["AGILENT_34908A"]["SINGLE_1-8"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["MEAS_B"],          compos["AGILENT_34901A_3"]["DIFF_9-12"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["MEAS_C"],          compos["AGILENT_34908A"]["SINGLE_9-16"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["DZ"],              compos["AGILENT_34908A"]["DZ"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER1"],          compos["HAMEG"]["VOUT1"])
    test_connections.add_connection(compos["CONFIGURATORXT"]["POWER8"],          compos["HAMEG"]["VOUT2"])

    print(test_connections.print_connections())

    visualizer = bench_visualizer.visualizer(connections=test_connections.connections, locations=visualizer_locations.component_locations().locations)
    visualizer.generate(file_base_name="Bench_Config", prune=True, file_format='svg', engine='neato')
