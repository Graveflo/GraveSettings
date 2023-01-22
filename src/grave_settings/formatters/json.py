import json

from grave_settings.formatter_settings import FormatterContext
from grave_settings.semantics import Indentation
from grave_settings.formatter import Formatter


class JsonFormatter(Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.semantics.add(Indentation(4))

    def serialized_obj_to_buffer(self, ser_obj: dict, context: FormatterContext) -> str:
        if indent := context.semantic_context[Indentation]:
            indent = indent.val
        return json.dumps(ser_obj, indent=indent)

    def buffer_to_obj(self, buffer: str, context: FormatterContext):
        return json.loads(buffer)
