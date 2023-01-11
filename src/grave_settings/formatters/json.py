import json

from grave_settings.semantics import Indentation
from grave_settings.formatter import Formatter


class JsonFormatter(Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_semantic(Indentation(4))

    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        if indent := self.get_semantic(Indentation):
            indent = indent.val
        return json.dumps(ser_obj, indent=indent)

    def buffer_to_obj(self, buffer: str):
        return json.loads(buffer)
