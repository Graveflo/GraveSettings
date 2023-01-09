# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Self, Type, TypeVar

from observer_hooks import notify, EventHandler, HardRefEventHandler
from ram_util.utilities import OrderedHandler

from grave_settings.semantics import Semantic


T_S = TypeVar('T_S', bound=Semantic)


class PreservedReferenceNotDissolvedError(Exception):
    pass


class KeySerializableDict:
    __slots__ = 'wrapped_dict',

    def __init__(self, wrapped_dict: dict):
        self.wrapped_dict = wrapped_dict

    def to_dict(self) -> dict:
        return {
            'kvps': list(x for x in self.wrapped_dict.items())
        }

    def from_dict(self, obj: dict):
        self.wrapped_dict = dict(x for x in obj['kvps'])


class PreservedReference(object):
    __slots__ = 'obj', 'ref', '__weakref__'

    def __init__(self, obj: None | object = None, ref=None):
        if ref is None:
            ref = id(obj)
        self.ref = ref
        self.obj = obj

    def __hash__(self):
        return hash(id(self.obj))


class ConfigFileReference:
    def __init__(self, config):
        self.config = config


class Route:
    #__slots__ = 'key_path', 'logical_path', 'id_cache', 'handler', '_finalize'

    def __init__(self, handler, finalize_handler: EventHandler = None):
        if finalize_handler is None:
            finalize_handler = HardRefEventHandler()
        self.obj_type_str = None  # can be set by the handler to change the type string
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

    def branch(self):
        r = self.new(self.finalize)  # we want to maintain a handle to the root frame's finalize EventHandler
        if self.semantics is not None:
            r.semantics = self.semantics.copy()
        return r

    @notify(no_origin=True, pass_ref=False)
    def finalize(self, id_cache: dict):
        pass

    def set_obj_class_str(self, class_str: str):
        self.obj_type_str = class_str

    def set_handler(self, handler: OrderedHandler, merge: bool = True, update_order=False):
        if merge and self.handler is not None and self.handler is not handler:
            handler.update(self.handler, update_order=update_order)
        self.handler = handler
