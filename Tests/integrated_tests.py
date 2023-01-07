# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import json
from typing import Self, Any
from unittest import TestCase, main

from ram_util.utilities import OrderedHandler

from grave_settings.abstract import Serializable
from grave_settings.base import SlotSettings
from grave_settings.default_handlers import JsonSerializationHandler, JsonDeSerializationHandler
from grave_settings.fmt_util import Route
from grave_settings.formatter import Formatter
from grave_settings.semantics import AutoPreserveReferences


class AssertsSerializable(Serializable):
    def assert_object_equiv(self, other: Self):
        pass


class Dummy(SlotSettings):
    __slots__ = 'a', 'b'

    def __init__(self, a=None, b=None):
        super().__init__()
        self.a = a
        self.b = b

    def assert_object_equiv(self, tc: TestCase, other: Self):
        tc.assertEqual(self.a, other.a)
        tc.assertEqual(self.b, other.b)

    def get_settings_keys_base_slots(self):  # Keep order consistent
        return self.__slots__


class Scenarios(TestCase):
    def get_serialization_handler(self) -> OrderedHandler:
        return JsonSerializationHandler()

    def get_deserialization_handler(self) -> OrderedHandler:
        return JsonDeSerializationHandler()

    def get_route(self, handler: OrderedHandler) -> Route:
        return Route(handler)

    def get_basic(self, a:Any=90, b:Any='this is a string') -> AssertsSerializable:
        return Dummy(a=a, b=b)

    def get_basic_versioned(self, a=90, b='this is a string', version=None) -> AssertsSerializable:
        class DummyVersioned(SlotSettings):
            VERSION = version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = a
                self.b = b

            def assert_object_equiv(self, tc: TestCase, other: Self):
                tc.assertEqual(self.a, other.a)
                tc.assertEqual(self.b, other.b)

            def get_settings_keys_base_slots(self):  # Keep order consistent
                return self.__slots__

        globals()['DummyVersioned'] = DummyVersioned
        return DummyVersioned()

    def get_layered_duplicate(self):
        class S(SlotSettings):
            __slots__ = 'a'

            def __init__(self):
                super().__init__()
                self.a = 0

        class C(SlotSettings):
            __slots__ = tuple()

        class A(SlotSettings):
            __slots__ = 'a', 'b', 'x'

            def __init__(self):
                super().__init__()
                self.a = S()
                self.x = 90
                self.b = [C(), 2, self.a, S(), self.a]

            def get_settings_keys_base_slots(self) -> set:  # Keep order consistent
                return self.__slots__

        return A()

    def assert_obj_roundtrip(self, obj):
        formatter = Formatter()
        formatter.register_symantec(AutoPreserveReferences(True))
        route = self.get_route(self.get_serialization_handler())
        ser_obj = formatter.serialize(obj, route)
        re_made_object = self.deser_ser_obj(ser_obj)
        obj.assert_object_equiv(self, re_made_object)
        self.assertIsNot(obj, re_made_object)
        return re_made_object

    def deser_ser_obj(self, ser_obj):
        formatter = Formatter()
        deser_route = self.get_route(self.get_deserialization_handler())
        re_made_object = formatter.deserialize(ser_obj, deser_route)
        return re_made_object

