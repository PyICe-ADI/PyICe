import time

def egg_timer(timeout, message=None, length=30, display_callback=None):
    '''Provides a blocking delay with a graphic to indicate progress so far so the computer doesn't look idle
    optionally, display a message on the line above the timer graphic
    optionally, specify a display_callback function to insert extra progress information after the timer display.
    display_callback function should accept a single dictionary argument and return a string.'''
    light_shade = "▒" #\u2592
    dark_shade = "█" #\u2588
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
        status['elapsed_time'] = min(status['present_time'] - status['start_time'], status['total_time'])
        status['remaining_time'] = status['total_time'] - status['elapsed_time']
        status['percent_complete'] = status['elapsed_time'] / status['total_time']
        complete_length = int(status['percent_complete'] * length)
        status['dark'] = "█" * complete_length
        status['light'] = "▒" * (length-complete_length)
        if display_callback is not None:
            status['callback_disp_str'] = display_callback(status)
        print_str =  "\r║{{dark}}{{light}}║ {{remaining_time:{digits}.0f}}/{{total_time:{digits}.0f}}s remaining. ({{percent_complete:3.1%}}). {{callback_disp_str}}".format(digits=digits).format(**status) #║╠╣
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