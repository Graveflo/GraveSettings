import json
from typing import Self
from unittest import TestCase

from grave_settings.handlers import OrderedHandler
from grave_settings.base import SlotSettings
from grave_settings.default_handlers import SerializationHandler, DeSerializationHandler
from grave_settings.framestackcontext import FrameStackContext
from grave_settings.formatter import Formatter
from grave_settings.semantics import *
from grave_settings.semantics import NotifyFinalizedMethodName


class EmptyFormatter(Formatter):
    def serialized_obj_to_buffer(self, ser_obj) -> str | bytes:
        raise Exception()

    def buffer_to_obj(self, buffer: str | bytes):
        raise Exception()


class Dummy(SlotSettings):
    __slots__ = 'a', 'b'

    def __init__(self, a=None, b=None):
        super().__init__()
        self.a = a
        self.b = b

    @classmethod
    def check_in_deserialization_context(cls, route: FrameStackContext):
        route.add_frame_semantic(NotifyFinalizedMethodName('finalize'))

    def assert_attr_equiv(self, tc: TestCase, self_val, other_val, circle=None):
        if circle is None:
            circle = set()
        tc.assertIs(type(self_val), type(other_val))
        if isinstance(other_val, Dummy):
            if self_val not in circle:
                self_val.assert_object_equiv(tc, other_val, circle=circle)
        else:
            tc.assertEqual(other_val, other_val)

    def assert_object_equiv(self, tc: TestCase, other: Self, circle=None):
        if circle is None:
            circle = set()
        circle.add(self)

        for attr in self.get_settings_keys():
            other_val = getattr(other, attr)
            self_val = getattr(self, attr)
            self.assert_attr_equiv(tc, self_val, other_val, circle=circle)

    def get_settings_keys_base_slots(self):  # Keep order consistent
        return self.__slots__


class IntegrationTestCaseBase(TestCase):
    def get_formatter(self, serialization=True) -> Formatter:
        f = EmptyFormatter()
        return f

    def get_serialization_handler(self) -> OrderedHandler:
        return SerializationHandler()

    def get_deserialization_handler(self) -> OrderedHandler:
        return DeSerializationHandler()

    def get_ser_obj(self, formatter, obj):
        return formatter.serialize(obj)

    def assert_obj_roundtrip(self, obj, test_equiv=True):
        formatter = self.get_formatter(serialization=True)
        ser_obj = self.get_ser_obj(formatter, obj)
        #print(json.dumps(ser_obj, indent=4))
        re_made_object = self.deser_ser_obj(ser_obj)
        #print(re_made_object)
        if test_equiv:
            obj.assert_object_equiv(self, re_made_object)
        self.assertIsNot(obj, re_made_object)
        return re_made_object

    def deser_ser_obj(self, ser_obj):
        formatter = self.get_formatter(serialization=False)
        re_made_object = self.formatter_deser(formatter, ser_obj)
        return re_made_object

    def formatter_deser(self, formatter, ser_obj):
        return formatter.deserialize(ser_obj)

