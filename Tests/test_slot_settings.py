from unittest import TestCase, main
from typing import Type
from grave_settings.base import SlotSettings


class TestSlotSettingsSettingsKeysResolution(TestCase):
    def get_tuple(self, cls: Type):
        return SlotSettings.assemble_settings_keys_from_base(cls)

    def test_empty(self):
        class Set(SlotSettings):
            __slots__ = tuple()

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

        class Set(SlotSettings):  # user forgets to define slots
            pass

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

        # 2 layer
        class Foo(SlotSettings):
            __slots__ = tuple()

        class Set(Foo):
            __slots__ = tuple()

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

    def test_base_with_slots(self):
        class Set(SlotSettings):
            __slots__ = 'a', 'b'

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('a', 'b'))

        # 2 layer
        class Foo(SlotSettings):
            __slots__ = 'c',

        class Set(Foo):
            __slots__ = 'a', 'b'

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('c', 'a', 'b'))

    def test_base_with_slots_and_rems(self):
        class Set(SlotSettings):
            _slot_rems = 'a',
            __slots__ = 'a', 'b'

        keys = self.get_tuple(Set)
        self.assertTupleEqual(keys, ('b', ))

        # 2 layer
        class Foo(SlotSettings):
            _slot_rems = 'd',
            __slots__ = 'c', 'd'

        class Set(Foo):
            _slot_rems = 'a',
            __slots__ = 'a', 'b'

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('c', 'b'))

    def test_base_with_settings_keys_defined(self):
        class Set(SlotSettings):
            __slots__ = 'a', 'b'
            SETTINGS_KEYS = ('b', )

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('b', ))


        # 2 layer
        class Foo(SlotSettings):
            __slots__ = 'c', 'd'
            SETTINGS_KEYS = ('d',)

        class Set(Foo):
            __slots__ = 'a', 'b'
            SETTINGS_KEYS = ('b', )

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('b', ))

    def test_empty_with_slot_rems(self):
        class Set(SlotSettings):
            __slots__ = 'b',
            _slot_rems = ('b', )

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

        # 2 layer
        class Foo(SlotSettings):
            __slots__ = 'a',
            _slot_rems = ('a', )

        class Set(Foo):
            __slots__ = 'b',
            _slot_rems = ('b',)

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

    def test_rems_cover_bases(self):
        class Foo(SlotSettings):
            __slots__ = 'a',

        class Set(Foo):
            __slots__ = 'b',
            _slot_rems = ('b', 'a')

        keys = self.get_tuple(Foo)
        self.assertSequenceEqual(keys, ('a', ))
        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, tuple())

    def test_settings_keys_override_base_rems(self):
        class Foo(SlotSettings):
            __slots__ = 'a',
            _slot_rems = 'a',


        class Set(Foo):
            __slots__ = 'b'
            SETTINGS_KEYS = 'b', 'a'

        keys = self.get_tuple(Foo)
        self.assertSequenceEqual(keys, tuple())
        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('b', 'a'))

    def test_base_defines_settings_keys_doesnt_stop_res(self):
        class Foo(SlotSettings):
            __slots__ = 'a',
            SETTINGS_KEYS = 'a',


        class Set(Foo):
            __slots__ = 'b', 'c'
            _slot_rems = 'c',

        keys = self.get_tuple(Foo)
        self.assertSequenceEqual(keys, ('a', ))
        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('a', 'b'))

    def test_settings_keys_overrides_slot_rems(self):
        class Set(SlotSettings):
            __slots__ = 'b', 'c'
            _slot_rems = 'c',
            SETTINGS_KEYS = 'b', 'c'

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('b', 'c'))


class TestSlotSettingsSettingsKeysResolutionObject(TestSlotSettingsSettingsKeysResolution):
    def get_tuple(self, cls: Type):
        obj = cls()
        return obj.get_settings_keys()

    def test_class_caches_settings_keys(self):
        class Foo(SlotSettings):
            __slots__ = 'a',
            _slot_rems = ('a', )

        class Set(Foo):
            __slots__ = 'b', 'c'
            _slot_rems = ('b',)

        keys = self.get_tuple(Set)
        self.assertSequenceEqual(keys, ('c', ))
        self.assertSequenceEqual(Set.SETTINGS_KEYS, ('c', ))
        self.assertEqual(Foo.SETTINGS_KEYS, None)


if __name__ == '__main__':
    main()
