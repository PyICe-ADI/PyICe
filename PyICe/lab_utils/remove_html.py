"""Remove html utility.

>>> from PyICe.lab_utils.remove_html import remove_html

"""
import re


def remove_html(text):
    """Strip HTML/XML tags from a string, returning only the text content.

    Useful for cleaning up instrument responses or log entries that contain
    embedded HTML markup.

    >>> remove_html('<b>bold</b>')
    'bold'
    >>> remove_html('no tags here')
    'no tags here'
    >>> remove_html('<a href="x">link</a> text')
    'link text'
    >>> remove_html(None) is None
    True

    Args:
        text: Input string possibly containing HTML tags, or None.

    Returns:
        The input with all HTML tags removed, or None if input was None.
    """
    if text is not None:
        text = re.sub('<[^<]+?>', '', text)
    return text
