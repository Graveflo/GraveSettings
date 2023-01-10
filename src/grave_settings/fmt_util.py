# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import re
from types import NoneType
from typing import Self, Type, TypeVar, Union, Never, Iterable

from observer_hooks import notify, EventHandler, HardRefEventHandler
from ram_util.utilities import OrderedHandler

from grave_settings.semantics import Semantic, remove_semantic_from_dict

T_S = TypeVar('T_S', bound=Semantic)


class ConfigFileReference:
    def __init__(self, config):
        self.config = config


class FormatterSettings:
    ROUTE_PATH_TRANSLATION = str.maketrans({
        '\\': '\\\\',
        '.': r'\.',
        '"': r'\"'
    })
    ROUTE_PATH_REGEX = re.compile(r'(?:[^\."]|"(?:\\.|[^"])*")+')

    def __init__(self):
        self.str_id = '__id__'
        self.version_id = '__version__'
        self.class_id = '__class__'
        # the thought was to use these to diff user structures and serialization structures, to
        # avoid the preservation of placeholder objects and consume less memory (holding id for lifecycle).
        # An added benefit, this would allow more extreme formatter options that use different types,
        # but I think that might be stupid
        #self.universal_sequence_type = list
        #self.universal_object_type = dict
        self.type_primitives = int | float | str | bool | NoneType
        self.type_special = dict | list
        self.type_attribute = Union[str, Never]

    def path_to_str(self, key_path: Iterable) -> str:
        parts = (str(part) if type(part) == int else f'"{part.translate(self.ROUTE_PATH_TRANSLATION)}"'
                 for part in key_path)
        return '.'.join(parts)

    def str_to_path(self, reference: str) -> list:
        return list(p[1:-1] if p.startswith('"') and p.endswith('"') else int(p)
                    for p in self.ROUTE_PATH_REGEX.findall(reference))

    def copy(self) -> Self:
        n = self.__class__()
        for v in vars(n):
            setattr(n, v, getattr(self, v))
        return n


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
        self.formatter_settings: FormatterSettings | None = None

    def clear(self):
        self.semantics = None
        self.finalize.clear_side_effects()
        self.obj_type_str = None
        self.formatter_settings = None

    def add_frame_semantic(self, semantic: Semantic):
        if self.frame_semantics is None:
            self.frame_semantics = {}
        self.frame_semantics[semantic.__class__] = semantic

    def add_semantic(self, semantic: Semantic):
        if self.semantics is None:
            self.semantics = {}
        self.semantics[semantic.__class__] = semantic

    def remove_frame_semantic(self, semantic: Type[Semantic] | Semantic):
        remove_semantic_from_dict(semantic, self.frame_semantics)

    def remove_semantic(self, semantic: Type[Semantic] | Semantic):
        remove_semantic_from_dict(semantic, self.semantics)

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
        r = self.new(self._finalize)  # we want to maintain a handle to the root frame's finalize EventHandler
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


