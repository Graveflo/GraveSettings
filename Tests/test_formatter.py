from unittest import TestCase
from grave_settings.formatter import Formatter


class TestFormatter(TestCase):
    def test_path_formatting(self):
        formatter = Formatter()
        path = formatter.str_to_path("")
        self.assertIs(type(path), list)
        self.assertListEqual(path, [])

        formatter.key_path = []
        str_path = formatter.path_to_str()
        self.assertEqual(str_path, '')
