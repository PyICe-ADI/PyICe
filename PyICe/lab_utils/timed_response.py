import threading


def timed_input(prompt, timeout):
    '''Prompt the user for input, returning None if no response within timeout seconds.'''
    response = [None]

    def _get_input():
        response[0] = input(prompt)
    thread = threading.Thread(target=_get_input, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        print(f"\nNo response received within {timeout}s. Continuing...")
        return None
    return response[0]
