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

from grave_settings.conversion_manager import get_descendent_class_formats
from grave_settings.utilities import format_class_str, generate_type_hierarchy_to_base
from grave_settings.abstract import IASettings, Serializable
from grave_settings.formatter_settings import FormatterContext
from grave_settings.formatters.toml import TomlFormatter
from grave_settings.formatters.json import JsonFormatter
from grave_settings.formatter import Formatter, DeSerializer, Serializer
from grave_settings.handlers import OrderedHandler
from grave_settings.semantics import ClassStringPassFunction, Semantics, Semantic, SecurityException


class PassLogFilePath(Semantic[str]):
    pass


class LogFileLink(Serializable):
    def __init__(self, config=None, file_path=None, rel_path=None):
        self.file_path = file_path
        self.rel_path = rel_path
        self.config: ConfigFile = config

    def to_dict(self, context: FormatterContext, **kwargs) -> dict:
        if self.rel_path is None:
            if self.file_path is None:
                raise AttributeError()
            pt_name = 'path'
            path = self.file_path
        else:
            pt_name = 'rel_path'
            path = self.rel_path
        return {
            pt_name: path,
            'config': self.config
        }

    def from_dict(self, state_obj: dict, context: FormatterContext, **kwargs):
        if 'rel_path' in state_obj:
            self.rel_path = state_obj['rel_path']
        else:
            self.file_path = state_obj['path']
        self.config = state_obj['config']


