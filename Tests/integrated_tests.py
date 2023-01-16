# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import json
from datetime import timedelta, datetime, date
from enum import Enum, auto
from unittest import TestCase, main

from ram_util.modules import format_class_str
from grave_settings.formatter_settings import PreservedReference, Temporary, NoRef
from integration_tests_base import Dummy, IntegrationTestCaseBase
from grave_settings.abstract import Serializable
from grave_settings.base import SlotSettings
from grave_settings.semantics import *


class AssertsSerializable(Serializable):
    def assert_object_equiv(self, other: Self):
        pass


class SampleEnum(Enum):
    THIS = auto()
    IS = auto()
    ENUM = auto()


def some_function():
    pass


class SomeSerializable(Serializable):
    def __init__(self):
        self.memeber = 'this is a string'
        self.auto_member = Dummy(a=some_function, b=5)

    def __eq__(self, other):
        if self.memeber != other.memeber:
            return False
        if self.auto_member != other.auto_member:
            return False
        return True


class PyObjectTest:
    def __init__(self):
        self.time = datetime.now()
        self.my_type = self.__class__

    def __eq__(self, other):
        if self.time != other.time:
            return False
        if self.my_type != other.my_type:
            return False
        return True


class DefaultHandlerObj(Dummy):
    __slots__ = ('type_keys', 'some_dict', 'literal_type', 'tuple', 'datetime', 'some_enum', 'serializable',
                 'pyobject')

    def __init__(self):
        super().__init__()
        self.type_keys = {
            timedelta: timedelta(hours=1, seconds=10, microseconds=100),
            Dummy: set([1, 2, 3, 4, 5])
        }
        self.some_dict = {
            1: Dummy(a=Dummy(), b=self),
            2: self.type_keys[Dummy]
        }
        self.literal_type = AssertsSerializable
        self.tuple = ('this', 'is', 'a', 'tuple')
        self.datetime = datetime(year=2022, month=1, day=1, hour=10, minute=1, second=5)
        self.some_enum = SampleEnum.ENUM
        self.serializable = SomeSerializable()
        self.pyobject = PyObjectTest()

    def assert_dict_attr_equiv(self, tc: TestCase, self_dict:dict, other_dict:dict, circle=None):
        for k,v in self_dict.items():
            other_v = other_dict[k]
            self.assert_attr_equiv(tc, v, other_v, circle=circle)

    def assert_object_equiv(self, tc: TestCase, other: Self, circle=None):
        if circle is None:
            circle = set()
        super().assert_object_equiv(tc, other, circle=circle)
        self.assert_dict_attr_equiv(tc, self.type_keys, other.type_keys, circle=circle)
        self.assert_dict_attr_equiv(tc, self.some_dict, other.some_dict, circle=circle)
        tc.assertIs(self.type_keys[Dummy], self.some_dict[2])
        tc.assertIs(other.type_keys[Dummy], other.some_dict[2])

        tc.assertIs(self.some_dict[1].b, self)
        tc.assertIs(other.some_dict[1].b, other)


class Scenarios(IntegrationTestCaseBase):
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


