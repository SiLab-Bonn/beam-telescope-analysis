import logging
import time
from functools import wraps

import tables as tb

from beam_telescope_analysis import __version__


# Python 3 compatibility
try:
    basestring
except NameError:
    basestring = str


class NameValue(tb.IsDescription):
    name = tb.StringCol(256, pos=0)
    value = tb.StringCol(4 * 1024, pos=1)


def save_configuration_dict(output_file, table_name, dictionary, date_created=None, **kwargs):
    '''Stores any configuration dictionary to HDF5 file.

    Parameters
    ----------
    output_file : string, file
        Filename of the output pytables file or file object.
    table_name : str
        The name will be used as table name.
    dictionary : dict
        A dictionary with key/value pairs.
    date_created : float, time.struct_time
        If None (default), the local time is used.
    '''
    def save_conf():
        try:
            h5_file.remove_node(h5_file.root.configuration, name=table_name)
        except tb.NodeError:
            pass
        try:
            configuration_group = h5_file.create_group(h5_file.root, "configuration")
        except tb.NodeError:
            configuration_group = h5_file.root.configuration

        scan_param_table = h5_file.create_table(configuration_group, name=table_name, description=NameValue, title=table_name)
        row_scan_param = scan_param_table.row
        for key, value in dictionary.items():
            row_scan_param['name'] = key
            row_scan_param['value'] = str(value)
            row_scan_param.append()
        if isinstance(date_created, float):
            scan_param_table.attrs.date_created = time.asctime(time.localtime(date_created))
        elif isinstance(date_created, time.struct_time):
            time.asctime(date_created)
        else:
            scan_param_table.attrs.date_created = time.asctime()
        scan_param_table.attrs.bta_version = __version__
        scan_param_table.flush()

    if isinstance(output_file, tb.file.File):
        h5_file = output_file
        save_conf()
    else:
        mode = kwargs.pop("mode", "a")
        with tb.open_file(output_file, mode=mode, **kwargs) as h5_file:
            save_conf()


def save_arguments(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        curr_time = time.time()
        output_file = func(*args, **kwargs)
        func_name = func.func_name
        if isinstance(output_file, basestring):
            all_parameters = func.func_code.co_varnames[:func.func_code.co_argcount]
            all_kwargs = dict(zip(all_parameters, args))
            all_kwargs.update(kwargs)
            save_configuration_dict(output_file=output_file, table_name=func_name, dictionary=all_kwargs, date_created=curr_time, mode="a")
        else:
            logging.warning("Value returned by \"%s()\" is not a string. Arguments were not saved." % func_name)
        return output_file
    return wrapper
