# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Mapping, Generator, Type
from abc import ABCMeta

from ordered_set import OrderedSet
from grave_settings.utilities import unwrap_slots_to_base, ext_str_slots
from grave_settings.abstract import IASettings, _KT, _VT, VersionedSerializable
from grave_settings.formatter_settings import FormatterContext


class Settings(IASettings):
    __slots__ = 'sd',

    def __init__(self, *args, initialize_settings=True, **kwargs):
        self.sd = {}
        super(Settings, self).__init__(*args, initialize_settings=initialize_settings, **kwargs)

    @classmethod
    def get_versioning_endpoint(cls) -> Type[VersionedSerializable]:
        return Settings

    def update(self, __m: Mapping[_KT, _VT], **kwargs: _VT):
        self.sd.update(__m, **kwargs)

    def __contains__(self, item):
        return item in self.sd

    def __setitem__(self, key, value):
        is_new = key not in self
        if is_new == False:
            prev = self[key]
            is_new = value != prev
        it_t = type(key)
        if it_t == list or it_t == tuple:
            set = self
            for it_ in key[:-1]:
                set = set[it_]
            set[key[-1]] = value
        else:
            self.sd[key] = value
        if is_new:
            self.invalidate()

    def __getitem__(self, item):
        it_t = type(item)
        if it_t == list or it_t == tuple:
            init_o = self
            for it_ in item:
                init_o = init_o[it_]
            return init_o
        else:
            return self.sd[item]

    def __delitem__(self, itm):
        del self.sd[itm]

    def __iter__(self):
        return iter(self.sd)

    def __len__(self):
        return len(self.sd)

    def generate_key_value_pairs(self, **kwargs) -> Generator[tuple[object, object], None, None]:
        yield from self.sd.items()

    def to_dict(self, context: FormatterContext, **kwargs) -> dict:
        return self.sd.copy()


def assemble_settings_keys_from_base(cls: Type, msub=IASettings) -> tuple:
    try:
        ret = object.__getattribute__(cls, 'SETTINGS_KEYS')
        if ret is not None:  # cached
            return ret
    except AttributeError:
        pass
    keys = OrderedSet()
    try:
        keys.update(object.__getattribute__(cls, '__slots__'))
    except AttributeError:
        pass
    for tt in cls.__bases__:
        if tt is not msub and issubclass(tt, msub):
            ins = OrderedSet(assemble_settings_keys_from_base(tt))
            ins.update(keys)
            keys = ins
    try:
        _slot_rems = object.__getattribute__(cls, '_slot_rems')
        if _slot_rems is not None:
            return tuple(k for k in keys if k not in _slot_rems)
    except AttributeError:
        pass
    return tuple(keys)


class slotsettings_meta(ABCMeta):
    def __new__(cls, clsname, bases, attrs):
        if '__slots__' not in attrs:
            attrs['__slots__'] = tuple()
        tt = super().__new__(cls, clsname, bases, attrs)
        if hasattr(tt, 'assemble_settings_keys_from_base'):
            settings_keys = tt.assemble_settings_keys_from_base(tt)
        else:
            settings_keys = assemble_settings_keys_from_base(tt)
        setattr(tt, 'SETTINGS_KEYS', settings_keys)
        setattr(tt, '__metaclass__', slotsettings_meta)
        return tt


class SlotSettings(IASettings, metaclass=slotsettings_meta):
    _slot_rems = None
    __slots__ = tuple()
    SETTINGS_KEYS = None

    @classmethod
    def get_versioning_endpoint(cls) -> Type[VersionedSerializable]:
        return SlotSettings

    def get_settings_keys_rems(self, rems=None) -> set:
        if rems is None:
            rems = self._slot_rems
        return self.get_settings_keys_base_slots().difference(rems)

    def get_settings_keys_base_slots(self) -> set:
        return unwrap_slots_to_base(SlotSettings, self.__class__)

    def get_settings_keys(self):
        return self.SETTINGS_KEYS

    def safe_update(self, mapping_obj: Mapping[_KT, _VT], **kwargs: _VT):
        try:
            return super(SlotSettings, self).update(mapping_obj, **kwargs)
        except AttributeError:
            valid_attrs = self.get_settings_keys()

            it_t = type(mapping_obj)
            if it_t == list or it_t == tuple:
                new_dict = {k: v for k, v in mapping_obj if k in valid_attrs}
            else:
                new_dict = {k: v for k, v in mapping_obj.items() if k in valid_attrs}
            for k, v in kwargs.items():
                if k in valid_attrs:
                    new_dict[k] = v
            return super(SlotSettings, self).update(new_dict)

    def __contains__(self, item):
        return hasattr(self, item)

    def __setitem__(self, key, value):
        it_t = type(key)
        if it_t == list or it_t == tuple:
            set = self
            for it_ in key[:-1]:
                set = set[it_]
            set[key[-1]] = value
        else:
            if it_t is str:
                setattr(self, key, value)
            else:
                raise ValueError('Keys for member settings must be string')
        self.invalidate()

    def __getitem__(self, item):
        it_t = type(item)
        if it_t == list or it_t == tuple:
            init_o = self
            for it_ in item:
                init_o = init_o[it_]
            return init_o
        else:
            if it_t is str:
                return getattr(self, item)
            else:
                raise ValueError('Keys for member settings must be string')

    def __delitem__(self, itm):
        raise ValueError('Cannot delete member of MemberVariableSettings')

    def __iter__(self):
        return iter(self.get_settings_keys())

    def __len__(self):
        return len(self.get_settings_keys())

    def generate_key_value_pairs(self) -> Generator[tuple[object, object], None, None]:
        return ((s, getattr(self, s)) for s in self.get_settings_keys())

    def to_dict(self, context: FormatterContext, **kwargs) -> dict:
        return dict(self.generate_key_value_pairs())

    def __str__(self):
        return ext_str_slots(self, base=self.get_versioning_endpoint())
