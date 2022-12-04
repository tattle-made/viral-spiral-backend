import json
from datetime import datetime
from peewee import ModelSelect, Model
from playhouse.shortcuts import model_to_dict as mtd_original

DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def model_to_dict(obj, **kwargs):
    """Handles datetime objects for easy JSON conversions. Passes kwargs
    to peewee's model to dict func"""
    if isinstance(obj, dict):
        dict_ = obj
    elif isinstance(obj, Model):
        if hasattr(obj, "to_dict"):
            dict_ = obj.to_dict(**kwargs)
        else:
            dict_ = mtd_original(obj, **kwargs)
    else:
        return obj
    for key in dict_.keys():
        if isinstance(dict_[key], datetime):
            dict_[key] = dict_[key].strftime(DATE_FORMAT)
        elif isinstance(dict_[key], dict):
            dict_[key] = model_to_dict(dict_[key])
        elif isinstance(dict_[key], list):
            dict_[key] = [model_to_dict(x) for x in dict_[key]]
        elif isinstance(dict_[key], ModelSelect):
            dict_[key] = [model_to_dict(x) for x in dict_[key]]
    return dict_
