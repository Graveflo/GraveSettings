User Object Base Classes
==========================

There are several base classes for defining settings. Some of them exist mostly to be templates that have proper conventions for interacting with formatters and others come with their own conventions and utilities.

:py:class:`~grave_settings.abstract.Serializable` - defines the interface for interacting with formatters
:py:class:`~grave_settings.abstract.VersionedSerializable` - defines interface for automatic versioning and conversion
:py:class:`~grave_settings.abstract.IASettings` - defines the interface for "settings like" objects
:py:class:`~grave_settings.base.Settings` - A simple base class that uses string keys
:py:class:`~grave_settings.base.SlotSettings` - A simple base class that uses slots and attributes

Serializable
--------------

If you take a look at the api documentation or code for this class (its very small) it will give you a decent idea of what a "serializable" object looks like to this library. You do not need to directly inherit from :py:class:`~grave_settings.abstract.Serializable` to adhere from this interface. As long as the object has these methods they will be called unless they are disabled with the :py:class:`~grave_settings.semantics.IgnoreDuckTypingForType` or :py:class:`~grave_settings.semantics.IgnoreDuckTypingForSubclasses`

Object template:

.. code-block:: python

    class MyObject(Serializable):
        __slots__ = tuple()  # this is not needed

        @classmethod
        def check_in_serialization_context(cls, context: FormatterContext):
            pass

        @classmethod
        def check_in_deserialization_context(cls, context: FormatterContext):
            # context.register_frame_semantic(NotifyFinalizedMethodName('finalize'))
            pass

        def to_dict(self, context: FormatterContext, **kwargs) -> dict:
            return super().to_dict(context, **kwargs)

        def from_dict(self, state_obj: dict, context: FormatterContext, **kwargs):
            super().from_dict(state_obj, context, **kwargs)


.. note::

    :py:meth:`~grave_settings.abstract.Serializable.check_in_serialization_context` and :py:meth:`~grave_settings.abstract.Serializable.check_in_deserialization_context` are class methods for a reason. See the docstrings for more info

Semantics should probably be added in the "check_in_context" methods and if no custom objects are being used in :py:meth:`~grave_settings.abstract.Serializable.to_dict` or :py:meth:`~grave_settings.abstract.Serializable.from_dict` they can just be erased. You can look at the default implementation to see if it suites your needs.

.. _API_Ref_VersionedSerializable:

Versioned Serializable
------------------------

This is the template for version-aware serializable objects. The default implementations use another class: :py:class:`~grave_settings.conversion_manager.ConversionManager` to handle most of this responsibility, but this is not required. The version aware objects exist for scenarios where data is stored on the hard drive (or something like that) and the client code that eventually reads the object is from a later date and using a different specification for the format. This can happen if you serialized a python object and then changed its attributes, or renamed something etc. Adding these methods to the mix allows you to version your object and write code that will update dictionaries in old formats to new ones.

Object Template:

.. code-block:: python

    class MyObject(VersionedSerializable):
        VERSION = '1'
        __slots__ = tuple()  # this is not needed

        @classmethod
        def check_in_serialization_context(cls, context: FormatterContext):
            pass

        @classmethod
        def check_in_deserialization_context(cls, context: FormatterContext):
            # context.register_frame_semantic(NotifyFinalizedMethodName('finalize'))
            pass

        @classmethod
        def get_conversion_manager(cls) -> ConversionManager:
            cm = super().get_conversion_manager()
            # TODO: Add converters here
            return cm

        def to_dict(self, context: FormatterContext, **kwargs) -> dict:
            return super().to_dict(context, **kwargs)

        def from_dict(self, state_obj: dict, context: FormatterContext, **kwargs):
            super().from_dict(state_obj, context, **kwargs)

Very similar to :py:class:`~grave_settings.abstract.Serializable` except we have defined the class ``VERSION`` as a class level variable. This is read by the super classes :py:meth:`~grave_settings.abstract.VersionedSerializable.get_version` and used in :py:meth:`~grave_settings.abstract.VersionedSerializable.get_version_object`. We also have a space where we can use the :py:class:`~grave_settings.conversion_manager.ConversionManager` to add conversion functions.

:py:meth:`~grave_settings.abstract.VersionedSerializable.get_version_object` and :py:meth:`~grave_settings.abstract.VersionedSerializable.check_convert_update` are the only two methods that are absolutely necessary for a custom setup. The version object should be a serializable object (like a python dict) that contains **all** of the information necessary to precisely deduce the object's version. :py:meth:`~grave_settings.abstract.VersionedSerializable.check_convert_update` will receive this version object and use it to ensure everything is up to date.

IASettings
-------------

This is an abstract class for "setting like" objects. They inherit from :py:class:`~grave_settings.abstract.VersionedSerializable`. If you take a look at the methods that :py:class:`~grave_settings.abstract.IASettings` has, it is basically a container that implements things like ``__len__``, ``__iter__``, ``__getitem__``, ``__setitem__`` while also having an interface for the validation framework (this isn't done yet).

Settings
----------

This is basically the non-abstract :py:class:`~grave_settings.abstract.IASettings`. It is implemented in the simplest way possible with a dict. This is only a good option if you want to access and set data with strings only.

SlotSettings
--------------

This is the class that I use most often. It uses ``__slots__`` to implement the interfaces, including :py:meth:`~grave_settings.base.SlotSettings.to_dict` and :py:meth:`~grave_settings.base.SlotSettings.from_dict`. I recommend reading the test cases in ``test_slot_settings.py`` to get a quick handle on how to use this class. I would recommend never messing with ``SETTINGS_KEYS`` and only manipulating ``__slots__`` and ``_slot_rems`` where necessary. If you are confused about why those two class variables exist it is to take away the annoyance of declaring the set of attributes that are should be serialized. Each class in a lineage of inheritance are only responsible for declaring which attributes that are adding or removing.
