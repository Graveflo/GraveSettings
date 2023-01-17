# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from types import MethodType
from typing import get_type_hints
from unittest import TestCase, main

from grave_settings.handlers import OrderedHandler, OrderedMethodHandler





class TrackException(Exception):
    pass


class TestOrderedHandler(TestCase):
    def get_handler(self) -> OrderedHandler:
        return OrderedHandler()

    def test_add_method_by_type_hint(self):
        class Something:
            def test_method(self, something: int):
                raise TrackException()
        s = Something()
        oh = self.get_handler()
        oh.add_handlers_by_type_hints(s.test_method)
        with self.assertRaises(TrackException):
            oh.handle(5)

    def test_add_function_by_type_hint(self):
        oh = self.get_handler()

        def some_function(param1: int):
            raise TrackException()

        oh.add_handlers_by_type_hints(some_function)
        with self.assertRaises(TrackException):
            oh.handle(5)

class TestOrderedMethodHanlder(TestCase):
    def get_handler(self) -> OrderedMethodHandler:
        return OrderedMethodHandler()

    def test_add_method_by_type_hint_bound(self):
        rs = self

        class Something:
            def test_method(self, something: int):
                rs.assertIsInstance(self, Something)
                raise TrackException()

        s = Something()
        oh = self.get_handler()
        oh.add_handlers_by_type_hints(s.test_method)
        with self.assertRaises(TrackException):
            oh.handle(s, 5)

    def test_add_method_by_type_hint_unbound(self):
        rs = self

        class Something:
            def test_method(self, something: int):
                rs.assertIsInstance(self, Something)
                raise TrackException()

        s = Something()
        oh = self.get_handler()
        self.assertIsInstance(s.test_method, MethodType)
        oh.add_handlers_by_type_hints(Something.test_method)
        with self.assertRaises(TrackException):
            oh.handle(s, 5)


if __name__ == '__main__':
    main()
