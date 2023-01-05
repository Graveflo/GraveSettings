# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Mapping, Generator, Type

from ram_util.utilities import generate_hierarchy_to_base, unwrap_slots_to_base, ext_str_slots
from grave_settings.abstract import IASettings, _KT, _VT, VersionedSerializable


class Settings(IASettings):
    __slots__ = 'sd',

    def __init__(self, *args, initialize_settings=True, **kwargs):
        self.sd = {}
        if initialize_settings:
            self.init_settings()
        super(Settings, self).__init__(*args, **kwargs)

    def get_versioning_endpoint(self) -> Type[VersionedSerializable]:
        return Settings
        # return JsonSerializable # this will change to this class in the future

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

    def to_dict(self, **kwargs) -> dict:
        return self.sd.copy()


rem_slot_fixed = set()


class SlotSettings(IASettings):
    _slot_rems = None
    __slots__ = 'get_settings_keys',

    @classmethod
    def __new__(cls, *args, **kwargs):
        if cls not in rem_slot_fixed:
            found_slot_rems = False

            slrm = set()
            for tt in generate_hierarchy_to_base(SlotSettings, cls):
                if hasattr(tt, '_slot_rems') and tt._slot_rems is not None:
                    found_slot_rems = True
                    slrm.update(tt._slot_rems)

            if found_slot_rems:
                cls._slot_rems = tuple(slrm)
                cls.get_settings_keys = cls.get_settings_keys_rems
            else:
                cls.get_settings_keys = cls.get_settings_keys_base_slots
            rem_slot_fixed.add(cls)

        return super(SlotSettings, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        super(SlotSettings, self).__init__(*args, **kwargs)

    def get_versioning_endpoint(self) -> Type[VersionedSerializable]:
        return SlotSettings
        # return JsonSerializable # This will change to this class in the future

    def get_settings_keys_rems(self, rems=None) -> set:
        if rems is None:
            rems = self._slot_rems
        return self.get_settings_keys_base_slots().difference(rems)

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

    def __setattr__(self, key, value):  # TODO: This is very inefficient but without it unexpected things can happen
        super(SlotSettings, self).__setattr__(key, value)
        if key in self.get_settings_keys():
            self.invalidate()

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

    def get_settings_keys_base_slots(self) -> set:
        return unwrap_slots_to_base(SlotSettings, self.__class__)

    def __iter__(self):
        return iter(self.get_settings_keys())

    def __len__(self):
        return len(self.get_settings_keys())

    def generate_key_value_pairs(self) -> Generator[tuple[object, object], None, None]:
        yield from self.get_partial_state().items()

    def to_dict(self, **kwargs) -> dict:
        return {s: self[s] for s in self.get_settings_keys()}

    def __str__(self):
        return ext_str_slots(self, base=self.get_versioning_endpoint())
