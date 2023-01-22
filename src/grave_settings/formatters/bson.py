from io import IOBase
import bson

from grave_settings.formatter import Formatter, Processor
from grave_settings.formatter_settings import FormatterContext


class BsonFormatter(Formatter):
    FORMAT_SETTINGS = Formatter.FORMAT_SETTINGS.copy()
    FORMAT_SETTINGS.type_primitives |= bson.ObjectId

    def serialized_obj_to_buffer(self, ser_obj: dict, context: FormatterContext) -> str:
        return bson.dumps(ser_obj)

    def buffer_to_obj(self, buffer, context: FormatterContext):
        return bson.loads(buffer)

    def to_buffer(self, data, _io: IOBase, encoding=None, serializer: Processor = None):
        return super().to_buffer(data, _io, encoding=encoding, serializer=serializer)

    def write_to_file(self, settings, path: str, encoding=None, serializer: Processor = None):
        return super().write_to_file(settings, path, encoding=encoding, serializer=serializer)

    def from_buffer(self, _io: IOBase, encoding=None, kwargs: dict | None = None, deserializer: Processor = None):
        return super().from_buffer(_io, encoding=encoding, kwargs=kwargs, deserializer=deserializer)

    def read_from_file(self, path: str, encoding=None, kwargs: dict | None = None, deserializer: Processor = None):
        return super().read_from_file(path, encoding=encoding, kwargs=kwargs, deserializer=deserializer)
