from unittest import main
from io import BytesIO

from grave_settings.formatters.bson import BsonFormatter
from integrated_tests import TestRoundTrip


class TestBsonRoundtrip(TestRoundTrip):
    def get_formatter(self, serialization=True) -> BsonFormatter:
        formatter = BsonFormatter()
        return formatter

    def get_ser_obj(self, formatter, obj):
        bytesio = BytesIO()
        formatter.to_buffer(obj, bytesio)
        bytesio.seek(0)
        return bytesio

    def formatter_deser(self, formatter, ser_obj: BytesIO):
        return formatter.from_buffer(ser_obj)


if __name__ == '__main__':
    main()
