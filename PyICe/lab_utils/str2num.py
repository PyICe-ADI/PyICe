def str2num(str_in, except_on_error=True):
    if isinstance(str_in,int) or isinstance(str_in,float) or str_in is None:
        return str_in
    if str_in == 'True':
        return True
    if str_in == 'False':
        return False
    try:
        return int(str_in,0) #automatically select base
    except ValueError:
        try:
            return float(str_in)
        except ValueError as e:
            if except_on_error:
                print("string failed to convert both to integer (automatic base selection) and float: {}".format(str))
                raise e
            else:
                #just return original string
                return str_in