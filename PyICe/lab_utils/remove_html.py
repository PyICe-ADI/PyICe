import re


def remove_html(text):
    """Remove a html."""
    if text is not None:
        re.sub('<[^<]+?>', '', text)
    return text
