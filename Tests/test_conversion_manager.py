from unittest import TestCase, main

from ram_util.modules import load_type

from grave_settings.conversion_manager import *


class VersionedObject:
    @classmethod
    def get_version(cls):
        return '1.0.0'


class TestConversionManager(TestCase):
    def get_conversion_manager(self) -> ConversionManager:
        return ConversionManager()

    def test_create_version_object(self):
        ret = ConversionManager.get_version_object(VersionedObject)
        self.assertIn(format_class_str(VersionedObject), ret)
        self.assertEqual(ret[format_class_str(VersionedObject)], '1.0.0')

        class VersionedEnded(VersionedObject):
            VERSION = '5'  # This will be overriden by class method inherited

            @classmethod
            def get_versioning_endpoint(cls):
                return VersionedObject

        ret = ConversionManager.get_version_object(VersionedEnded)
        self.assertIn(format_class_str(VersionedEnded), ret)
        self.assertNotIn(format_class_str(VersionedObject), ret)
        self.assertEqual(ret[format_class_str(VersionedEnded)], '1.0.0')
        self.assertEqual(len(ret), 1)

        class VersionedInherited(VersionedObject):
            VERSION = '5'

            @classmethod
            def get_version(cls):
                return cls.VERSION

        ret = ConversionManager.get_version_object(VersionedInherited)
        self.assertIn(format_class_str(VersionedInherited), ret)
        self.assertIn(format_class_str(VersionedObject), ret)
        self.assertEqual(ret[format_class_str(VersionedInherited)], '5')
        self.assertEqual(ret[format_class_str(VersionedObject)], '1.0.0')
        self.assertEqual(len(ret), 2)

    def test_simple_convert(self):
        cm = self.get_conversion_manager()

        def convert_1_0_0_to_1_0_1(state_obj: dict):
            state_obj['test'] = 100

        cm.add_converter('1.0.0', VersionedObject, convert_1_0_0_to_1_0_1, '1.0.1')
        output = cm.try_convert({}, format_class_str(VersionedObject), '1.0.0', '1.0.1')
        self.assertEqual(output['test'], 100)

    def test_test_convert_failure(self):  # TODO: revisit this. Do we really not want to communicate the conversion failure?
        cm = self.get_conversion_manager()
        output = cm.try_convert({}, format_class_str(VersionedObject), '1.0.0', '1.0.1')
        self.assertEqual({}, output)

    def test_convert_multiple_passes(self):
        cm = self.get_conversion_manager()

        def convert1(state_obj: dict):
            state_obj['test'] = 100

        def convert2(stat_obj: dict):
            stat_obj['foo'] = 'bar'

        cm.add_converter('1.0.0', VersionedObject, convert1, '1.0.1')
        cm.add_converter('1.0.1', VersionedObject, convert2, '1.0.2')
        output = cm.try_convert({}, format_class_str(VersionedObject), '1.0.0', '1.0.2')
        self.assertEqual(output['test'], 100)
        self.assertEqual(output['foo'], 'bar')

    def test_convert_multiple_passes_stops_at_target(self):
        cm = self.get_conversion_manager()

        def convert1(state_obj: dict):
            state_obj['test'] = 100

        def convert2(stat_obj: dict):
            stat_obj['foo'] = 'bar'

        def convert3(stat_obj: dict):
            stat_obj['bar'] = 'foo'

        cm.add_converter('1.0.0', VersionedObject, convert1, '1.0.1')
        cm.add_converter('1.0.1', VersionedObject, convert2, '1.0.2')
        cm.add_converter('1.0.2', VersionedObject, convert3, '1.0.3')
        output = cm.try_convert({}, format_class_str(VersionedObject), '1.0.0', '1.0.2')
        self.assertEqual(output['test'], 100)
        self.assertEqual(output['foo'], 'bar')
        self.assertNotIn('bar', output)

        output = cm.try_convert({}, format_class_str(VersionedObject), '1.0.0', '1.0.3')
        self.assertIn('bar', output)

    def test_simple_managed_convert(self):
        rs = self

        class Foo:
            VERSION = '0.1.0'

            @classmethod
            def get_version(cls):
                return cls.VERSION

        old_version_info = self.get_conversion_manager().get_version_object(Foo)

        class Foo:
            VERSION = '1.0.0'

            @classmethod
            def get_version(cls):
                return cls.VERSION

            def get_conversion_manager(self) -> ConversionManager:
                cm = rs.get_conversion_manager()
                cm.add_converter('0.1.0', Foo, self.convert, '1.0.0')
                return cm

            def convert(self, dict_obj: dict):
                return {
                    'something': 100
                }

        globals()['Foo'] = Foo
        f = Foo()
        cm = f.get_conversion_manager()
        output = cm.update_to_current({}, load_type, old_version_info)
        self.assertIn('something', output)

    def test_managed_multiple_passes(self):
        rs = self

        class Foo:
            VERSION = '0.1.0'

            @classmethod
            def get_version(cls):
                return cls.VERSION

        old_version_info = self.get_conversion_manager().get_version_object(Foo)

        class Foo:
            VERSION = '1.1.0'

            @classmethod
            def get_version(cls):
                return cls.VERSION

            def get_conversion_manager(self) -> ConversionManager:
                cm = rs.get_conversion_manager()
                cm.add_converter('0.1.0', Foo, self.convert, '1.0.0')
                cm.add_converter('1.0.0', Foo, self.convert2, '1.1.0')
                return cm

            def convert(self, dict_obj: dict):
                return {
                    'something': [100]
                }

            def convert2(self, dict_obj: dict):
                dict_obj['something'].append(200)

        globals()['Foo'] = Foo
        f = Foo()
        cm = f.get_conversion_manager()
        output = cm.update_to_current({}, load_type, old_version_info)
        self.assertIn('something', output)
        self.assertEqual(output['something'], [100, 200])


if __name__ == '__main__':
    main()
