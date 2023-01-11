import re
from types import NoneType
from typing import Union, Never, Iterable, Self

from ram_util.utilities import T


class Temporary:
    __slots__ = 'val',

    def __init__(self, val: T):
        self.val = val

    def get_dict(self) -> T:
        return self.val


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
        self.temporary = Temporary
        #self.universal_sequence_type = UniversalSequence  # Non-user defined list (used for serialization)
        #self.universal_object_type = UniversalObject  # Non-user defined dictionary (used for serialization)
        self.type_primitives = int | float | str | bool | NoneType
        self.type_special = dict | list | Temporary
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
