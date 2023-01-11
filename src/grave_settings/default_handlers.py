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

from ram_util.modules import format_class_str, load_type
from grave_settings.handlers import OrderedHandler
from grave_settings.abstract import Serializable, Route
from grave_settings.helper_objects import KeySerializableDict, PreservedReference


class NotSerializableException(Exception):
    pass


class SerializationHandler(OrderedHandler):
    def init_handler(self):
        super(SerializationHandler, self).init_handler()
        self.add_handlers({  # This only works because dictionaries preserve order! Be careful order matters here
            Type: self.handle_type,
            NoneType: self.handle_NoneType,
            Iterable: self.handle_Iterable,
            Mapping: self.handle_Mapping,
            FunctionType: self.handle_function_type,
            PreservedReference: self.handle_PreservedReference,
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
            'ref': key.ref
        }

    def handle_Iterable(self, key: Iterable, route: Route, *args, **kwargs):
        return {
            'state': route.formatter_settings.temporary(list(key))
        }

    def handle_Mapping(self, key: Mapping, route: Route, *args, **kwargs):
        return {k: key[k] for k in key}

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
        return key.to_dict(route, **kwargs)

    def handle_datetime(self, key: datetime, route: Route, *args, **kwargs):
        t = route.formatter_settings.temporary
        return {
            'state': t([key.year, key.month, key.day, key.hour, key.minute, key.second, key.microsecond])
        }

    def handle_date(self, key: date, route: Route, *args, **kwargs):
        t = route.formatter_settings.temporary
        return {
            'state': t([key.year, key.month, key.day])
        }

    def handle_timedelta(self, key: timedelta, route: Route, *args, **kwargs):
        t = route.formatter_settings.temporary
        return {
            'state': t([key.days, key.seconds, key.microseconds])
        }

    # noinspection PyMethodOverriding
    def default_handler(self, key, route: Route, *args, **kwargs):
        if hasattr(key, 'to_dict'):
            return self.handle_serializable(key, route, **kwargs)
        else:
            return Serializable.to_dict(key, route, **kwargs)

    # noinspection PyMethodOverriding
    def handle(self, key, route: Route, *args, **kwargs):
        route.obj_type_str = format_class_str(key.__class__)
        return route.formatter_settings.temporary(super().handle(key, route, *args, **kwargs))


class DeSerializationHandler(OrderedHandler):
    def __init__(self, *args, **kwargs):
        super(DeSerializationHandler, self).__init__(*args, **kwargs)

    def init_handler(self):
        super(DeSerializationHandler, self).init_handler()
        self.add_handlers({
            Type: self.handle_type,
            NoneType: self.handle_NoneType,
            tuple: self.handle_tuple,
            set: self.handle_set,
            PreservedReference: self.handle_PreservedReference,
            FunctionType: self.handle_type,
            Serializable: self.handle_serializable,
            KeySerializableDict: self.handle_KeySerializableDict,
            date: self.handle_date,
            datetime: self.handle_datetime,
            timedelta: self.handle_timedelta,
            Enum: self.handle_Enum
        })

    def handle_Enum(self, t_object: Type[Enum], json_obj: dict, route: Route, **kwargs):
        return t_object[json_obj['state']]

    def handle_NoneType(self, t_object: Type[NoneType], *args, **kwargs):
        return None

    def handle_PreservedReference(self, t_object: Type[PreservedReference], json_obj: dict, route: Route, **kwargs):
        return t_object(ref=json_obj['ref'])

    def handle_KeySerializableDict(self, t_object: Type[KeySerializableDict], json_obj: dict, route: Route, **kwargs):
        ksd = t_object(None)
        ksd.from_dict(json_obj, route)
        return ksd.wrapped_dict

    def handle_tuple(self, t_object: Type[tuple], json_obj: dict, route: Route, **kwargs):
        return tuple(json_obj['state'])

    def handle_set(self, t_object: Type[set], json_obj: dict, route: Route, **kwargs):
        return set(json_obj['state'])

    def handle_type(self, t_object: Type[Type], json_obj: dict, route: Route, **kwargs):
        return load_type(json_obj['state'])

    def handle_serializable(self, t_object: Type[Serializable], json_obj: dict, route: Route, **kwargs) -> Serializable:
        settings_obj = t_object()
        settings_obj.from_dict(json_obj, route, **kwargs)
        return settings_obj

    def handle_datetime(self, t_object: Type[datetime], json_obj: dict, route: Route, **kwargs) -> datetime:
        obs = json_obj['state']
        return t_object(year=obs[0], month=obs[1], day=obs[2], hour=obs[3], minute=obs[4], second=obs[5],
                        microsecond=obs[6])

    def handle_date(self, t_object: Type[date], json_obj: dict, route: Route, **kwargs) -> date:
        obs = json_obj['state']
        return t_object(year=obs[0], month=obs[1], day=obs[2])

    def handle_timedelta(self, t_object: Type[timedelta], json_obj: dict, route: Route, **kwargs) -> timedelta:
        obs = json_obj['state']
        return t_object(days=obs[0], seconds=obs[1], microseconds=obs[2])

    # noinspection PyMethodOverriding
    def default_handler(self, t_object: Type, json_obj: dict, route: Route, **kwargs):
        if hasattr(t_object, 'from_dict'):
            # noinspection PyTypeChecker
            return self.handle_serializable(t_object, json_obj, route, **kwargs)  # this is duck typed
        else:
            settings_obj = t_object()
            Serializable.from_dict(settings_obj, json_obj, route)
            return settings_obj

    def handle_node(self, key, *args, **kwargs):
        f = self.get_key_func(key)  # this overrides the superclass's expectation of an object not a type
        return f(key, *args, handler=self, **kwargs)
