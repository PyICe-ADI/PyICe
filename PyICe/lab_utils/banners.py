def print_banner(*message, offset=1, length=80):
    print(build_banner(*message, offset=offset, length=length))
    
def build_banner(*message, offset=1, length=80):
    upper_left = u"\u250c"
    bar = u"\u2500"
    upper_right = u"\u2510"
    lower_left = u"\u2514"
    lower_right = u"\u2518"
    wall = u"\u2502"
    
    ret_str=f'{upper_left}{bar * (length-2)}{upper_right}\n'
    for line in message:
        ret_str+=f'{wall}{" " * offset}{str(line)}{" " * ((length-2-offset) - len(str(line)))}{wall}\n'
    ret_str+=f'{lower_left}{bar * (length-2)}{lower_right}'
    return ret_str