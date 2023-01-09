import json
import tomli_w
import tomllib
from grave_settings.formatter import Formatter


class JsonFormatter(Formatter):
    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return json.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return json.loads(buffer)


class TomlFormatter(Formatter):
    PRIMITIVES = int | float | str | bool

    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return tomli_w.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return tomllib.loads(buffer)
