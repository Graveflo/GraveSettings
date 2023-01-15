from unittest import main
from io import StringIO

from grave_settings.formatters.toml import TomlFormatter
from integrated_tests import TestRoundTrip


OUTPUT_FILES = True


class TestJsonRoundtrip(TestRoundTrip):
    def get_formatter(self, serialization=True) -> TomlFormatter:
        formatter = TomlFormatter()
        return formatter

    def get_ser_obj(self, formatter, obj):
        stringio = StringIO()
        formatter.to_buffer(obj, stringio)
        stringio.seek(0)
        if OUTPUT_FILES:
            with open(f'{self.id()}.toml', 'w') as f:
                f.write(stringio.read())
            stringio.seek(0)
        return stringio

    def formatter_deser(self, formatter, ser_obj: StringIO):
        return formatter.from_buffer(ser_obj)


if __name__ == '__main__':
    main()