class TestSerialization(Scenarios):
    def test_basic(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        obj = formatter.serialize(self.get_basic())
        self.assertDictEqual(obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': 90,
            'b': 'this is a string'
        })

    def test_basic_versioned(self):
        formatter = self.get_formatter(serialization=True)
        obj = formatter.serialize(self.get_basic_versioned(version='1.0'))
        self.assertDictEqual(obj, {
            formatter.spec.version_id: {'integrated_tests.DummyVersioned': '1.0'},
            formatter.spec.class_id: 'integrated_tests.DummyVersioned',
            'a': 90,
            'b': 'this is a string'
        })

    def test_nested_in_attribute(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=99)
        ser_obj = formatter.serialize(obj)
        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': 90,
                'b': 'this is a string'
            },
            'b': 99
        })

    def test_nested_in_list(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        lis = [
            self.get_basic(a=90, b='this'),
            self.get_basic(a=0, b=False)
        ]
        obj = self.get_basic(a=lis, b=99)
        ser_obj = formatter.serialize(obj)
        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': [{
                formatter.spec.class_id: format_class_str(Dummy),
                'a': 90,
                'b': 'this'
            }, {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': 0,
                'b': False
            }],
            'b': 99
        })

    def test_duplicate_in_attribute(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(AutoPreserveReferences(True))
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        dummy = self.get_basic(a=90, b='this is a string')
        obj = self.get_basic(a=dummy, b=dummy)
        ser_obj = formatter.serialize(obj)
        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': 90,
                'b': 'this is a string'
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"'
            }
        })

    def test_layered_duplicate(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(AutoPreserveReferences(True))
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        ser_obj = formatter.serialize(dummy3)

        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': 'this is a string'
                },
                'b': None
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"."a"'
            }
        }, msg=str(json.dumps(ser_obj, indent=4)))

    def test_circular_reference(self):
        formatter = self.get_formatter(serialization=True)
        formatter.semantics.add_semantic(AutoPreserveReferences(True))
        formatter.semantics.add_semantic(SerializeNoneVersionInfo(False))
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        dummy.b = dummy2

        ser_obj = formatter.serialize(dummy3)

        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': {
                        formatter.spec.class_id: format_class_str(PreservedReference),
                        'ref': '"a"'
                    }
                },
                'b': None
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"."a"'
            }
        }, msg=str(json.dumps(ser_obj, indent=4)))

    def test_circular_reference_beginning(self):
        formatter = self.get_formatter(serialization=True)
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        dummy.b = dummy3

        ser_obj = formatter.serialize(dummy3)

        self.assertDictEqual(ser_obj, {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': {
                        formatter.spec.class_id: format_class_str(PreservedReference),
                        'ref': ''
                    }
                },
                'b': None
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"."a"'
            }
        }, msg=str(json.dumps(ser_obj, indent=4)))

    def test_serialization_doesnt_damage_obj_state(self):
        dummy = Dummy(a=[Dummy(), Dummy()], b={
                    date(year=2022, month=1, day=1): Dummy()
                })
        formatter = self.get_formatter(serialization=True)
        formatter.serialize(dummy)
        self.assertIs(type(dummy.a[0]), Dummy)
        self.assertIs(type(dummy.a[1]), Dummy)
        self.assertIn(date(year=2022, month=1, day=1), dummy.b)
        self.assertIs(type(dummy.b[date(year=2022, month=1, day=1)]), Dummy)

    def test_temporary(self):
        formatter = self.get_formatter(serialization=True)
        dummy_ref = [Dummy(a=1, b=1), Dummy(a=2, b=2)]
        dummy = Dummy(a=Temporary(dummy_ref), b=Temporary(dummy_ref))
        result = formatter.serialize(dummy)
        self.assertEqual(result['a'], result['b'])
        self.assertIs(result['b'][0], dummy_ref[0])
        self.assertEqual(dummy_ref[0][formatter.spec.class_id], format_class_str(Dummy))

    def test_noref(self):
        formatter = self.get_formatter(serialization=True)
        dummy_ref = Dummy(a=1, b=1)
        dummy = Dummy(a=NoRef(dummy_ref), b=NoRef(dummy_ref))
        result = formatter.serialize(dummy)
        self.assertEqual(result['a'], result['b'])
        self.assertEqual(result['b'][formatter.spec.class_id], format_class_str(Dummy))
        self.assertEqual(result['a'][formatter.spec.class_id], format_class_str(Dummy))

        formatter = self.get_formatter(serialization=True)
        dummy_ref = Dummy(a=1, b=1)
        dummy = {
            'a': NoRef(dummy_ref),
            'b': NoRef(dummy_ref)
        }
        result = formatter.serialize(dummy)
        self.assertEqual(result['a'], result['b'])
        self.assertEqual(result['b'][formatter.spec.class_id], format_class_str(Dummy))
        self.assertEqual(result['a'][formatter.spec.class_id], format_class_str(Dummy))


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

    def test_circular_reference(self):
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        dummy.b = dummy2
        remade = self.assert_obj_roundtrip(dummy3)
        self.assertIs(remade.a.a.b, remade.a)

    def test_circular_reference_beginning(self):
        dummy = self.get_basic(a=90, b='this is a string')
        dummy2 = self.get_basic(a=dummy, b=None)
        dummy3 = self.get_basic(a=dummy2, b=dummy)
        dummy.b = dummy3
        remade = self.assert_obj_roundtrip(dummy3)
        self.assertIs(remade.a.a.b, remade)

    def test_all_default_handlers(self):
        obj = DefaultHandlerObj()
        self.assert_obj_roundtrip(obj)


