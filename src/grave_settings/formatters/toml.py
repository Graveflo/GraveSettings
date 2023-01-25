import tomllib
from grave_settings.formatter_settings import FormatterContext

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

    def serialized_obj_to_buffer(self, ser_obj: dict, context: FormatterContext) -> str:
        return tlw.dumps(ser_obj)

    def buffer_to_obj(self, buffer, context: FormatterContext):
        return tomllib.loads(buffer)

    def get_serializer(self, root_obj, context) -> Serializer:
        serializer = super().get_serializer(root_obj, context)
        serializer.handler.add_handler(type(None), self.__class__.handle_None)
        return serializer

    def handle_None(self, none_obj, **kwargs):
        return {
            self.spec.class_id: 'types.NoneType'
        }
