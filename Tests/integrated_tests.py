# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import json
from unittest import TestCase, main

from ram_util.utilities import OrderedHandler

from grave_settings.abstract import Serializable
from grave_settings.base import SlotSettings
from grave_settings.default_handlers import JsonSerializationHandler
from grave_settings.fmt_util import Route
from grave_settings.formatter import Formatter, AutoPreserveReferences


class TestSerialization(TestCase):
    def get_basic(self, a=90, b='this is a string') -> Serializable:
        class S(SlotSettings):
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = a
                self.b = b
        return S()

    def get_basic_versioned(self, a=90, b='this is a string', version=None) -> Serializable:
        class S(SlotSettings):
            VERSION = version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = a
                self.b = b
        return S()

    def get_nested_in_attribute(self, s_a=90, s_b='this is a string', a_b=99, s_version=None, a_version=None) -> Serializable:
        class S(SlotSettings):
            VERSION = s_version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = s_a
                self.b = s_b

        class A(SlotSettings):
            VERSION = a_version
            __slots__ = 'a', 'b'
            def __init__(self):
                super().__init__()
                self.a = S()
                self.b = a_b
        return A()

    def get_nested_in_list(self,s_a=90, s_b='this is a string', a_b=99, s_version=None, a_version=None) -> Serializable:
        class S(SlotSettings):
            VERSION = s_version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = s_a
                self.b = s_b

        class A(SlotSettings):
            VERSION = a_version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = [S(), S()]
                self.b = a_b

        return A()

    def get_duplicate_reference_attribute(self, s_a=90, s_b='this is a string', a_b=99, s_version=None, a_version=None) -> Serializable:
        class S(SlotSettings):
            VERSION = s_version
            __slots__ = 'a', 'b'

            def __init__(self):
                super().__init__()
                self.a = s_a
                self.b = s_b

        class A(SlotSettings):
            VERSION = a_version
            __slots__ = 'a', 'b', 'a2'

            def __init__(self):
                super().__init__()
                self.a = S()
                self.a2 = self.a
                self.b = a_b
        return A()

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

        return A()

    def get_serialization_handler(self) -> OrderedHandler:
        return JsonSerializationHandler()

    def get_route(self, handler: OrderedHandler) -> Route:
        return Route(handler)

    def test_basic(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = formatter.serialize(self.get_basic(), route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.S',
            'a': 90,
            'b': 'this is a string'
        })

    def test_basic_versioned(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = formatter.serialize(self.get_basic_versioned(version='1.0'), route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: '1.0',
            formatter.settings.class_id: 'integrated_tests.S',
            'a': 90,
            'b': 'this is a string'
        })

    def test_nested_in_attribute(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = self.get_nested_in_attribute(s_a=90, s_b='this is a string', s_version='1.0', a_b=99, a_version=None)
        obj = formatter.serialize(obj, route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.A',
            'a': {
                formatter.settings.version_id: '1.0',
                formatter.settings.class_id: 'integrated_tests.S',
                'a': 90,
                'b': 'this is a string'
            },
            'b': 99
        })

    def test_nested_in_list(self):
        formatter = Formatter()
        route = self.get_route(self.get_serialization_handler())
        obj = self.get_nested_in_list(s_a=90, s_b='this is a string', s_version='1.0', a_b=99, a_version=None)
        obj = formatter.serialize(obj, route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.A',
            'a': [{
                formatter.settings.version_id: '1.0',
                formatter.settings.class_id: 'integrated_tests.S',
                'a': 90,
                'b': 'this is a string'
            },{
                formatter.settings.version_id: '1.0',
                formatter.settings.class_id: 'integrated_tests.S',
                'a': 90,
                'b': 'this is a string'
            }],
            'b': 99
        })

    def test_duplicate_in_attribute(self):
        formatter = Formatter()
        formatter.register_symantec(AutoPreserveReferences())
        route = self.get_route(self.get_serialization_handler())
        obj = self.get_duplicate_reference_attribute(s_a=90, s_b='this is a string', s_version='1.0', a_b=99,
                                                     a_version=None)
        obj = formatter.serialize(obj, route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.A',
            'a': {
                formatter.settings.version_id: '1.0',
                formatter.settings.class_id: 'integrated_tests.S',
                'a': 90,
                'b': 'this is a string'
            },
            'a2': {
                formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                'ref': 'a'
            },
            'b': 99
        })

    def test_layered_duplicate(self):
        formatter = Formatter()
        formatter.register_symantec(AutoPreserveReferences())
        route = self.get_route(self.get_serialization_handler())
        obj = self.get_layered_duplicate()
        obj = formatter.serialize(obj, route)
        self.assertDictEqual(obj, {
            formatter.settings.version_id: None,
            formatter.settings.class_id: 'integrated_tests.A',
            'a': {
                formatter.settings.version_id: None,
                formatter.settings.class_id: 'integrated_tests.S',
                'a': 0
            },
            'x': 90,
            'b':[{
                    formatter.settings.version_id: None,
                    formatter.settings.class_id: 'integrated_tests.C'
                }, 2,
                {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': 'a'
                },
                {
                    formatter.settings.version_id: None,
                    formatter.settings.class_id: 'integrated_tests.S',
                    'a': 0
                },
                {
                    formatter.settings.class_id: 'grave_settings.fmt_util.PreservedReference',
                    'ref': 'a'
                }
            ]
        }, msg=str(json.dumps(obj, indent=4)))



if __name__ == '__main__':
    main()
