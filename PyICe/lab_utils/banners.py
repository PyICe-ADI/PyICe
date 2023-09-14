def print_banner(*message, offset=1, length=80):
    print(build_banner(*message, offset=offset, length=length))
    
def build_banner(*message, offset=1, length=80):
    ret_str=u"\u250c" + u"\u2500" * (length-2) + u"\u2510\n"
    for line in message:
        ret_str+=u"\u2502" + " " * offset + line + " " * ((length-2-offset) - len(line)) + u"\u2502\n"
    ret_str+=u"\u2514" + u"\u2500" * (length-2) + u"\u2518"
    return ret_str