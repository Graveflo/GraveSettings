from io import IOBase

import bson

from grave_settings.abstract import Route
from grave_settings.formatter import Formatter


class BsonFormatter(Formatter):
    FORMAT_SETTINGS = Formatter.FORMAT_SETTINGS.copy()
    FORMAT_SETTINGS.type_primitives |= bson.ObjectId

    def serialized_obj_to_buffer(self, ser_obj: dict) -> str:
        return bson.dumps(ser_obj)

    def buffer_to_obj(self, buffer):
        return bson.loads(buffer)

    def to_buffer(self, data, _io: IOBase, encoding=None, route: Route = None):
        return super().to_buffer(data, _io, encoding=encoding, route=route)

    def write_to_file(self, settings, path: str, encoding=None, route: Route = None):
        return super().write_to_file(settings, path, encoding=encoding, route=route)

    def from_buffer(self, _io: IOBase, encoding=None, route: Route = None):
        return super().from_buffer(_io, encoding=encoding, route=route)

    def read_from_file(self, path: str, encoding=None, route=None):
        return super().read_from_file(path, encoding=encoding, route=route)
