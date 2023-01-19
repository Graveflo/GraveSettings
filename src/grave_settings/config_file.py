# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Self, Any, Type

from observer_hooks import EventCapturer
from ram_util.modules import format_class_str

from grave_settings.abstract import IASettings, VersionedSerializable
from grave_settings.formatter_settings import FormatterContext
from grave_settings.formatters.toml import TomlFormatter
from grave_settings.formatters.json import JsonFormatter
from grave_settings.formatter import Formatter, DeSerializer
from grave_settings.semantics import ClassStringPassFunction



class ConfigFile:
    FORMATTER_STR_DICT = {
        'json': JsonFormatter(),
        'toml': TomlFormatter()
    }

    def __init__(self, file_path: Path, data: IASettings | Any | Type | None = None,
                 formatter: None | Formatter | str = None, auto_save=False, read_only=False):
        if type(formatter) == str:
            formatter = self.FORMATTER_STR_DICT[formatter]
        self.file_path = file_path.resolve().absolute()
        self.data = data
        self.auto_save = auto_save
        self.formatter = formatter
        self.changes_made = not isinstance(data, IASettings)
        self.read_only = read_only
        self.sub_configs = {}

    def add_config_dependency(self, other: 'ConfigFile'):
        self.sub_configs[other.file_path] = other

    def backup_settings_file(self):
        if self.file_path.is_file():
            base = self.file_path.parent
            dt_n = datetime.now().strftime('%Y_%m_%d %H%M')
            backup_path = base / f"{self.file_path.stem}_backup_{dt_n}{self.file_path.suffix}"
            shutil.copyfile(str(self.file_path), str(backup_path))

    def deserializer_notify_settings_converted(self, processor: DeSerializer, conversion_type: Type[VersionedSerializable]):
        self.backup_settings_file()

    def settings_invalidated(self):
        self.changes_made = True
        if self.auto_save:
            self.save()

    def validate_file_path(self, path: Path, must_exist=False):
        if must_exist:
            if not path.exists():
                raise ValueError(f'Path does not exist: {path}')
        if path.exists() and (not os.access(path, os.R_OK)):
            raise ValueError(f'Do not have permission to write to: {path}')
        if not self.read_only:
            if path.exists() and (not os.access(path, os.W_OK)):
                raise ValueError(f'Do not have permission to write to: {path}')
        if path.exists() and (not path.is_file()):
            raise ValueError(f'File path is invalid: {path}')

    def save(self, path: Path = None, formatter: None | Formatter = None, force=True, validate_path=True):
        if self.read_only:
            raise ValueError('Saving in read-only mode')
        if path is None:
            path = self.file_path
            vf = self.changes_made
        elif (not force) and self.changes_made and hasattr(self.data, 'invalidate'):
            return
        else:
            vf = False
        if validate_path:
            self.validate_file_path(path)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        formatter.write_to_file(self.data, str(self.file_path))
        self.changes_made = vf

    def load(self, path: Path = None, formatter: None | Formatter = None, validate_path=True):
        if path is None:
            path = self.file_path
        if validate_path:
            self.validate_file_path(path, must_exist=True)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        context = self.formatter.get_deserialization_context()
        deserializer = self.formatter.get_deserializer(None, context)
        self.check_in_deserialization_context(context)
        with EventCapturer(deserializer.notify_settings_converted) as capture:
            self.data = formatter.read_from_file(str(path), deserializer=deserializer)
        if len(capture) > 0:
            self.backup_settings_file()
        if isinstance(self.data, IASettings):
            self.data.file_path = self.file_path
        self.changes_made = False

    def check_in_deserialization_context(self, context: FormatterContext):
        if isinstance(self.data, type):
            context.add_frame_semantic(ClassStringPassFunction(lambda x: x == format_class_str(self.data)))

    def instantiate_data(self):
        return self.data()

    def __enter__(self) -> Self:
        try:
            self.validate_file_path(self.file_path, must_exist=True)
            load = True
        except ValueError:
            load = False
        if load:
            self.load(validate_path=False)
        elif isinstance(self.data, type):
            self.data = self.instantiate_data()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.read_only:
            self.save()
