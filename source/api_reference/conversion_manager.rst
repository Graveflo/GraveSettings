Conversion Manager
====================

The :py:class:`~grave_settings.conversion_manager.ConversionManager` is a simple utility class that acts as a repository of functions that can upgrade a objects state from a previous version to a more current one. The :py:class:`~grave_settings.abstract.VersionedSerializable` provides the interface for objects that are "versioned" in the eyes of the default formatters.

.. note::

    Subclassing :py:class:`~grave_settings.abstract.VersionedSerializable` is not necessary for the default formatters to understand that a class is versioned. Just the method names are enough. :py:class:`~grave_settings.conversion_manager.ConversionManager` is not a requirement either. It can be switched out for a different class or implemented directly in the user object

The :py:class:`~grave_settings.conversion_manager.ConversionManager` is also responsible for creating a "version object" from a versioned user object. See :ref:`The interface for VersionedSerializable<API_Ref_VersionedSerializable>` for more info about this. Essentially the conversion manager needs to create a serializable object that can differentiate version effectively.

The default :py:class:`~grave_settings.conversion_manager.ConversionManager`, being simplistic, can only convert from one version to another. This means if you have a file that is 4 versions behind and only write 4 converters each for converting from the subsequent version to it's next. The :py:class:`~grave_settings.conversion_manager.ConversionManager` will have to run all 4 converters in sequence to update the state object to the correct version.

Here is what a version object looks like for the following class ``Graph3D``

.. code-block:: python

    class Graph(VersionedSerializable):
        VERSION = '1'


    class Graph3D(Graph):
        VERSION = '2'

.. code-block::

    {
        "__main__.Graph": "1",
        "__main__.Graph3D": "2"
    }

Note that the conversion manager saves the version of the super classes also, as they may change independently.

This is what a simple converter might look like:

.. code-block:: python

    def convert_1_to_2(state_obj: dict):
        theta = state_obj.pop('thetha')
        state_obj['theta'] = theta
        return state_obj

This function just fixes a spelling error. To add it to the conversion manager it would look like this:


.. code-block:: python

    cm = ConversionManager()
    cm.add_converter('1', Graph3D, convert_1_to_2, '2')

This is for the class ``Graph3D`` and converts version ``1`` to version ``2``.

