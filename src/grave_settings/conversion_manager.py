# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Callable, Type

from dataclasses import field, dataclass
from ram_util.modules import format_class_str, load_type
from observer_hooks import notify, EventHandler
from ram_util.utilities import generate_type_hierarchy_to_base

from grave_settings import P_VERSION


class ConversionError(Exception):
    pass


def basic_converter(json_obj: dict, mapping: dict, new_ver: str) -> dict:
    new_json_obj = {P_VERSION: new_ver}
    for k, v in mapping.items():
        if k in json_obj:
            new_json_obj[mapping[k]] = json_obj[k]
    return new_json_obj



class ConversionManager:
    __slots__ = 'converters', 'converted'

    def __init__(self):
        # mapping of version to tuple of conversion function and output version
        self.converters: dict[tuple[str, str], tuple[Callable, str]] = {}
        self.converted = EventHandler()

    @classmethod
    def get_version_object(cls, t_obj: Type | object):
        versioning_info = {}
        if hasattr(t_obj, 'get_versioning_endpoint'):
            end_point = t_obj.get_versioning_endpoint()
        else:
            end_point = object
        if type(t_obj) != Type:
            t_obj = t_obj.__class__
        for clt in generate_type_hierarchy_to_base(end_point, t_obj):
            if hasattr(clt, 'VERSION'):
                if clt.VERSION is not None:
                    versioning_info[format_class_str(clt)] = clt.VERSION
        if versioning_info:
            return versioning_info

    def add_converter(self, target_ver, target_class: Type | str, conversion_func, out_ver):
        if type(target_class) is not str:
            target_class = format_class_str(target_class)
        self.converters[(target_class, target_ver)] = (conversion_func, out_ver)

    def try_convert(self, state_obj: dict, class_str: str, ver: str, target_ver: str | None=None):
        version_map = state_obj[P_VERSION]
        search_key = (class_str, ver)
        while (ver != target_ver) and (search_key in self.converters):
            try:
                convert_func, out_version = self.converters[search_key]
            except KeyError:
                raise ConversionError
            if (new_object := convert_func(state_obj)) is not None:
                state_obj = new_object
                self.converted.emit(state_obj, class_str, ver, target_ver=out_version)
            version_map[class_str] = out_version
            ver = out_version
        return state_obj

    def update_to_current(self, json_obj, version_info) -> dict:
        if version_info is None:
            return json_obj
        for class_str, version in version_info.items():
            this_class = load_type(class_str)
            if not version == this_class.VERSION:
                try:
                    json_obj = self.try_convert(json_obj.copy(), class_str, version, target_ver=this_class.VERSION)
                except ConversionError:
                    raise IOError('Settings file version is not understood')

        return json_obj
