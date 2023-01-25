import os
import re
from types import NoneType
from typing import Iterable, Self, get_args, Type

from observer_hooks import notify, HardRefEventHandler

from grave_settings.utilities import T, format_class_str, load_type
from grave_settings.handlers import OrderedHandler
from grave_settings.framestack_context import FrameStackContext
from grave_settings.semantics import Semantic, AutoPreserveReferences, T_S_E, DoNotAllowImportingModules, \
    ClassStringPassFunction, SecurityException


class AddSemantics:
    """
    Wrapping an object in this class will tell the formatter to add semantics to its frame
    """
    __slots__ = 'val', 'semantics', 'frame_semantics'

    def __init__(self, val: T, semantics: set[Semantic] | None = None, frame_semantics: set[Semantic] | None = None):
        self.val = val
        self.semantics = semantics
        self.frame_semantics = frame_semantics

    def __str__(self):
        return f'AddSemantics({self.val})'


class NoRef(AddSemantics):
    """
    Wrapping an object in this class will tell the formatter to not reference this object or cache it
    """
    __slots__ = tuple()

    def __init__(self, val: T, semantics: set[Semantic] | None = None, frame_semantics: set[Semantic] | None = None):
        if frame_semantics is None:
            frame_semantics = {AutoPreserveReferences(False)}
        else:
            if AutoPreserveReferences(True) not in frame_semantics:
                frame_semantics.add(AutoPreserveReferences(False))
        super().__init__(val, semantics=semantics, frame_semantics=frame_semantics)

    def __str__(self):
        return f'NoRef({self.val})'


class Temporary(NoRef):
    """
    Wrapping an object in this class will tell the formatter that the object is not to be referenced and has no strings
    attached to any other object. The wrapped object exists only for communicating data to the formatter.
    The formatter may mutate it and destroy it.
    """
    __slots__ = tuple()

    def __str__(self):
        return f'Temporary({self.val})'


class PreservedReference:
    """
    This clas denotes a reference to another path in an object hierarchy. This object should act like a pointer
    describing where an object exists in the structure.
    """
    __slots__ = 'obj', 'ref', '__weakref__'

    def __init__(self, obj: None | object = None, ref=None):
        if ref is None:
            ref = id(obj)
        self.ref = ref
        self.obj = obj

    def __hash__(self):
        return hash(id(self.obj))

    def __str__(self):
        return f'PreservedReference(ref={repr(self.ref)}, obj={self.obj})'


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
        self.key = None

    def __str__(self):
        return f'Formatter Context ({format_class_str(self.__class__)}): {repr(self.key_path)}{os.linesep}{self.semantic_context}'

    @property
    def handler(self) -> OrderedHandler:
        return self.semantic_context.handler

    @handler.setter
    def handler(self, handler: OrderedHandler):
        self.semantic_context.set_handler(handler, update_order=True)

    def handle(self, obj):
        return self.semantic_context.handler.handle(obj, self)

    def update(self, obj: Self):
        self.key_path = obj.key_path.copy()

    def __enter__(self):
        self.key_path.append(self.key)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.key_path.pop(-1)

    def __call__(self, path):
        self.key = path
        return self

    def find(self, reference: PreservedReference):
        return self.id_cache[reference.ref]

    def check_ref(self, reference: PreservedReference):
        if reference.ref in self.id_cache:
            return self.id_cache[reference.ref]

    def add_frame_semantics(self, *semantic: T_S_E):
        self.semantic_context.add_frame_semantics(*semantic)

    def add_semantics(self, *semantic: T_S_E):
        self.semantic_context.add_semantics(*semantic)

    def get_stack_depth(self) -> int:
        return len(self.key_path)

    def load_type(self, class_str: str) -> Type:
        semantics = self.semantic_context
        allow_imports = not bool(semantics[DoNotAllowImportingModules])
        validation = semantics[ClassStringPassFunction]
        if validation:
            for validation_call in validation:
                if not validation_call.val(class_str):
                    raise SecurityException()
        return load_type(class_str, do_import=allow_imports)

    @notify(no_origin=True, pass_ref=True, handler_t=HardRefEventHandler)
    def finalize(self):
        pass

    def dispose(self):
        self.id_cache.clear()
