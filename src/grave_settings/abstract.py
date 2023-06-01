# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import abstractmethod
from typing import TypeVar, MutableMapping, Type, Mapping, Callable, Self, Generator, Literal

from observer_hooks import notify

from grave_settings.conversion_manager import ConversionManager
from grave_settings.formatter_settings import FormatterContext, PreservedReference
from grave_settings.validation import SettingsValidator

_KT = TypeVar('_KT')
_VT = TypeVar('_VT')


class Serializable:
    __slots__ = '__weakref__',

    @classmethod
    def check_in_serialization_context(cls, context: FormatterContext):
        """
        This method typically is called on an instantiated object, so it may not be necessary for it to be a class
        method.
        """
        pass

    @classmethod
    def check_in_deserialization_context(cls, context: FormatterContext):
        """
        This method is typically called on type objects, so it should remain a class method in sub-classes. This is where
        you can put a reference to :py:class:`~grave_settings.semantics.NotifyFinalizedMethodName` to get a callback
        """
        # context.register_frame_semantic(NotifyFinalizedMethodName('finalize'))
        pass

    def to_dict(self, context: FormatterContext, **kwargs) -> dict:
        #zgen = ((i, getattr(self, i)) for i in dir(self))
        return self.__dict__

    def from_dict(self, state_obj: dict, context: FormatterContext, **kwargs):
        for k, v in state_obj.items():
            setattr(self, k, v)

    def finalize(self, frame: FormatterContext) -> None:  # This is pretty inefficient. Override it
        for key in dir(self):
            v = getattr(self, key)
            if isinstance(v, PreservedReference):
                setattr(self, key, frame.find(v))


class VersionedSerializable(Serializable):
    VERSION = None
    __slots__ = tuple()

    @classmethod
    def get_version(cls):
        return cls.VERSION

    @classmethod
    def get_version_object(cls):
        """
        It is saf to override this as an instance method
        """
        return cls.get_conversion_manager().get_version_object(cls)

    @classmethod
    def get_conversion_manager(cls) -> ConversionManager:
        cm = ConversionManager()
        cm.converted.subscribe(cls.conversion_manager_converted)
        return cm

    @classmethod
    def check_convert_update(cls, state_obj: dict, load_type: Callable[[str], Type],
                             version_obj: dict) -> dict | Literal[False]:
        conversion_manager = cls.get_conversion_manager()
        rst = state_obj
        instance = conversion_manager.update_to_current(state_obj, load_type, version_obj)
        if rst is instance:
            return False
        else:
            return instance

    @classmethod
    def conversion_manager_converted(cls, state_obj: dict, class_str: str, ver: str, target_ver: str = None):
        pass

    @classmethod
    def get_versioning_endpoint(cls) -> Type[Self]:
        return VersionedSerializable


def make_kill_converter(cls: Type[VersionedSerializable]) -> Callable[[dict], dict]:
    return lambda *_: cls().to_dict(None)


class IASettings(VersionedSerializable, MutableMapping):
    __slots__ = 'parent', '_invalidate'

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

    def finalize(self, frame: FormatterContext):
        for key, v in self.generate_key_value_pairs():
            if isinstance(v, PreservedReference):
                self[key] = frame.find(v)

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

    def get_validator(self) -> SettingsValidator | None:
        pass

    def __hash__(self):  # override this if you want to support value based equality
        return hash(id(self))

