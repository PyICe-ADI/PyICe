def present_menu(intro_msg, prompt_msg, item_list):
    """Command-line interface. Presents item_list as a menu to the user, and prompts for a choice.
    For example:

        sweep_dac = dac_type(name="AD5693R DAC", bits=16, input_channel_name="sweep_dac", output_meter_channel_name="sweep_dac_meter")
        epot = dac_type(name="CAT5140 ePot", bits=8, input_channel_name="scale_epot_code", output_meter_channel_name="scale_meter")
        hameg = source_type(name="Hameg bench supply", min=0.0, max=32.0, input_channel_name="hameg", output_meter_channel_name="vtest_meter")
        bipdac = dac_type(name="8-bit bipolar DAC", bits=8, input_channel_name="val", output_meter_channel_name="bipdac_meter", bipolar=True)

        choice = present_menu(intro_msg="I can force the SCALE ADC input using the following:",
                              prompt_msg="What method should I use?",
                              item_list=[bipdac, epot, hameg, sweep_dac])

    prints the following:

        I can force the SCALE ADC input using the following:
           0: 8-bit bipolar DAC
           1: CAT5140 ePot
           2: Hameg bench supply
           3: AD5693R DAC
        What method should I use?

    The menu items are formatted as <item #>: <str(item)>
    so it is important that each item in item_list has a descriptive __str__() method.

    Returns the chosen item from item_list.
    """
    assert hasattr(item_list, "__getitem__") and hasattr(item_list, "__len__")
    assert len(item_list) > 0 and hasattr(item_list[0], "__str__")
    while True:
        print(intro_msg)
        for item_num in range(len(item_list)):
            print(" {:>3d}: {}".format(item_num, item_list[item_num]))
        prompt = prompt_msg if prompt_msg[-1]==" " else prompt_msg + " "
        try:
            item_num = int(input(prompt))
            return item_list[item_num]
        except (IndexError, ValueError):
            print()
            print("Please choose amongst the given choices, 0-{}.".format(len(item_list)-1))