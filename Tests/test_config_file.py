# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import json
import os
from pathlib import Path
from typing import Any, Type
from unittest import main

from observer_hooks import EventHandler
from ram_util.modules import format_class_str

from integration_tests_base import IntegrationTestCaseBase, Dummy, EmptyFormatter
from grave_settings.abstract import IASettings
from grave_settings.config_file import ConfigFile
from grave_settings.conversion_manager import ConversionManager
from grave_settings.formatter import Formatter, ProcessingException
from grave_settings.formatters.json import JsonFormatter
from grave_settings.semantics import SecurityException

TEST_FILE_PATH = Path('test_config_file.test')


class JsonFormatterIntegrationBase(IntegrationTestCaseBase):
    def get_formatter(self, serialization=True) -> JsonFormatter:
        return JsonFormatter()


class TestConfigFile(IntegrationTestCaseBase):
    def get_formatter(self) -> Formatter:
        return JsonFormatter()

    def get_config_file(self, file_path: Path, data: IASettings | Any | Type | None = None,
                 formatter: None | Formatter | str = None, auto_save=False, read_only=False) -> ConfigFile:
        if formatter is None:
            formatter = self.get_formatter()
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
        formatter = self.get_formatter()
        ser_obj = self.get_ser_obj(formatter, obj)
        with open(TEST_FILE_PATH, 'w') as f:
            f.write(json.dumps(ser_obj))

    def read_file_contents(self) -> str:
        with open(TEST_FILE_PATH, 'r') as f:
            return f.read()
#=============  THIS IS NO LONGER VALID ==================  TODO: make a test to sub
#    def test_instantiating_invalid_path_raises_error(self):
#        with self.assertRaises(Exception):
#            self.get_config_file(None)

    def test_exception_raised_with_path_is_none(self):
        c = self.get_config_file(TEST_FILE_PATH)
        with self.assertRaises(ValueError):
            c.load(path=None)

    def test_exception_raised_when_no_formatter(self):
        self.write_object_to_file(Dummy())
        c = self.get_config_file(TEST_FILE_PATH, Dummy)
        c.formatter = None
        with self.assertRaises(ValueError):
            c.load()

        c = self.get_config_file(TEST_FILE_PATH, Dummy())
        c.formatter = None
        with self.assertRaises(ValueError):
            c.load()

        c = self.get_config_file(TEST_FILE_PATH, Dummy)
        c.formatter = None
        with self.assertRaises(ValueError):
            c.save()

        c = self.get_config_file(TEST_FILE_PATH, Dummy())
        c.formatter = None
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
        with self.assertRaises(ProcessingException):
            c.load()

    def test_no_conversion_no_config_trigger(self):
        self.write_object_to_file(Dummy(a=1, b=1))
        c = self.get_config_file(TEST_FILE_PATH, Dummy, formatter=JsonFormatter())

        def sentenal_func(*args, **kwargs):
            self.assertTrue(False)
        c.deserializer_notify_settings_converted = EventHandler()
        c.deserializer_notify_settings_converted.subscribe(sentenal_func)
        c.load()

    def test_conversion_triggers_callback(self):
        class CustomDummy(Dummy):
            VERSION = '1.0.0'

            @classmethod
            def get_conversion_manager(cls) -> ConversionManager:
                cm = super().get_conversion_manager()
                cm.add_converter('0.1.0', CustomDummy, lambda x: x, '1.0.0')
                return cm
        globals()['CustomDummy'] = CustomDummy
        wd = CustomDummy(a=1, b=1)
        formatter = self.get_formatter()
        ser_obj = self.get_ser_obj(formatter, wd)
        ser_obj[formatter.spec.version_id][format_class_str(CustomDummy)] = '0.1.0'
        with open(TEST_FILE_PATH, 'w') as f:
            f.write(json.dumps(ser_obj))
        c = self.get_config_file(TEST_FILE_PATH, CustomDummy, formatter=JsonFormatter())

        class CustExc(Exception):
            pass

        def sentenal_func(*args, **kwargs):
            raise CustExc()

        c.backup_settings_file = EventHandler()
        c.backup_settings_file.subscribe(sentenal_func)
        with self.assertRaises(CustExc):
            c.load()
        globals().pop('CustomDummy')

    def test_serialize_logfile_with_link(self):
        cfg = self.get_config_file(TEST_FILE_PATH, data=Dummy())
        cfg2 = self.get_config_file(Path('test_config_2.test'), data=Dummy())
        cfg.data.a = cfg2.data
        cfg.add_config_dependency(cfg2, relative_path=False)
        cfg.save()

        remade_cfg = self.get_config_file(TEST_FILE_PATH, data=Dummy)
        remade_cfg.load()



if __name__ == '__main__':
    main()
