# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import ABC, abstractmethod
from typing import TypeVar, MutableMapping, Type, Mapping, Callable, Self, Generator

from observer_hooks import notify, EventHandler, HardRefEventHandler

from grave_settings.handlers import OrderedHandler
from grave_settings.conversion_manager import ConversionManager
from grave_settings.formatter_settings import FormatterSettings
from grave_settings.semantics import Semantic, T_S
from grave_settings.validation import SettingsValidator

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')


class Route(ABC):
    __slots__ = 'obj_type_str', 'handler', '_finalize', 'formatter_settings'

    def __init__(self, handler, finalize_handler: EventHandler = None):
        if finalize_handler is None:
            finalize_handler = HardRefEventHandler()
        self.obj_type_str = None  # can be set by the handler to change the type string
        self.handler: OrderedHandler = handler
        self._finalize = finalize_handler
        self.formatter_settings: FormatterSettings | None = None

    def clear(self):
        self.finalize.clear_side_effects()
        self.formatter_settings = None
        self.clear_branch()

    def clear_branch(self):
        self.obj_type_str = None

    @abstractmethod
    def add_frame_semantic(self, semantic: Semantic):
        pass

    @abstractmethod
    def add_semantic(self, semantic: Semantic):
        pass

    @abstractmethod
    def remove_frame_semantic(self, semantic: Type[Semantic] | Semantic):
        pass

    @abstractmethod
    def remove_semantic(self, semantic: Type[Semantic] | Semantic):
        pass

    @abstractmethod
    def get_semantic(self, t_semantic: Type[T_S]) -> T_S | None:
        pass

    @abstractmethod
    def branch(self):
        pass

    @notify(no_origin=True, pass_ref=False)
    def finalize(self, id_cache: dict):
        pass

    def set_obj_class_str(self, class_str: str):
        self.obj_type_str = class_str

    def set_handler(self, handler: OrderedHandler, merge: bool = True, update_order=False):
        if merge and self.handler is not None and self.handler is not handler:
            handler.update(self.handler, update_order=update_order)
        self.handler = handler


class Serializable:
    __slots__ = '__weakref__',

    @classmethod
    def check_in_serialization_route(cls, route: Route):
        pass

    @classmethod
    def check_in_deserialization_route(cls, route: Route):
        # Uncomment this to get the limited auto circular reference resolution
        # route.register_frame_semantic(NotifyFinalizedMethodName('finalize'))
        pass

    def to_dict(self, route: Route, **kwargs) -> dict:
        zgen = ((i, getattr(self, i)) for i in dir(self))
        return dict(i for i in zgen if not (callable(i[1]) or i[0].startswith('__')))

    def from_dict(self, state_obj: dict, route: Route, **kwargs):
        for k, v in state_obj.items():
            setattr(self, k, v)

    def finalize(self, id_map: dict) -> None:  # This is pretty inefficient. Override it
        from grave_settings.helper_objects import PreservedReference

        for key in dir(self):
            v = getattr(self, key)
            if isinstance(v, PreservedReference):
                if v.ref in id_map:
                    setattr(self, key, id_map[v.ref])


class VersionedSerializable(Serializable):
    VERSION = None
    __slots__ = tuple()

    @classmethod
    def get_version(cls):
        return cls.VERSION

    @classmethod
    def get_conversion_manager(cls) -> ConversionManager:
        cm = ConversionManager()
        cm.converted.subscribe(cls.conversion_manager_converted)
        return cm

    @classmethod
    def conversion_manager_converted(cls, state_obj: dict, class_str: str, ver: str, target_ver: str = None):
        pass

    @classmethod
    def version_mismatch(cls, state_obj: dict, old_version: str, **kwargs) -> dict:
        cm = cls.get_conversion_manager()
        new_state_obj = cm.update_to_current(state_obj)
        is_convert = new_state_obj is not state_obj
        if is_convert:
            cls.conversion_completed(state_obj, new_state_obj)
        return new_state_obj

    @classmethod
    def get_versioning_endpoint(cls) -> Type[Self]:
        return VersionedSerializable

    def conversion_completed(self, old_ver: dict, new_ver: dict):
        pass


def make_kill_converter(cls: Type[VersionedSerializable]) -> Callable[[dict], dict]:
    return lambda _: cls().to_dict(explicit=True)


class IASettings(VersionedSerializable, MutableMapping):
    __slots__ = 'parent', '_invalidate', '_conversion_completed'

    def __init__(self, *args, initialize_settings=True, **kwargs):
        self.parent: IASettings | None = None
        if initialize_settings:
            self.init_settings(**kwargs)

    def init_settings(self, **kwargs) -> None:
        pass

    def get_versioning_endpoint(self) -> Type[VersionedSerializable]:
        return IASettings

    @notify()
    def invalidate(self) -> None:
        if self.parent is not None:
            self.parent.invalidate()

    def update(self, mapping_obj: Mapping[_KT, _VT], **kwargs: _VT):
        it_t = type(mapping_obj)
        if it_t == list or it_t == tuple:
            for k, v in mapping_obj:
                self[k] = v
        else:
            for k, v in mapping_obj.items():
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def finalize(self, id_map: dict):
        from grave_settings.helper_objects import PreservedReference

        for key, v in self.generate_key_value_pairs():
            if isinstance(v, PreservedReference):
                if v.ref in id_map:
                    self[key] = id_map[v.ref]

    @abstractmethod
    def __contains__(self, item):
        pass

    @abstractmethod
    def __setitem__(self, key, value):
        pass

    @abstractmethod
    def __getitem__(self, item):
        pass

    @abstractmethod
    def __delitem__(self, itm):
        pass

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def __len__(self) -> int:
        pass

    def __bool__(self):  # This is to avoid unexpected edge case bugs since __len__ is implemented. Maybe just use explicit checks
        return True

    @abstractmethod
    def generate_key_value_pairs(self, **kwargs) -> Generator[tuple[object, object], None, None]:
        pass

    def conversion_manager_settings_updated(self, state_obj: dict, class_str: str, ver: str, target_ver: str=None):
        self.invalidate()

    @notify()
    def conversion_completed(self, old_ver: dict, new_ver: dict):
        self.invalidate()

    def get_validator(self) -> SettingsValidator | None:
        pass

    def __hash__(self):  # override this if you want to support value based equality
        return hash(id(self))

