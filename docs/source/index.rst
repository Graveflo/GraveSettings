Welcome to the Grave Settings documentation!
==============================================

A library for automatic serialization of python object hierarchies to storage.

.. code-block:: python

    from pathlib import Path
    from grave_settings.config_file import ConfigFile
    from datetime import datetime


    class MyObject:
        def __init__(self):
            self.attribute1 = 'test'
            self.attribute2 = datetime.now()


    with ConfigFile(Path('test.toml'), data=MyObject, formatter='toml') as config:
        pass  # file will be saved automatically at the end of the with block

    with open('test.toml', 'r') as f:
        print(f.read())


.. code-block::
  :caption: Output

    __class__ = "__main__.MyObject"
    attribute1 = "test"

    [attribute2]
    __class__ = "datetime.datetime"
    state = [
        2023,
        1,
        24,
        19,
        8,
        34,
        522692,
    ]


Getting Started:
-----------------
This library was primarily created to manage configuration files in "human readable" formats.

:doc:`Check out the examples for a quick start<examples>`

:doc:`Check out the reference for details<api_reference>`


Limitations:
--------------

Security
^^^^^^^^^^^
By default this library allows for the importing and instantiation of arbitrary python modules / classes.
This is a security concern in many production environments. There are a couple of mechanisms built in to
deal with this, but they have not been a main concern of mine. Feel free to reach out with suggestions ect.

If security wasn't your first thought, its likely that importing arbitrary modules is not really a concern with
your use case. Just dont do anything too crazy like automatically deserializing HTTP request bodies and expect no one
to get weird with it.

Read this page (with examples) about security concerns.


Circular References
^^^^^^^^^^^^^^^^^^^^^

Circular references can be a problem when deserializing structures because of a "chicken and egg" problem in the
recursive process. There is an automatic process for dealing with circular references, but only if the nested reference
associated with the attribute of a managed object, like an object that implements
:py:class:`grave_settings.abstract.Serializable`'s interface. If the reference is nested in a list or a python dictionary
then custom code will have to take care of switching the :py:class:`grave_settings.formatter_settings.PreservedReference`
objects out for their proper references. The interface outlined in Serializable makes it easy to get a callback when the
deserialization is finished and provides a reference to the :py:class:`grave_settings.formatter_settings.FormatterContext`.
With this method it is simple to resolve the circular references, but you will likely have to have some idea of where
the references might be.

Also, note that the "automatic" handling of circular references is only enabled if you add the
:py:class:`grave_settings.semantics.NotifyFinalizedMethodName` semantic to a context. This must be manually enabled because
the default implementation of finalize is inefficient. See :py:meth:`grave_settings.abstract.Serializable.finalize`


For examples and more info on dealing with circular references. :doc:`examples/circular_references`



.. toctree::
   :caption: Directory

   limitations
   api_reference
   examples
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