class ConfigFile(Serializable):
    FORMATTER_STR_DICT = {
        'json': JsonFormatter,
        'toml': TomlFormatter
    }
    FORMATTER_PREFERRED_EXT: dict[type, str] = {
        JsonFormatter: 'json',
        TomlFormatter: 'toml'
    }  # Might seem redundant but FORMATTER_STR_DICT values might not be types

    def __init__(self, file_path: Path, data: IASettings | Any | Type | None = None,
                 formatter: None | Formatter | str = None, auto_save=False, read_only=False):
        if file_path is not None:
            if formatter is None:
                formatter = file_path.suffix.lower()
                if formatter.startswith('.'):
                    formatter = formatter[1:]
            file_path = file_path.resolve().absolute()
        if type(formatter) == str:
            formatter = self.guess_formatter_from_str(formatter)()
        self.file_path = file_path
        self.data = data
        self.save_on_invalidate = auto_save
        self.formatter = formatter
        self.changes_made = not isinstance(data, IASettings)
        self.track_changes = self.changes_made
        self.read_only = read_only
        self.sub_configs: dict[Any, LogFileLink] = {}
        self.sub_config_paths: dict[Path, Any] = {}

    def set_file_path(self, path: Path):
        self.file_path = path

    @classmethod
    def guess_file_type(cls, formatter: Formatter):
        for t in generate_type_hierarchy_to_base(object, formatter.__class__):
            if t in cls.FORMATTER_PREFERRED_EXT:
                return cls.FORMATTER_PREFERRED_EXT[t]

    @classmethod
    def guess_formatter_from_str(cls, short_name: str):
        return cls.FORMATTER_STR_DICT[short_name]

    def add_config_dependency(self, other: 'ConfigFile', relative_path=True):
        if not other.is_loaded():
            raise ValueError('Only add config files after they have been loaded or set their data object properly')
        if relative_path:
            log_file_link = LogFileLink(config=other, rel_path=other.file_path.relative_to(self.file_path.parent))
        else:
            log_file_link = LogFileLink(config=other, file_path=other.file_path)
        self.add_log_file_link(log_file_link)

    def add_log_file_link(self, link: LogFileLink):
        other = link.config
        if other.file_path in self.sub_config_paths:
            self.sub_configs.pop(self.sub_config_paths[other.file_path])
        self.sub_configs[other.data] = link
        self.sub_config_paths[other.file_path] = other.data

    def is_loaded(self):
        return self.data is not None and not isinstance(self.data, type)

    def backup_settings_file(self):
        if self.file_path.is_file():
            base = self.file_path.parent
            dt_n = datetime.now().strftime('%Y_%m_%d %H%M')
            backup_path = base / f"{self.file_path.stem}_backup_{dt_n}{self.file_path.suffix}"
            shutil.copyfile(str(self.file_path), str(backup_path))

    def settings_invalidated(self):
        self.changes_made = True
        if self.save_on_invalidate:
            self.save()

    def validate_file_path(self, path: Path, must_exist=False, test_if_file=True):
        if self.file_path is None:
            raise ValueError('File path not specified')
        if must_exist:
            if not path.exists():
                raise ValueError(f'Path does not exist: {path}')
        if path.exists() and (not os.access(path, os.R_OK)):
            raise ValueError(f'Do not have permission to write to: {path}')
        if not self.read_only:
            if path.exists() and (not os.access(path, os.W_OK)):
                raise ValueError(f'Do not have permission to write to: {path}')
        if test_if_file and path.exists() and (not path.is_file()):
            raise ValueError(f'File path is invalid: {path}')

    def save(self, path: Path = None, formatter: None | Formatter = None, force=True, validate_path=True):
        if self.read_only:
            raise ValueError('Saving in read-only mode')
        if path is None:
            path = self.file_path
            vf = self.changes_made
        elif (not force) and (not self.changes_made) and self.track_changes:
            return
        else:
            vf = False
        if validate_path:
            self.validate_file_path(path)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        serializer = self.formatter.get_serializer(self.data, self.get_serialization_context())
        serializer.handler.type_bank[object] = self.handle_serialize_object
        #serializer.handler.add_handler(IASettings, self.handle_serialize_IASettings)
        formatter.write_to_file(self.data, str(self.file_path), serializer=serializer)
        self.changes_made = vf

    @classmethod
    def check_in_serialization_context(cls, context: FormatterContext):
        pass

    def get_serialization_context(self):
        return self.formatter.get_serialization_context()

    def handle_serialize_object(self, serializer: Serializer, obj: IASettings, **kwargs):
        if obj in self.sub_configs:
            link = self.sub_configs[obj]
            link.config.save()
            return serializer.handle_default(link)
        else:
            return serializer.handle_default(obj, **kwargs)

    def load(self, path: Path = None, formatter: None | Formatter = None, validate_path=True, semantics: Semantics = None):
        if path is None:
            path = self.file_path
        if validate_path:
            self.validate_file_path(path, must_exist=True)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        context = self.get_deserialization_context()
        deserializer = self.formatter.get_deserializer(None, context)
        deserializer.secondary_handler.add_handler(LogFileLink, self.handle_deserialize_LogFileLink)
        if semantics is not None:
            context.semantic_context.semantics.update(semantics)
        with EventCapturer(deserializer.notify_settings_converted) as capture:
            self.data = formatter.read_from_file(str(path), deserializer=deserializer)
        if len(capture) > 0:
            self.backup_settings_file()
        self.changes_made = False

    @classmethod
    def check_in_deserialization_context(cls, context: FormatterContext):
        handler = OrderedHandler()
        handler.add_handler(ConfigFile, cls.handle_me)
        context.semantic_context.set_handler(handler, update_order=True)

    def get_deserialization_context(self):
        context = self.formatter.get_deserialization_context()
        found_init = False
        def descriptive_error(class_string: str):
            if class_string in format_class_str(self.data):
                return True
            elif found_init:
                if class_string in get_descendent_class_formats(self.data):  # TODO: This is not functional
                    return True
            raise SecurityException(f'{class_string} does not match correct class string {format_class_str(self.data)}')
        if isinstance(self.data, type):
            context.add_frame_semantics(ClassStringPassFunction(descriptive_error))
        return context

    def handle_deserialize_LogFileLink(self, deserializer: DeSerializer, obj: LogFileLink, **kwargs):
        if obj.file_path is not None:
            obj.config.file_path = obj.file_path.absolute()
        else:
            obj.config.file_path = obj.rel_path.absolute()
        data_obj = obj.config.get_load_data_obj()
        self.add_log_file_link(obj)
        return data_obj

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
        if self.file_path is not None and not self.read_only:
            self.save()

    def get_load_data_obj(self):
        if not self.is_loaded():
            self.load()
        return self.data

    def to_dict(self, *args):
        return {
            'formatter_t': self.formatter.__class__,
            'data_t': self.data.__class__
        }

    def from_dict(self, state_obj: dict, *args):
        raise Exception('Nope')

    @classmethod
    def handle_me(cls, ser_type: Type[Self], state_obj: dict, *args, **kwargs):
        return ser_type(Path(), data=state_obj['data_t'], formatter=state_obj['formatter_t']())
