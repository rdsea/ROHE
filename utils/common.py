import traceback,sys

def merge_dict(f_dict, i_dict, prio=False):
    try:
        if isinstance(f_dict, dict) and isinstance(i_dict, dict):
            for key in f_dict:
                if key in i_dict:
                    f_dict[key] = merge_dict(f_dict[key],i_dict[key],prio)
                    i_dict.pop(key)
            f_dict.update(i_dict)
        else:
            if f_dict != i_dict:
                if prio:
                    return f_dict
                else:
                    return i_dict
    except Exception as e:
        print("[ERROR] - Error {} in merge_dict: {}".format(type(e),e.__traceback__))
        traceback.print_exception(*sys.exc_info())
    return f_dict