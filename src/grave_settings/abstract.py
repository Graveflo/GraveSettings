# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import ABC, abstractmethod
from typing import TypeVar, MutableMapping, Type, Mapping, Callable, Self, Generator

from ram_util.utilities import OrderedHandler

from observer_hooks import notify, notify_copy_super
from grave_settings.conversion_manager import ConversionManager
from grave_settings.validation import SettingsValidator

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')




class Serializable(ABC):
    __slots__ = tuple()

    def to_dict(self, **kwargs) -> dict:
        zgen = ((i,getattr(self, i)) for i in dir(self))
        return dict(i for i in zgen if not (callable(i[1]) or i[0].startswith('__')))

    def from_dict(self, state_obj: dict, **kwargs):
        for k,v in state_obj.items():
            setattr(self, k, v)



class VersionedSerializable(Serializable):
    VERSION = None
    __slots__ = '_conversion_completed',

    def get_version(self):
        return self.VERSION

    def get_versioning_endpoint(self) -> Type[Self]:
        return VersionedSerializable

    def get_conversion_manager(self) -> ConversionManager:
        cm = ConversionManager()
        cm.converted.subscribe(self.conversion_manager_converted)
        return cm

    def conversion_manager_converted(self, state_obj: dict, class_str: str, ver: str, target_ver: str=None):
        pass

    @notify()
    def conversion_completed(self, old_ver: dict, new_ver: dict):
        pass

    def version_mismatch(self, state_obj: dict, old_version: str, **kwargs) -> dict:
        cm = self.get_conversion_manager()
        new_state_obj = cm.update_to_current(state_obj)
        is_convert = new_state_obj is not state_obj
        if is_convert:
            self.conversion_completed(state_obj, new_state_obj)
        return new_state_obj



def make_kill_converter(cls: Type[VersionedSerializable]) -> Callable[[dict], dict]:
    return lambda _: cls().to_dict(explicit=True)



class IASettings(VersionedSerializable, MutableMapping):
    __slots__ = 'parent', '_invalidate'

    def __init__(self, *args, **kwargs):
        self.parent: IASettings | None = None
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

    def get_partial_state(self, **kwargs) -> dict:
        return dict(self.generate_key_value_pairs(**kwargs))

    def get_serialization_handler(self) -> OrderedHandler | None:
        return None

    def get_deserialization_handler(self) -> OrderedHandler | None:
        return None

    def conversion_manager_settings_updated(self, state_obj: dict, class_str: str, ver: str, target_ver: str=None):
        self.invalidate()

    @notify_copy_super()
    def conversion_completed(self, old_ver: dict, new_ver: dict):
        self.invalidate()

    def get_validator(self) -> SettingsValidator | None:
        pass

    def needs_write(self) -> bool:
        return self.changes_made

    def __hash__(self):  # override this if you want to support value based equality
        return hash(id(self))


