import re
from types import NoneType
from typing import Iterable, Self, get_args

from observer_hooks import notify, HardRefEventHandler
from ram_util.utilities import T

from grave_settings.handlers import OrderedHandler
from grave_settings.framestackcontext import FrameStackContext
from grave_settings.semantics import Semantic


class NoRef:
    __slots__ = 'val',

    def __init__(self, val: T):
        self.val = val

    def __str__(self):
        return f'NoRef({self.val})'


class Temporary(NoRef):
    __slots__ = tuple()

    def __str__(self):
        return f'Temporary({self.val})'


class PreservedReference(object):
    __slots__ = 'obj', 'ref', '__weakref__'

    def __init__(self, obj: None | object = None, ref=None):
        if ref is None:
            ref = id(obj)
        self.ref = ref
        self.obj = obj

    def __hash__(self):
        return hash(id(self.obj))


class FormatterSpec:
    ROUTE_PATH_TRANSLATION = str.maketrans({
        '\\': '\\\\',
        '.': r'\.',
        '"': r'\"'
    })
    ROUTE_PATH_REGEX = re.compile(r'(?:[^\."]|"(?:\\.|[^"])*")+')
    PRIMITIVES = int | float | str | bool | NoneType
    SPECIAL = dict | list
    ATTRIBUTE = str

    TYPES = PRIMITIVES | SPECIAL

    def __init__(self):
        self.str_id = '__id__'
        self.version_id = '__version__'
        self.class_id = '__class__'
        self.temporary = Temporary
        self.type_primitives = self.PRIMITIVES
        self.type_special = self.SPECIAL
        self.type_attribute = self.ATTRIBUTE

    def get_primitive_types(self) -> set:
        return set(get_args(self.type_primitives))

    def get_special_types(self) -> set:
        return set(get_args(self.type_special))

    def get_attribute_types(self) -> set:
        return {self.type_attribute}

    def path_to_str(self, key_path: Iterable) -> str:
        parts = (str(part) if type(part) == int else f'"{part.translate(self.ROUTE_PATH_TRANSLATION)}"'
                 for part in key_path)
        return '.'.join(parts)

    def str_to_path(self, reference: str) -> list:
        return list(p[1:-1] if p.startswith('"') and p.endswith('"') else int(p)
                    for p in self.ROUTE_PATH_REGEX.findall(reference))

    def get_part_from_path(self, obj: TYPES, path: list | str) -> TYPES:
        if type(path) is str:
            path = self.str_to_path(path)
        for key in path:
            obj = obj[key]
        return obj

    def is_circular_ref(self, path: list | str, in_path: list | str) -> bool:
        if type(path) is str:
            path = self.str_to_path(path)
        if type(in_path) is str:
            in_path = self.str_to_path(in_path)
        if len(path) > len(in_path):
            return False
        for pf, rp in zip(in_path, path):
            if pf != rp:
                return False
        return True

    def copy(self) -> Self:
        n = self.__class__()
        for v in vars(n):
            setattr(n, v, getattr(self, v))
        return n


class FormatterContext:
    def __init__(self, semantics: FrameStackContext):
        self.key_path = []
        self.id_cache = {}
        self.semantic_context = semantics

    @property
    def handler(self) -> OrderedHandler:
        return self.semantic_context.handler

    @handler.setter
    def handler(self, handler: OrderedHandler):
        self.semantic_context.set_handler(handler)

    def update(self, obj: Self):
        self.key_path = obj.key_path.copy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.key_path.pop(-1)

    def __call__(self, path):
        self.key_path.append(path)
        return self

    def find(self, reference: PreservedReference):
        return self.id_cache[reference.ref]

    def check_ref(self, reference: PreservedReference):
        if reference.ref in self.id_cache:
            return self.id_cache[reference.ref]

    def add_frame_semantic(self, semantic: Semantic):
        self.semantic_context.add_frame_semantic(semantic)

    def add_semantic(self, semantic: Semantic):
        self.semantic_context.add_semantic(semantic)

    @notify(no_origin=True, pass_ref=True, handler_t=HardRefEventHandler)
    def finalize(self):
        pass

