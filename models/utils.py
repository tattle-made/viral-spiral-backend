import json
from datetime import datetime
from playhouse.shortcuts import model_to_dict as mtd_original

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def model_to_dict(obj):
    """Handles datetime objects for easy JSON conversions"""
    if isinstance(obj, dict):
        dict_ = obj
    else:
        dict_ = mtd_original(obj)
    for key in dict_.keys():
        if isinstance(dict_[key], datetime):
            dict_[key] = dict_[key].strftime(DATE_FORMAT)
        elif isinstance(dict_[key], dict):
            dict_[key] = model_to_dict(dict_[key])
    return dict_
