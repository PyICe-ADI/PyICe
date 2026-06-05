"""Egg timer utility.

>>> from PyICe.lab_utils.egg_timer import egg_timer

"""
import time


def egg_timer(timeout, message=None, length=30, display_callback=None):
    """Block for a specified duration while displaying a text-based progress bar.

    Useful during long hardware settling times or calibration waits so the
    console does not appear idle.  The progress bar updates at ~10 Hz and shows
    elapsed/remaining time plus a percentage.  An optional *display_callback*
    can append live telemetry (e.g. temperature readings) after the bar.


    >>> from PyICe.lab_utils.egg_timer import egg_timer
    >>> callable(egg_timer)
    True

    Args:
        timeout: Duration to wait, in seconds.
        message: Optional message printed on the line above the progress bar
            before the countdown begins.
        length: Width of the progress bar in characters (default 30).
        display_callback: Optional callable that receives a status dict
            (keys: ``start_time``, ``total_time``, ``elapsed_time``,
            ``remaining_time``, ``percent_complete``, ``message``) and returns
            a string to append after the progress bar on each refresh.
    """
    _light_shade = "▒"  # noqa: F841 - \u2592
    _dark_shade = "█"  # noqa: F841 - \u2588
    digits = len(str(int(timeout)))
    longest_line_len = 0
    status = {}
    status['start_time'] = time.time()
    status['total_time'] = timeout
    status['callback_disp_str'] = ''
    status['elapsed_time'] = 0
    status['message'] = message
    if message is not None:
        print(message)
    while status['elapsed_time'] != status['total_time']:
        status['present_time'] = time.time()
        status['elapsed_time'] = min(
            status['present_time'] -
            status['start_time'],
            status['total_time'])
        status['remaining_time'] = status['total_time'] - \
            status['elapsed_time']
        status['percent_complete'] = status['elapsed_time'] / \
            status['total_time']
        complete_length = int(status['percent_complete'] * length)
        status['dark'] = "█" * complete_length
        status['light'] = "▒" * (length - complete_length)
        if display_callback is not None:
            status['callback_disp_str'] = display_callback(status)
        print_str = "\r║{{dark}}{{light}}║ {{remaining_time:{digits}.0f}}/{{total_time:{digits}.0f}}s remaining. ({{percent_complete:3.1%}}). {{callback_disp_str}}".format(
            digits=digits).format(
            **status)  # ║╠╣
        if len(print_str) < longest_line_len:
            pad = " " * (longest_line_len - len(print_str))
        else:
            pad = ""
            longest_line_len = len(print_str)
        print(print_str + pad, end=' ')
        loop_time = time.time() - status['present_time']
        if loop_time < 0.1:
            time.sleep(0.1 - loop_time)
    print()
