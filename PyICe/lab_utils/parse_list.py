"""Parse list utility."""
import ast


def parse_list(string_list):
    """Safely convert a string-encoded Python list literal back into a list.

    Uses ``ast.literal_eval`` so only literal structures (numbers, strings,
    tuples, lists, dicts, booleans, None) are accepted — no arbitrary code
    execution. Commonly used to deserialize list-valued fields read from CSV
    or SQLite text columns.

    >>> parse_list('[1, 2, 3]')
    [1, 2, 3]
    >>> parse_list("['a', 'b']")
    ['a', 'b']
    >>> parse_list('[[1, 2], [3, 4]]')
    [[1, 2], [3, 4]]
    >>> parse_list('[True, None, 3.14]')
    [True, None, 3.14]

    Args:
        string_list: A string containing a valid Python list literal.

    Raises:
        Exception: If the argument is not a string.
        ValueError: If the string is not a valid Python literal (from ast).
    """
    if type(string_list) is not type(""):
        raise Exception(
            f"\n\nlab_utils: Attempt to parse a list that isn't a string: {string_list}\n\n")
    return ast.literal_eval(string_list)
