# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import ABC, abstractmethod
from io import IOBase
from typing import Self, Callable, Any, Collection, Type, TypeVar

from observer_hooks import notify, EventHandler, HardRefEventHandler
from ram_util.modules import format_class_str
from ram_util.utilities import OrderedHandler, T

from grave_settings.semantics import Semantic


class PreservedReferenceNotDissolvedError(Exception):
    pass


T_S = TypeVar('T_S', bound=Semantic)


class IFormatter(ABC):
    #def __init__(self):
    #    self.semantics: Collection[Semantic] = set()

    def write_to_buffer(self, settings, _io: IOBase, encoding=None):
        pass

    def write_to_file(self, settings, path: str):
        with open(path, 'w') as f:
            # noinspection PyTypeChecker
            self.write_to_buffer(settings, f)

    @abstractmethod
    def serialize(self, obj: Any, route: 'Route', **kwargs):
        pass

    @abstractmethod
    def deserialize(self, obj, route: 'Route', **kwargs):
        pass

    @abstractmethod
    def supports_symantec(self, semantic_class: Type[Semantic]) -> bool:
        pass

    @abstractmethod
    def register_symantec(self, symantec: Semantic):
        pass

    @abstractmethod
    def get_semantic(self, semantic_class: Type[T_S]) -> T_S:
        pass


class KeySerializableDict:
    __slots__ = 'wrapped_dict',

    def __init__(self, wrapped_dict: dict):
        self.wrapped_dict = wrapped_dict


class PreservedReference(object):
    __slots__ = 'obj', 'ref'

    def __init__(self, obj: None | object = None, ref=None):
        if ref is None:
            ref = id(obj)
        self.ref = ref
        self.obj = obj

    def __hash__(self):
        return hash(id(self.obj))

    def detonate(self):
        raise PreservedReferenceNotDissolvedError()


class ConfigFileReference:
    def __init__(self, config):
        self.config = config


class Route:
    #__slots__ = 'key_path', 'logical_path', 'id_cache', 'handler', '_finalize'

    def __init__(self, handler, finalize_handler: EventHandler = None):
        self._finalize_frame = HardRefEventHandler()
        if finalize_handler is None:  # The very first frame shares event handler with finalize_frame
            finalize_handler = self._finalize_frame
        self.key_path = []
        self.obj_type_str = None  # can be set by the handler to change the type string
        self.id_cache = {}
        self.handler: OrderedHandler = handler
        self.frame_semantics = None
        self.semantics = None
        self._finalize = finalize_handler

    def register_frame_semantic(self, semantic: Semantic):
        if self.frame_semantics is None:
            self.frame_semantics = {}
        self.frame_semantics[semantic.__class__] = semantic

    def register_semantic(self, semantic: Semantic):
        if self.semantics is None:
            self.semantics = {}
        self.semantics[semantic.__class__] = semantic

    def get_semantic(self, t_semantic: Type[T_S]) -> T_S | None:
        if self.frame_semantics is not None:
            if t_semantic in self.frame_semantics:
                return self.frame_semantics[t_semantic]
        elif self.semantics is not None:
            if t_semantic in self.semantics:
                return self.semantics[t_semantic]

    def new(self, finalize_event: EventHandler) -> Self:
        return self.__class__(self.handler, finalize_handler=finalize_event)

    def branch(self, obj=None, path=None):
        r = self.branch_skip(self.key_path, obj=obj, path=path)
        if self.semantics is not None:
            r.semantics = self.semantics.copy()
        return r

    def branch_skip(self, key_path: list, obj=None, path=None):
        r = self.new(self._finalize)
        r.id_cache = self.id_cache
        r.key_path = key_path
        if obj is not None:
            self.obj_type_str = format_class_str(obj.__class__)
        if path is not None:
            r.key_path.append(path)
        return r

    @notify(no_origin=True, pass_ref=True)
    def finalize_frame(self):
        '''
        This even fires after the current frame has popped
        '''
        pass

    @notify(no_origin=True, pass_ref=True)
    def finalize(self):
        '''
        This even only fires after the root frame has been popped
        '''
        pass

    def set_obj_class_str(self, class_str: str):
        self.obj_type_str = class_str

    def check_in_object(self, obj: T, path_func: Callable[[Self], str]) -> PreservedReference | T:
        object_id = id(obj)
        if object_id in self.id_cache:
            return PreservedReference(obj=obj, ref=self.id_cache[object_id])
        else:
            self.id_cache[object_id] = path_func(self)
            return obj

    def check_out_object(self, obj: T, path_func: Callable[[Self], str]) -> T | object:
        if isinstance(obj, PreservedReference):
            if obj.ref in self.id_cache:
                return self.id_cache[obj.ref]
        else:
            self.id_cache[path_func(self)] = obj
        return obj

    def set_handler(self, handler: OrderedHandler, merge: bool=True, update_order=False):
        if merge and self.handler is not None and self.handler is not handler:
            handler.update(self.handler, update_order=update_order)
        self.handler = handler

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.finalize_frame()
        if len(self.key_path) > 0:
            self.key_path.pop(-1)
