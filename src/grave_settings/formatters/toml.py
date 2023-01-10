import tomllib

try:
    import tomli_w as tlw
except ImportError:
    class tlw:
        @staticmethod
        def dumps(*args, **kwargs):
            raise ImportError('Could not import tomli_w. Writing toml is disabled')

from grave_settings.formatter import Formatter


class TomlFormatter(Formatter):
    FORMAT_SETTINGS = Formatter.FORMAT_SETTINGS.copy()
    FORMAT_SETTINGS.type_primitives = int | float | str | bool

    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return tlw.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return tomllib.loads(buffer)