class TestDeSerialization(Scenarios):
    def test_look_ahead_preserved_reference(self):
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.version_id: None,
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.version_id: None,
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(PreservedReference),
                    'ref': '"b"'
                },
                'b': None
            },
            'b': {
                    formatter.spec.version_id: None,
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': 'this is a string'
                }
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b)

    def test_look_ahead_preserved_reference_in_list(self):
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.version_id: None,
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.version_id: None,
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(PreservedReference),
                    'ref': '"b".1'
                },
                'b': None
            },
            'b': [None, {
                    formatter.spec.version_id: None,
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': 'this is a string'
                }]
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a.a, obj.b[1])

    def test_look_ahead_preserved_reference_point_to_list(self):
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.version_id: None,
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.version_id: None,
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(PreservedReference),
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
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.version_id: None,
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.version_id: None,
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(PreservedReference),
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

    def test_circular_reference(self):
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': {
                        formatter.spec.class_id: format_class_str(PreservedReference),
                        'ref': '"a"'
                    }
                },
                'b': None
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"."a"'
            }
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj.a, obj.a.a.b)
        self.assertIs(obj.b, obj.a.a)
        self.assertEqual(obj.a.a.a, 90)

    def test_circular_reference_beginning(self):
        formatter = self.get_formatter(serialization=False)
        deser_obj = {
            formatter.spec.class_id: format_class_str(Dummy),
            'a': {
                formatter.spec.class_id: format_class_str(Dummy),
                'a': {
                    formatter.spec.class_id: format_class_str(Dummy),
                    'a': 90,
                    'b': {
                        formatter.spec.class_id: format_class_str(PreservedReference),
                        'ref': ''
                    }
                },
                'b': None
            },
            'b': {
                formatter.spec.class_id: format_class_str(PreservedReference),
                'ref': '"a"."a"'
            }
        }
        obj = self.deser_ser_obj(deser_obj)
        self.assertIs(obj, obj.a.a.b)
        self.assertIs(obj.b, obj.a.a)
        self.assertEqual(obj.a.a.a, 90)

    def test_can_remake_pyobject_with_new(self):
        class RGB:
            def __init__(self, r, g, b):
                self.r = r
                self.g = g
                self.b = b

        r = RGB(255, 245, 225)
        globals()['RGB'] = RGB
        try:
            json_formatter = self.get_formatter(serialization=True)
            s = json_formatter.serialize(r)
            json_formatter = self.get_formatter(serialization=False)
            remade_object = json_formatter.deserialize(s)

            self.assertTrue(hasattr(remade_object, 'r'))
            self.assertTrue(hasattr(remade_object, 'g'))
            self.assertTrue(hasattr(remade_object, 'b'))
            self.assertEqual(remade_object.r, 255)
            self.assertEqual(remade_object.g, 245)
            self.assertEqual(remade_object.b, 225)
        finally:
            globals().pop('RGB')


if __name__ == '__main__':
    main()
