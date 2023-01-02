# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Self

from grave_settings.abstract import IASettings
from grave_settings.formatter import Formatter


class ConfigFile:
    def __init__(self, file_path: Path, settings: IASettings, formatter: None | Formatter=None, auto_save=False,
                 read_only=False):
        self.file_path = file_path.resolve().absolute()
        self.settings = settings
        self.auto_save = auto_save
        self.formatter = formatter
        self.changes_made = False
        self.read_only = read_only
        self.sub_configs = {}

    def backup_settings_file(self):
        if self.file_path.is_file():
            base = self.file_path.parent
            backup_path = base / f"{self.file_path.stem}_backup_{datetime.now().strftime('%Y_%m_%d %H%M')}{self.file_path.suffix}"
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
        if self.settings is not None:
            self.detach_settings(settings)
        self.settings = settings
        self.attach_settings(settings)

    def validate_file_path(self, path: Path):
        if not os.access(path, os.W_OK):
            raise ValueError(f'Do not have permission to write to: {path}')
        if path.exists() and (not path.is_file()):
            raise ValueError(f'File path is invalid: {path}')

    def save(self, path: Path=None, formatter: None | Formatter=None, force=False):
        if self.read_only:
            raise ValueError('Saving in read-only mode')
        if path is None:
            path = self.file_path
            vf = self.changes_made
        elif (not force) and self.changes_made:
            return
        else:
            vf = False
        self.validate_file_path(path)
        if formatter is None:
            formatter = self.formatter
        if formatter is None:
            raise ValueError('No formatter supplied')
        formatter.write_to_file(self.settings, str(self.file_path))
        self.changes_made = vf

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.save()