class TestSerialization(Scenarios):
    def test_basic(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = formatter.serialize(self.get_basic(), route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': 90,
            'b': 'this is a string'
        })

    def test_basic_versioned(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = formatter.serialize(self.get_basic_versioned(version='1.0'), route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: {'integrated_tests.DummyVersioned': '1.0'},
            formatter.settings.class_id: 'integrated_tests.DummyVersioned',
            'a': 90,
            'b': 'this is a string'
        })

    def test_nested_in_attribute(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=99)
        ser_obj = formatter.serialize(obj, route)
        self.assertDictEqual(ser_obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': 90,
                'b': 'this is a string'
            },
            'b': 99
        })

    def test_nested_in_list(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        lis = [
            self.get_basic(a=90, b='this'),
            self.get_basic(a=0, b=False)
        ]
        obj = self.get_basic(a=lis, b=99)
        ser_obj = formatter.serialize(obj, route)
        self.assertDictEqual(ser_obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': [{
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': 90,
                'b': 'this'
            }, {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': 0,
                'b': False
            }],
            'b': 99
        })

    def test_duplicate_in_attribute(self):
        formatter = Formatter()
        formatter.register_symantec(AutoPreserveReferences(True))
        route = self.get_route(self.get_serialization_handler())
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=dummy)
        ser_obj = formatter.serialize(obj, route)
        self.assertDictEqual(ser_obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': 90,
                'b': 'this is a string'
            },
            'b': {
                formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                'ref': '"a"'
            }
        })

    def test_layered_duplicate(self):
        formatter = Formatter()
        formatter.register_symantec(AutoPreserveReferences(True))
        route = self.get_route(self.get_serialization_handler())
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        ser_obj = formatter.serialize(dummy3, route)
        #print(json.dumps(ser_obj, indent=4))
        self.assertDictEqual(ser_obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': {
                    formatter.settings.version_id: None,
                    formatter.settings.class_id: 'integrated_tests.Dummy',
                    'a': 90,
                    'b': 'this is a string'
                },
                'b': None
            },
            'b': {
                formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                'ref': '"a"."a"'
            }
        }, msg=str(json.dumps(ser_obj, indent=4)))


class TestRoundTrip(Scenarios):
    def test_basic(self):
        obj = self.get_basic()
        self.assert_obj_roundtrip(obj)

    def test_basic_versioned(self):
        obj = self.get_basic_versioned(version='1.0')
        self.assert_obj_roundtrip(obj)

    def test_nested_in_attribute(self):
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=99)
        self.assert_obj_roundtrip(obj)

    def test_nested_in_list(self):
        lis = [
            self.get_basic(a=90, b='this'),
            self.get_basic(a=0, b=False)
        ]
        obj = self.get_basic(a=lis, b=99)
        self.assert_obj_roundtrip(obj)

    def test_duplicate_in_attribute(self):
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=dummy)
        remade = self.assert_obj_roundtrip(obj)
        self.assertIs(remade.a, remade.b)

    def test_layered_duplicate(self):
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        remade = self.assert_obj_roundtrip(dummy3)
        self.assertIs(remade.a.a, remade.b)

    def test_duplicate_in_list(self):
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=[None, dummy], b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        remade = self.assert_obj_roundtrip(dummy3)
        self.assertIs(remade.a.a[1], remade.b)

class TestDeSerialization(Scenarios):
    def test_look_ahead_preserved_reference(self):
        formatter = Formatter()
        deser_obj = {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': '"b"'
                },
                'b': None
            },
            'b': {
                    formatter.settings.version_id: None,
                    formatter.settings.class_id: 'integrated_tests.Dummy',
                    'a': 90,
                    'b': 'this is a string'
                }
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b)

    def test_look_ahead_preserved_reference_in_list(self):
        formatter = Formatter()
        deser_obj = {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': '"b".1'
                },
                'b': None
            },
            'b': [None, {
                    formatter.settings.version_id: None,
                    formatter.settings.class_id: 'integrated_tests.Dummy',
                    'a': 90,
                    'b': 'this is a string'
                }]
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b[1])

    def test_look_ahead_preserved_reference_point_to_list(self):
        formatter = Formatter()
        deser_obj = {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': '"b"'
                },
                'b': None
            },
            'b': [None, 'hi']
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b)
        self.assertEqual(obj.b, [None, 'hi'])

    def test_look_ahead_preserved_reference_point_to_dict(self):
        formatter = Formatter()
        deser_obj = {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.Dummy',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.Dummy',
                'a': {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': '"b"'
                },
                'b': None
            },
            'b': {
                'a': None,
                'b': 'hi'
            }
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b)
        self.assertEqual(obj.b, {
                'a': None,
                'b': 'hi'
            })


if __name__ == '__main__':
    main()
