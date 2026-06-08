"""Timed response utility.

>>> from PyICe.lab_utils.timed_response import timed_input

"""
import threading


def timed_input(prompt, timeout):
    """Prompt the user for input, returning ``None`` if no response within *timeout* seconds.

    Useful for automated test scripts that should continue unattended when an
    operator is not present.  A daemon thread waits for ``input()``, and if the
    thread does not finish within the timeout a message is printed and ``None``
    is returned.


    >>> from PyICe.lab_utils.timed_response import timed_input
    >>> callable(timed_input)
    True

    Args:
        prompt: Text shown to the user as the input prompt.
        timeout: Maximum seconds to wait for a response before giving up.

    Returns:
        The user's input string, or ``None`` if the timeout expired.
    """
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
