# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import json
import os
from pathlib import Path
from typing import Any, Type
from unittest import main

from Tests.integration_tests_base import IntegrationTestCaseBase, Dummy, EmptyFormatter
from grave_settings.abstract import IASettings
from grave_settings.config_file import ConfigFile
from grave_settings.formatter import Formatter
from grave_settings.formatters.json import JsonFormatter
from grave_settings.semantics import SecurityException

TEST_FILE_PATH = Path('test_config_file.test')


class JsonFormatterIntegrationBase(IntegrationTestCaseBase):
    def get_formatter(self, serialization=True) -> JsonFormatter:
        return JsonFormatter()


class TestConfigFile(IntegrationTestCaseBase):
    def get_config_file(self, file_path: Path, data: IASettings | Any | Type | None = None,
                 formatter: None | Formatter | str = None, auto_save=False, read_only=False) -> ConfigFile:
        return ConfigFile(file_path, data=data, formatter=formatter, auto_save=auto_save, read_only=read_only)

    def setUp(self) -> None:
        super().setUp()
        if TEST_FILE_PATH.exists():
            os.remove(TEST_FILE_PATH)

    def tearDown(self) -> None:
        super().tearDown()
        if TEST_FILE_PATH.exists():
            os.remove(TEST_FILE_PATH)

    def write_object_to_file(self, obj):
        formatter = self.get_formatter(serialization=True)
        ser_obj = self.get_ser_obj(formatter, obj)
        with open(TEST_FILE_PATH, 'w') as f:
            f.write(json.dumps(ser_obj))

    def read_file_contents(self) -> str:
        with open(TEST_FILE_PATH, 'r') as f:
            return f.read()

    def test_instantiating_invalid_path_raises_error(self):
        with self.assertRaises(Exception):
            self.get_config_file(None)

    def test_exception_raised_with_path_is_none(self):
        c = self.get_config_file(TEST_FILE_PATH)
        with self.assertRaises(ValueError):
            c.load(path=None)

    def test_exception_raised_when_no_formatter(self):
        c = self.get_config_file(TEST_FILE_PATH, Dummy)
        with self.assertRaises(ValueError):
            c.load()

        c = self.get_config_file(TEST_FILE_PATH, Dummy())
        with self.assertRaises(ValueError):
            c.load()

        c = self.get_config_file(TEST_FILE_PATH, Dummy)
        with self.assertRaises(ValueError):
            c.save()

        c = self.get_config_file(TEST_FILE_PATH, Dummy())
        with self.assertRaises(ValueError):
            c.save()

    def test_loading_file_not_exist_raises(self):
        c = self.get_config_file(TEST_FILE_PATH, Dummy, formatter=JsonFormatter())
        with self.assertRaises(ValueError):
            c.load()

        self.write_object_to_file(Dummy())
        c = self.get_config_file(TEST_FILE_PATH, Dummy, formatter=JsonFormatter())
        c.load()

    def test_file_read_write(self):
        self.write_object_to_file([1,2,3])
        text = self.read_file_contents()
        self.assertEqual(text, '[1, 2, 3]')

    def test_basic_load_file(self):
        self.write_object_to_file(Dummy(a=1, b=1))
        c = self.get_config_file(TEST_FILE_PATH, Dummy, formatter=JsonFormatter())
        c.load()
        self.assertIsInstance(c.data, Dummy)
        self.assertEqual(c.data.a, 1)
        self.assertEqual(c.data.b, 1)

    def test_type_in_data_enforced_deserialized_type(self):
        self.write_object_to_file(Dummy(a=1, b=1))
        class Foo:
            pass
        c = self.get_config_file(TEST_FILE_PATH, Foo, formatter=JsonFormatter())
        with self.assertRaises(SecurityException):
            c.load()

    def test_loading_write_file_path(self):
        self.write_object_to_file(Dummy(a=1, b=1))
        c = self.get_config_file(TEST_FILE_PATH, Dummy, formatter=JsonFormatter())
        with self.assertRaises(SecurityException):
            c.load()
        self.assertEqual(c.data.file_path, str(TEST_FILE_PATH))



if __name__ == '__main__':
    main()
