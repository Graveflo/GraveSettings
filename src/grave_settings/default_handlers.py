# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from types import NoneType
from datetime import timedelta, datetime, date
from enum import Enum
from typing import Type, Mapping
from types import FunctionType
from collections.abc import Iterable

from ram_util.modules import format_class_str
from ram_util.utilities import OrderedHandler
from grave_settings.abstract import Serializable, IASettings
from grave_settings.fmt_util import Route, KeySerializableDict, PreservedReference


class NotJsonSerializableException(Exception):
    pass


class JsonSerializationHandler(OrderedHandler):
    def __init__(self, *args, **kwargs):
        super(JsonSerializationHandler, self).__init__(*args, **kwargs)
        self._handle_default = self.handle_pyobj

    def init_handler(self):
        super(JsonSerializationHandler, self).init_handler()
        self.add_handlers({  # This only works because dictionaries preserve order! Be careful order matters here
            Type: self.handle_type,
            NoneType: self.handle_NoneType,
            Iterable: self.handle_Iterable,
            Mapping: self.handle_Mapping,
            FunctionType: self.handle_function_type,
            PreservedReference: self.handle_PreservedReference,
            KeySerializableDict: self.handle_KeySerializableDict,
            Serializable: self.handle_serializable,
            date: self.handle_date,
            datetime: self.handle_datetime,
            timedelta: self.handle_timedelta,
            Enum: self.handle_Enum
        })

    def handle_Enum(self, key: Enum, route: Route, *args, **kwargs):
        return {
            'state': key.name
        }

    def handle_PreservedReference(self, key: PreservedReference, route: Route, *args, **kwargs):
        return {
            'ref': key.obj_ref
        }

    def handle_Iterable(self, key: Iterable, route: Route, *args, **kwargs):
        return list(key)

    def handle_Mapping(self, key: Mapping, route: Route, *args, **kwargs):
        return {k: key[k] for k in key}

    def handle_KeySerializableDict(self, key: KeySerializableDict, route: Route, *args, **kwargs):
        return {
            'kvps': list(x for x in key.wrapped_dict.items())
        }

    def handle_type(self, key: Type, route: Route, *args, **kwargs):
        return {
            'state': format_class_str(key)
        }

    def handle_function_type(self, key: Type, route: Route, *args, **kwargs):
        route.set_obj_class_str('types.FunctionType')
        return {
            'state': format_class_str(key)
        }

    def handle_NoneType(self, key: NoneType, route: Route, *args, **kwargs):
        route.set_obj_class_str('types.NoneType')
        return dict()

    def handle_serializable(self, key: Serializable, route: Route, *args, **kwargs):
        return key.to_dict(**kwargs)

    def handle_datetime(self, key: datetime, route: Route, *args, **kwargs):
        return {
            'state': [key.year, key.month, key.day, key.hour, key.minute, key.second, key.microsecond]
        }

    def handle_date(self, key: date, route: Route, *args, **kwargs):
        return {
            'state': [key.year, key.month, key.day]
        }

    def handle_timedelta(self, key: timedelta, route: Route, *args, **kwargs):
        return {
            'state': [key.days, key.seconds, key.microseconds]
        }

    def handle_pyobj(self, key, route: Route, *args, **kwargs):
        if hasattr(key, 'to_dict'):
            return self.handle_serializable(key, route, **kwargs)
        else:
            return Serializable.to_dict(key, **kwargs)

