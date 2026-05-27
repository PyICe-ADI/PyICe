"""Select string menu utility."""
from curses import panel
import curses


def select_string_menu(header, items):
    """Display a curses-based interactive menu and return the user's selection.

    Presents *items* in a terminal window with arrow-key navigation and
    Enter to confirm. Lists longer than 25 items are automatically paginated
    with *back* / *more* navigation entries. Selecting *exit* (always last
    on the final page) returns ``None``.

    Used by the ProjectCreatorWizard and other interactive CLI tools to let
    the user pick from a dynamic list without typing.

    Args:
        header: Descriptive text displayed above the menu items.
        items: Sequence of selectable values. Each item is rendered via
            its ``str()`` representation.

    Returns:
        The chosen item from *items*, or ``None`` if the list is empty or
        the user selects *exit*.
    """
    if len(items) == 0:
        print('No items to select from. Returning None')
        return None
    if len(items) == 1:
        print(f'Only one item presented. Returning {items[0]}')
        return items[0]
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    window = stdscr.subwin(0, 0)
    window.keypad(True)
    panel2 = panel.new_panel(window)
    panel2.hide()
    panel.update_panels()
    position = 0
    pages = []
    for idx in range(len(items)):
        if idx % 25 == 0:
            if idx != 0:
                pages[-1].append('more')
            pages.append([])
            if idx != 0:
                pages[-1].append('back')
            pages[-1].append(items[idx])
        else:
            pages[-1].append(items[idx])
    pages[-1].append('exit')
    page_idx = 0
    panel2.top()
    panel2.show()
    window.clear()

    def close_up_shop(last_items, selected_position):
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()
        if selected_position == len(last_items) - 1:
            return None
        else:
            return items[selected_position]

    while True:
        active_list = pages[page_idx]
        window.refresh()
        window.addstr(0, 1, header, curses.A_NORMAL)
        curses.curs_set(0)
        for index, item in enumerate(active_list):
            if index == position:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            msg = f"{item}"
            window.addstr(2 + index, 1, msg, mode)
        key = window.getch()
        if key in [curses.KEY_ENTER, ord("\n")]:
            if len(pages) == 1:
                return close_up_shop(active_list, position)
            if (active_list != pages[-1]) and (
                    position == len(active_list) - 1):
                page_idx += 1
                position = 0
                window.clear()
            elif active_list != pages[0] and position == 0:
                page_idx -= 1
                window.clear()
            else:
                return close_up_shop(active_list, position)
        elif key == curses.KEY_UP:
            position += -1
        elif key == curses.KEY_DOWN:
            position += 1
        if position < 0:
            position = 0
        elif position >= len(active_list):
            position = len(active_list) - 1


if __name__ == "__main__":

    x = select_string_menu('How ya doing, buddy?',
                           ['Not too shabby.',
                            'Fine and dandy.',
                            'Fit as a fiddle and ready for love.',
                            3,
                            4,
                            5,
                            6,
                            7,
                            8,
                            9,
                            1,
                            1,
                            1,
                            1,
                            1,
                            1,
                            1,
                            1,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2,
                            2])
    breakpoint()
