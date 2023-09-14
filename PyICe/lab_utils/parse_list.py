import ast

def parse_list(string_list):
    if type(string_list) is not type(""):
        raise Exception(f"\n\nlab_utils: Attempt to parse a list that isn't a string: {string_list}\n\n")
    return ast.literal_eval(string_list)