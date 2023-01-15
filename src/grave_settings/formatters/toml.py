import tomllib
from types import NoneType

from grave_settings.formatter_settings import FormatterContext
from grave_settings.semantics import OverrideClassString

try:
    import tomli_w as tlw
except ImportError:
    class tlw:
        @staticmethod
        def dumps(*args, **kwargs):
            raise ImportError('Could not import tomli_w. Writing toml is disabled')

from grave_settings.formatter import Formatter, Serializer


class TomlFormatter(Formatter):
    FORMAT_SETTINGS = Formatter.FORMAT_SETTINGS.copy()
    FORMAT_SETTINGS.type_primitives = int | float | str | bool
    FORMAT_SETTINGS.type_special |= None

    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return tlw.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return tomllib.loads(buffer)

    def get_serializer(self, root_obj, context) -> Serializer:
        serializer = super().get_serializer(root_obj, context)
        serializer.handler.add_handler(type(None), self.handle_None)
        return serializer

    def handle_None(self, none_obj, **kwargs):
        return {
            self.spec.class_id: 'types.NoneType'
        }
