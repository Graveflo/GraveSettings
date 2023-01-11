from unittest import TestCase

from grave_settings.abstract import Route
from grave_settings.formatter import Formatter
from grave_settings.semantics import *

from integration_tests_base import IntegrationTestCaseBase, Dummy


class TestFormatter(TestCase):
    def test_path_formatting(self):
        formatter = Formatter()
        path = formatter.settings.str_to_path("")
        self.assertIs(type(path), list)
        self.assertListEqual(path, [])

        formatter.key_path = []
        str_path = formatter.path_to_str()
        self.assertEqual(str_path, '')


class TestSemantics(IntegrationTestCaseBase):
    def test_class_can_disallow_preserved_refs(self):
        class NonSerializableDummy(Dummy):
            @classmethod
            def check_in_serialization_route(cls, route: Route):
                route.add_frame_semantic(AutoPreserveReferences(False))
        globals()['NonSerializableDummy'] = NonSerializableDummy
        try:
            inner_dummy = NonSerializableDummy()
            dummy = Dummy(a=inner_dummy, b=inner_dummy)

            remade = self.assert_obj_roundtrip(dummy, test_equiv=False)
            self.assertIs(type(remade), Dummy)
            self.assertIs(type(remade.a), NonSerializableDummy)
            self.assertIs(type(remade.b), NonSerializableDummy)
            self.assertIsNot(remade.a, remade.b)
        finally:
            globals().pop('NonSerializableDummy')
