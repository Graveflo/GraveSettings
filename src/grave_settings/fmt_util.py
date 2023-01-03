# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Self, Callable

from observer_hooks import notify
from ram_util.modules import format_class_str
from ram_util.utilities import OrderedHandler


class PreservedReferenceNotDissolvedError(Exception):
    pass


class KeySerializableDict:
    __slots__ = 'wrapped_dict',

    def __init__(self, wrapped_dict: dict):
        self.wrapped_dict = wrapped_dict


class PreservedReference(object):
    __slots__ = 'ref_obj', 'obj_ref'

    def __init__(self, ref_obj: None | object = None, obj_ref = None):
        if obj_ref is None:
            obj_ref = id(ref_obj)
        self.obj_ref = obj_ref
        self.ref_obj = ref_obj

    def __hash__(self):
        return hash(id(self.ref_obj))

    def detonate(self):
        raise PreservedReferenceNotDissolvedError()


class ConfigFileReference:
    def __init__(self, config):
        self.config = config


class Route:
    #__slots__ = 'key_path', 'logical_path', 'id_cache', 'handler', '_finalize'

    def __init__(self, handler):
        self.key_path = []
        self.obj_type_str = None
        self.logical_path: str | None = None
        self.id_cache: dict[int, object] = {}
        self.handler: OrderedHandler = handler

    def new(self) -> Self:
        return self.__class__(self.handler)

    def branch(self, obj=None, path=None, logical=None):
        r = self.new()
        r.id_cache = self.id_cache
        r.key_path = self.key_path
        if obj is not None:
            self.obj_type_str = format_class_str(obj.__class__)
        if path is not None:
            r.key_path.append(path)
        return r

    @notify(no_origin=True, pass_ref=True)
    def finalize(self):
        pass

    def set_obj_class_str(self, class_str:str):
        self.obj_type_str = class_str

    def check_in_object(self, object, path_func: Callable[[Self], str]) -> PreservedReference | None:
        object_id = id(object)
        if object_id in self.id_cache:
            return PreservedReference(object, obj_ref=self.id_cache[object_id])
        else:
            self.id_cache[object_id] = path_func(self)
            return object

    def set_handler(self, handler: OrderedHandler, merge: bool=True, update_order=False):
        if merge and self.handler is not None and self.handler is not handler:
            handler.update(self.handler, update_order=update_order)
        self.handler = handler

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize()
        if len(self.key_path) > 0:
            self.key_path.pop(-1)

