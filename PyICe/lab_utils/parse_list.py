import ast

def parse_list(string_list):
    '''Parse a string representation of a list using ast.literal_eval.

    >>> parse_list('[1, 2, 3]')
    [1, 2, 3]
    >>> parse_list("['a', 'b']")
    ['a', 'b']
    >>> parse_list('[[1, 2], [3, 4]]')
    [[1, 2], [3, 4]]
    '''
    if type(string_list) is not type(""):
        raise Exception(f"\n\nlab_utils: Attempt to parse a list that isn't a string: {string_list}\n\n")
    return ast.literal_eval(string_list)