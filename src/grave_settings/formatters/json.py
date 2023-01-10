import json

from grave_settings.formatter import Formatter


class JsonFormatter(Formatter):
    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return json.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return json.loads(buffer)
