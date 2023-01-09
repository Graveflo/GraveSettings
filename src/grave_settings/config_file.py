# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Self, Any

from grave_settings.abstract import IASettings
from grave_settings.default_formatters import JsonFormatter, TomlFormatter
from grave_settings.formatter import Formatter


class ConfigFile:
    FORMATTER_STR_DICT = {
        'json': JsonFormatter(),
        'toml': TomlFormatter()
    }

    def __init__(self, file_path: Path, data: IASettings | Any, formatter: None | Formatter | str = None,
                 auto_save=False, read_only=False):
        if type(formatter) == str:
            formatter = self.FORMATTER_STR_DICT[formatter]
        self.file_path = file_path.resolve().absolute()
        self.data = data
        self.auto_save = auto_save
        self.formatter = formatter
        self.changes_made = not isinstance(data, IASettings)
        self.read_only = read_only
        self.sub_configs = {}

    def backup_settings_file(self):
        if self.file_path.is_file():
            base = self.file_path.parent
            dt_n = datetime.now().strftime('%Y_%m_%d %H%M')
            backup_path = base / f"{self.file_path.stem}_backup_{dt_n}{self.file_path.suffix}"
            shutil.copyfile(str(self.file_path), str(backup_path))

    def settings_converted(self, old_ver: dict, new_ver: dict):
        self.backup_settings_file()

    def settings_invalidated(self):
        self.changes_made = True
        if self.auto_save:
            self.save()

    def attach_settings(self, settings: IASettings):
        settings.invalidate.subscribe(self.settings_invalidated)
        settings.conversion_completed.subscribe(self.settings_converted)

    def detach_settings(self, settings: IASettings):
        try:
            settings.invalidate.unsubscribe(self.settings_invalidated)
        except KeyError:
            pass
        try:
            settings.conversion_completed.unsubscribe(self.settings_converted)
        except KeyError:
            pass

    def set_settings(self, settings: IASettings):
        if self.data is not None:
            self.detach_settings(settings)
        self.data = settings
        self.attach_settings(settings)

    def validate_file_path(self, path: Path, must_exist=False):
        if must_exist:
            if not path.exists():
                raise ValueError(f'Path does not exist: {path}')
        if path.exists() and (not os.access(path, os.W_OK)):
            raise ValueError(f'Do not have permission to write to: {path}')
        if path.exists() and (not path.is_file()):
            raise ValueError(f'File path is invalid: {path}')

    def save(self, path: Path=None, formatter: None | Formatter=None, force=False, validate_path=True):
        if self.read_only:
            raise ValueError('Saving in read-only mode')
        if path is None:
            path = self.file_path
            vf = self.changes_made
        elif (not force) and self.changes_made:
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

    def load(self, path: Path=None, formatter: None | Formatter=None, validate_path=True):
        if path is None:
            path = self.file_path
        if validate_path:
            self.validate_file_path(path, must_exist=True)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        self.data = formatter.read_from_file(str(path))

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
