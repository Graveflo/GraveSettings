# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Callable, Type

from observer_hooks import EventHandler
from grave_settings.utilities import generate_type_hierarchy_to_base, format_class_str


class ConversionError(Exception):
    pass


def basic_converter(json_obj: dict, mapping: dict) -> dict:
    new_json_obj = {}
    for k, v in mapping.items():
        if k in json_obj:
            new_json_obj[mapping[k]] = json_obj[k]
    return new_json_obj


def get_object_versioning_endpoint(t_obj: Type | object):
    if hasattr(t_obj, 'get_versioning_endpoint'):
        return t_obj.get_versioning_endpoint()
    else:
        return object


def get_descendent_class_formats(t_obj: Type | object, end_point=None) -> set[Type]:
    if end_point is None:
        end_point = get_object_versioning_endpoint(t_obj)
    if not isinstance(t_obj, type):  # meta-classes force use of isinstance for Type[type] checking
        t_obj = t_obj.__class__
    return {format_class_str(c) for c in generate_type_hierarchy_to_base(end_point, t_obj)}


class ConversionManager:
    __slots__ = 'converters', 'converted'

    def __init__(self):
        # mapping of version to tuple of conversion function and output version
        self.converters: dict[tuple[str, str], tuple[Callable, str]] = {}
        self.converted = EventHandler()

    @classmethod
    def get_version_info_from_class(cls, clt: Type):
        v = None
        if hasattr(clt, 'get_version'):
            v = clt.get_version()
        elif hasattr(clt, 'VERSION'):
            v = clt.VERSION
        return v

    @classmethod
    def get_version_object(cls, t_obj: Type | object):
        versioning_info = {}
        if hasattr(t_obj, 'get_versioning_endpoint'):
            end_point = t_obj.get_versioning_endpoint()
        else:
            end_point = object
        if not isinstance(t_obj, type):  # meta-classes force use of isinstance for Type[type] checking
            t_obj = t_obj.__class__
        for clt in generate_type_hierarchy_to_base(end_point, t_obj):
            if (v := cls.get_version_info_from_class(clt)) is not None:
                versioning_info[format_class_str(clt)] = v
        if versioning_info:
            return versioning_info

    def add_converter(self, target_ver, target_class: Type | str, conversion_func, out_ver):
        if type(target_class) is not str:
            target_class = format_class_str(target_class)
        self.converters[(target_class, target_ver)] = (conversion_func, out_ver)

    def try_convert(self, state_obj: dict, class_str: str, ver: str, target_ver: str):
        search_key = (class_str, ver)
        while (ver != target_ver) and (search_key in self.converters):
            try:
                convert_func, out_version = self.converters[search_key]
            except KeyError:
                raise ConversionError('Settings version info object is not understood')
            if (new_object := convert_func(state_obj)) is not None:
                state_obj = new_object
                self.converted.emit(state_obj, class_str, ver, target_ver=out_version)
            ver = out_version
            search_key = (class_str, ver)
        return state_obj

    def update_to_current(self, json_obj, load_type: Callable[[str], Type], version_info) -> dict:
        if version_info is None:
            return json_obj
        for class_str, version in version_info.items():
            this_class = load_type(class_str)
            if not version == (target_ver := self.get_version_info_from_class(this_class)):
                json_obj = self.try_convert(json_obj.copy(), class_str, version, target_ver)
        return json_obj
