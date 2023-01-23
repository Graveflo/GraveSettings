# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from fractions import Fraction
from zoneinfo import ZoneInfo
import datetime
from enum import Enum, auto
from functools import partial
from unittest import TestCase, main
from grave_settings.formatter_settings import FormatterContext, FormatterSpec
from grave_settings.default_handlers import SerializationHandler, DeSerializationHandler, NotSerializableException
from grave_settings.framestack_context import FrameStackContext
from grave_settings.semantics import *
from grave_settings.formatter import Serializer, DeSerializer, ProcessingException


def test_function(arg1, arg2, name=None):
    pass


class SomeEnum(Enum):
    VAL = auto()
    VLO = auto()


class ClassFoo:
    def some_method(self):
        pass


class TestHandler(TestCase):
    def get_semantics(self):
        return Semantics({
            AutoPreserveReferences: AutoPreserveReferences(True),
            ResolvePreservedReferences: ResolvePreservedReferences(True)
        })
    def get_serialization_handler(self):
        return SerializationHandler()

    def get_deserialization_handler(self):
        return DeSerializationHandler()

    def get_formatter_context(self, serialization=True):
        if serialization:
            return FormatterContext(FrameStackContext(self.get_serialization_handler(), self.get_semantics()))
        else:
            return FormatterContext(FrameStackContext(self.get_deserialization_handler(), self.get_semantics()))

    def get_spec(self) -> FormatterSpec:
        return FormatterSpec()

    def get_serializer(self, root_obj, context):
        return Serializer(root_obj, self.get_spec(), context)

    def get_deserializer(self, root_obj, context):
        return DeSerializer(root_obj, self.get_spec(), context)

    def serialize(self, obj):
        ser_context = self.get_formatter_context(serialization=True)
        with self.get_serializer(obj, ser_context) as ser:
            return ser.serialize(obj)

    def deserialize(self, obj):
        deser_context = self.get_formatter_context(serialization=False)
        with self.get_deserializer(obj, deser_context) as deser:
            return deser.deserialize(obj)

    def assert_make_remake(self, obj):
        output = self.serialize(obj)
        remade = self.deserialize(output)
        self.assertEqual(remade, obj)

    def test_bytes(self):
        self.assert_make_remake('This is a test'.encode('utf-8'))

    def test_partial(self):
        output = self.serialize(partial(test_function, 1, 2, name=3))
        remade = self.deserialize(output)
        self.assertIs(remade.func, test_function)
        self.assertSequenceEqual(remade.args, (1,2))
        self.assertDictEqual(remade.keywords, {
            'name': 3
        })

    def test_enum(self):
        self.assert_make_remake(SomeEnum.VLO)

    def test_lambda(self):
        with self.assertRaises(ProcessingException):
            self.serialize(lambda: None)

    def test_method(self):
        obj = ClassFoo()
        output = self.serialize((obj, obj.some_method))
        remade = self.deserialize(output)
        self.assertEqual(remade[0].some_method, remade[1])

    def test_class(self):
        self.assert_make_remake(ClassFoo)

    def test_date(self):
        self.assert_make_remake(datetime.date(year=2022, day=1, month=1))

    def test_time_delta(self):
        self.assert_make_remake(datetime.timedelta(seconds=54))

    def test_datetime_niave(self):
        dt = datetime.datetime.now()
        self.assert_make_remake(dt)

    def test_date_time_tzinfo(self):
        dt = datetime.datetime.now().astimezone()
        self.assert_make_remake(dt)

    def test_datetime_zoneinfo(self):
        dt = datetime.datetime.now().astimezone(ZoneInfo('America/Los_Angeles'))
        self.assert_make_remake(dt)

    def test_fraction(self):
        self.assert_make_remake(Fraction(1, 10))

    def test_complex(self):
        self.assert_make_remake(complex(5,3))


if __name__ == '__main__':
    main()
