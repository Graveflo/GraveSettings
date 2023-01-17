# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from types import NoneType, MethodType
from datetime import timedelta, datetime, date
from enum import Enum
from typing import Mapping
from types import FunctionType
from functools import partial

from ram_util.modules import format_class_str, load_type, T
from observer_hooks import FunctionStub, EventHandler
from grave_settings.formatter_settings import Temporary, PreservedReference, FormatterContext, NoRef
from grave_settings.handlers import OrderedHandler
from grave_settings.abstract import Serializable
from grave_settings.framestack_context import FrameStackContext
from grave_settings.helper_objects import KeySerializableDict
from grave_settings.semantics import *


def force_instantiate(type_obj: Type[T]) -> T:
    try:
        return type_obj()
    except TypeError:
        return type_obj.__new__(type_obj)


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
            MethodType: self.handle_method,
            PreservedReference: self.handle_PreservedReference,
            Serializable: self.handle_serializable,
            date: self.handle_date,
            datetime: self.handle_datetime,
            timedelta: self.handle_timedelta,
            Enum: self.handle_Enum,
            partial: self.handle_partial,
            bytes: self.handle_bytes,
            FunctionStub: self.omit,
            EventHandler: self.omit
        })

    @staticmethod
    def handle_method(key: MethodType, context: FormatterContext, **kwargs):
        context.add_frame_semantic(OverrideClassString('types.MethodType'))
        return {
            'object': key.__self__,
            'name': key.__name__
        }

    @staticmethod
    def omit(self):
        raise OmitMeError()

    @staticmethod
    def handle_bytes(key: bytes, context: FormatterContext, **kwargs):
        return {
            'hex': key.hex()
        }

    @staticmethod
    def handle_partial(key: partial, context: FormatterContext, **kwargs):
        return {
            'func': NoRef(key.func),
            'args': Temporary(list(key.args)),
            'kwargs': Temporary(key.keywords.copy())
        }

    @staticmethod
    def handle_Enum(key: Enum, context: FormatterContext, **kwargs):
        return {
            'state': key.name
        }

    @staticmethod
    def handle_PreservedReference(key: PreservedReference, context: FormatterContext, **kwargs):
        return {
            'ref': key.ref
        }

    @staticmethod
    def handle_Iterable(key: Iterable, context: FormatterContext, **kwargs):
        return {
            'state': Temporary(list(key))
        }

    @staticmethod
    def handle_Mapping(key: Mapping, context: FormatterContext, **kwargs):
        return {k: key[k] for k in key}

    @staticmethod
    def handle_type(key: Type, context: FormatterContext, **kwargs):
        return {
            'state': format_class_str(key)
        }

    @staticmethod
    def handle_function_type(key: FunctionType, context: FormatterContext, **kwargs):
        if key.__name__ == '<lambda>':
            raise NotSerializableException('lambda functions are not serializable')
        context.add_frame_semantic(OverrideClassString('types.FunctionType'))
        return {
            'state': format_class_str(key)
        }

    @staticmethod
    def handle_NoneType(key: NoneType, context: FormatterContext, **kwargs):
        context.add_frame_semantic(OverrideClassString('types.NoneType'))
        nid = id(None)
        if nid in context.id_cache:
            del context.id_cache[nid]
        return dict()

    @staticmethod
    def handle_serializable(key: Serializable, context: FormatterContext, **kwargs):
        return key.to_dict(context, **kwargs)

    @staticmethod
    def handle_datetime(key: datetime, context: FormatterContext, **kwargs):
        t = Temporary
        return {
            'state': t([key.year, key.month, key.day, key.hour, key.minute, key.second, key.microsecond])
        }

    @staticmethod
    def handle_date(key: date, context: FormatterContext, **kwargs):
        t = Temporary
        return {
            'state': t([key.year, key.month, key.day])
        }

    @staticmethod
    def handle_timedelta(key: timedelta, context: FormatterContext, **kwargs):
        t = Temporary
        return {
            'state': t([key.days, key.seconds, key.microseconds])
        }

    # noinspection PyMethodOverriding
    @staticmethod
    def default_handler(key, context: FormatterContext, **kwargs):
        if hasattr(key, 'to_dict'):
            return SerializationHandler.handle_serializable(key, context, **kwargs)
        else:
            return Serializable.to_dict(key, context, **kwargs)

    # noinspection PyMethodOverriding
    def handle(self, key, context: FormatterContext, **kwargs):
        return Temporary(super().handle(key, context, **kwargs))


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
            MethodType: self.handle_method,
            Serializable: self.handle_serializable,
            KeySerializableDict: self.handle_KeySerializableDict,
            date: self.handle_date,
            datetime: self.handle_datetime,
            timedelta: self.handle_timedelta,
            Enum: self.handle_Enum,
            partial: self.handle_partial,
            bytes: self.handle_bytes
        })

    @staticmethod
    def handle_method(t_object: Type[MethodType], json_obj: dict, context: FrameStackContext, **kwargs):
        return getattr(json_obj['object'], json_obj['name'])

    @staticmethod
    def handle_bytes(t_object: Type[bytes], json_obj: dict, context: FrameStackContext, **kwargs):
        return t_object.fromhex(json_obj['hex'])

    @staticmethod
    def handle_partial(t_object: Type[partial], json_obj: dict, context: FrameStackContext, **kwargs):
        return t_object(json_obj['func'], *json_obj['args'], **json_obj['kwargs'])

    @staticmethod
    def handle_Enum(t_object: Type[Enum], json_obj: dict, context: FrameStackContext, **kwargs):
        return t_object[json_obj['state']]

    @staticmethod
    def handle_NoneType(t_object: Type[NoneType], *args, **kwargs):
        return None

    @staticmethod
    def handle_PreservedReference(t_object: Type[PreservedReference], json_obj: dict, context: FrameStackContext, **kwargs):
        return t_object(ref=json_obj['ref'])

    @staticmethod
    def handle_KeySerializableDict(t_object: Type[KeySerializableDict], json_obj: dict, context: FrameStackContext, **kwargs):
        ksd = t_object(None)
        ksd.from_dict(json_obj, context)
        return ksd.wrapped_dict

    @staticmethod
    def handle_tuple(t_object: Type[tuple], json_obj: dict, context: FrameStackContext, **kwargs):
        return tuple(json_obj['state'])

    @staticmethod
    def handle_set(t_object: Type[set], json_obj: dict, context: FrameStackContext, **kwargs):
        return set(json_obj['state'])

    @staticmethod
    def handle_type(t_object: Type[Type], json_obj: dict, context: FrameStackContext, **kwargs):
        return load_type(json_obj['state'])

    @staticmethod
    def handle_serializable(t_object: Type[Serializable], json_obj: dict, context: FrameStackContext, **kwargs) -> Serializable:
        settings_obj = force_instantiate(t_object)
        settings_obj.from_dict(json_obj, context, **kwargs)
        return settings_obj

    @staticmethod
    def handle_datetime(t_object: Type[datetime], json_obj: dict, context: FrameStackContext, **kwargs) -> datetime:
        obs = json_obj['state']
        return t_object(year=obs[0], month=obs[1], day=obs[2], hour=obs[3], minute=obs[4], second=obs[5],
                        microsecond=obs[6])

    @staticmethod
    def handle_date(t_object: Type[date], json_obj: dict, context: FrameStackContext, **kwargs) -> date:
        obs = json_obj['state']
        return t_object(year=obs[0], month=obs[1], day=obs[2])

    @staticmethod
    def handle_timedelta(t_object: Type[timedelta], json_obj: dict, context: FrameStackContext, **kwargs) -> timedelta:
        obs = json_obj['state']
        return t_object(days=obs[0], seconds=obs[1], microseconds=obs[2])

    @staticmethod
    def default_handler(t_object: Type[T], json_obj: dict, context: FrameStackContext, **kwargs) -> T:
        if hasattr(t_object, 'from_dict'):
            # noinspection PyTypeChecker
            return DeSerializationHandler.handle_serializable(t_object, json_obj, context, **kwargs)  # this is duck typed
        else:
            settings_obj = force_instantiate(t_object)
            Serializable.from_dict(settings_obj, json_obj, context)
            return settings_obj

    def handle_node(self, key, *args, **kwargs):
        f = self.get_key_func(key)  # this overrides the superclass's expectation of an object not a type
        return f(key, *args, **kwargs)
