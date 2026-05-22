"""Remove html utility."""
import re


def remove_html(text):
    """Remove a html.

    Args:
        text: Text.

    Returns:
        Result value.
    """
    if text is not None:
        re.sub('<[^<]+?>', '', text)
    return text
