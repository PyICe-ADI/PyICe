"""Present menu utility."""
def present_menu(intro_msg, prompt_msg, item_list):
    """Print a numbered menu on stdout and return the item the user selects.

    Useful for interactive bench scripts where the operator must choose among
    hardware configurations, sweep sources, or test modes at run-time.
    Each item is printed as ``<index>: <str(item)>``, so every element in
    *item_list* should have a descriptive ``__str__`` method.

    Example output::

        I can force the SCALE ADC input using the following:
           0: 8-bit bipolar DAC
           1: CAT5140 ePot
           2: Hameg bench supply
           3: AD5693R DAC
        What method should I use?

    The user types an index number; invalid input re-displays the menu.

    Args:
        intro_msg: Explanatory text printed before the numbered list.
        prompt_msg: Question printed after the list to solicit user input.
            A trailing space is added automatically if absent.
        item_list: Indexable sequence of objects to choose from (must
            support ``__getitem__``, ``__len__``, and ``__str__`` on
            elements).

    Returns:
        The element of *item_list* corresponding to the index the user
        entered.
    """
    assert hasattr(item_list, "__getitem__") and hasattr(item_list, "__len__")
    assert len(item_list) > 0 and hasattr(item_list[0], "__str__")
    while True:
        print(intro_msg)
        for item_num in range(len(item_list)):
            print(" {:>3d}: {}".format(item_num, item_list[item_num]))
        prompt = prompt_msg if prompt_msg[-1] == " " else prompt_msg + " "
        try:
            item_num = int(input(prompt))
            return item_list[item_num]
        except (IndexError, ValueError):
            print()
            print(
                "Please choose amongst the given choices, 0-{}.".format(len(item_list) - 1))
