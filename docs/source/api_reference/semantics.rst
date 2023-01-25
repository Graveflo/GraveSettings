Semantics
===========

Semantics provide a simple mechanism for objects to communicate with the formatter during processing. Semantics are not guaranteed to be supported by all formatters and thus custom formatters should not have to implement all or any of the semantics. You can also make custom semantics and use them wherever you want. Objects that work with semantics should always accept any semantic that is given to them but they do not have to actually use them. The built in formatters should support all semantics where applicable.


Usage
------

Semantics are just objects that wrap another object. Each semantic has a specific meaning that is implied from it's unique type and the encapsulated data is like a setting value. Creating a semantic will look something like this:

.. code-block:: python

    Semantic(True)

This creates a semantic of type Semantic with the value True. Of course, real semantics will be a subclass of Semantic and the subclass should define its encapsulating type by means of the generic typing of Semantic. For example this is the definition of a Semantic used in this module:

.. code-block:: python

    class Indentation(Semantic[int]):

This is the :py:class:`Indentation<grave_settings.semantics.Indentation>` semantic and it specifies the type int to the generic class. This means that you are meant to create Indentation semantics like this:

.. code-block:: python

    Indentation(4)

Grouping and Interactions
---------------------------

There are two distinct kinds of Semantics and they are not differentiated by their class but instead the value of the class variable COLLECTION. :py:class:`Semantic<grave_settings.semantics.Semantic>` (the base class of all semantics) sets this value to :py:class:`None` meaning that, by default, semantics do not stack and instead overwrite each-other.

This means that adding the same semantic type to something like a :py:class:`Semantics<grave_settings.semantics.Semantics>` object, like this:

.. code-block:: python

    from grave_settings.semantics import Indentation, Semantics

    semantics = Semantics()
    semantics.add_semantics(Indentation(4))
    semantics.add_semantics(Indentation(5))
    print(semantics[Indentation])

The value printed will be 5.

If the COLLECTION variable is not :py:class:`None` then it is assumed that semantics of that type are meant to stack instead of overwriting each other and the collection that holds them will be instantiated from the type COLLECTION is set to. The value of COLLECTION should be a type and :py:class:`Semantic<grave_settings.semantics.Semantic>` has some methods that can be overriden if this type happens to be incompatible with the interface of the :py:class:`set` class. Here is an example showing how stacking semantics work:

.. code-block:: python

    from grave_settings.semantics import Semantics, Semantic


    class SomeSemantic(Semantic[int]):
        COLLECTION = set


    semantics = Semantics()
    semantics.add_semantics(SomeSemantic(4))
    semantics.add_semantics(SomeSemantic(5))
    print(semantics[SomeSemantic])
    print(SomeSemantic(4) in semantics)
    print(SomeSemantic(5) in semantics)

This will print:

.. code-block::
  :caption: Output

    {SomeSemantic(4), SomeSemantic(5)}
    True
    True

Showing that stacking semantics are stored in a collection (:py:class:`set` in this case) and multiple values can be "in" the collection at a given time.

Integration
--------------

Simple enough, but why and how are semantics actually used? The formatter, or more specifically :py:class:`Processors<grave_settings.formatter.Processor>` in the default configurations, accept, view and manipulate semantics. Semantics are meant to function on a "stack" the same way we think about a recursive process. In this way of thinking we have what are referred to as "frame semantics" as well as the regular "semantics." Semantics will propagate in depth, but not in breadth, meaning that if an object adds a semantic to the process it will stay there unless is it removed or overriden down stream. When a frame is "popped" the state of the semantics are restored to their configuration before the "push." Frame semantics only effect the current recursion frame and do not effect either depth or breadth. The object that is responsible for managing this stack-like behavior is :py:class:`SemanticContext<grave_settings.semantics.SemanticContext>` or in an actual formatter its subclass :py:class:`FrameStackContext<grave_settings.framestack_context.FrameStackContext>` which adds a :doc:`handler</api_reference/handlers>` to the stack.

:py:class:`Formatters<grave_settings.formatter.Formatter>` allow you to set semantics that they will hold onto and insert into the root frame's semantics (not frame semantics) and :py:class:`processors<grave_settings.formatter.Processor>` also set default semantics to the root frame. The formatter's semantics are added after the processor's defaults since the formatter's semantics are empty by default. They are there for user convenience.

Objects have access to semantics during processing via the :py:class:`FormatterContext<grave_settings.formatter_settings.FormatterContext>` that is passed into specially named methods on objects: :py:meth:`check_in_serialization_context<grave_settings.abstract.Serializable.check_in_serialization_context>`, :py:meth:`check_in_deserialization_context<grave_settings.abstract.Serializable.check_in_deserialization_context>`, :py:meth:`to_dict<grave_settings.abstract.Serializable.to_dict>`, :py:meth:`from_dict<grave_settings.abstract.Serializable.from_dict>`

It's important to note that the default formatters call :py:meth:`check_in_serialization_context<grave_settings.abstract.Serializable.check_in_serialization_context>` and :py:meth:`check_in_deserialization_context<grave_settings.abstract.Serializable.check_in_deserialization_context>` before the item in question is handled, but :py:meth:`check_in_deserialization_context<grave_settings.abstract.Serializable.check_in_deserialization_context>` happens before the object even exists. This is because in the deserialization process, the object is instantiated during handling from format specific objects, where it is the other way around for serialization. :py:meth:`from_dict<grave_settings.abstract.Serializable.from_dict>` and :py:meth:`to_dict<grave_settings.abstract.Serializable.to_dict>` happen during the handling process if the :py:mod:`default handlers<grave_settings.default_handlers>` are used.


Explanation by Example
------------------------

You can read a description of the available semantics here: :py:class:`grave_settings.semantics`

Lets looks at the :py:class:`AutoKeySerializableDictType<grave_settings.semantics.AutoKeySerializableDictType>` semantic. This will tell the formatter which type to use for automatic conversion from a dictionary. This is needed when the file format does not support dictionary keys of arbitrary types. For example: JSON strings will only accept strings as their dictionary keys but python can have a dictionary keyed by arbitrary python objects. The default formatter will respond to this semantic and scan each dictionary's keys for a types that are not allowed.

.. note::

    The types that are allowed to be dictionary keys are set in the :py:class:`FormatterSpec<grave_settings.formatter_settings.FormatterSpec>` from the method :py:class:`get_attribute_types<grave_settings.formatter_settings.FormatterSpec.get_attribute_types>` which by default looks at the class variable ATTRIBUTE. The supplied formatters like :py:class:`JsonFormatter<grave_settings.formatters.json.JsonFormatter>` already have the appropriate values set, and :py:class:`AutoKeySerializableDictType<grave_settings.semantics.AutoKeySerializableDictType>` is enabled by default.

Normally this semantic is either not present, meaning that the python objects will either never have invalid keys, or will be incompatible with formats that do not support their keys, or it will be set as a default value at the root frame and forgotten, letting it do it's job when needed. Lets say we wanted to turn it on manually. In the following example we will:

1. Disable the semantic on the root frame thus overriding the default
2. Create a class that turns the semantic on
3. Observe the output of the serialization process


.. code-block:: python

    from grave_settings.abstract import Serializable
    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.semantics import AutoKeySerializableDictType, Negate
    from grave_settings.helper_objects import KeySerializableDict
    from grave_settings.formatter_settings import FormatterContext


    class MyObject(Serializable):
        def __init__(self):
            self.my_mapping = {
                b'foo': 'bar'  # [1]
            }

        @classmethod
        def check_in_serialization_context(cls, context: FormatterContext):
            context.add_semantic(AutoKeySerializableDictType(KeySerializableDict))


    formatter = JsonFormatter()
    formatter.add_semantics(Negate(AutoKeySerializableDictType))  # [2]
    print(formatter.dumps(MyObject()))

.. admonition:: Note: [1]

    that the dictionary has a single key ``b'foo'`` which is of type :py:class:`bytes`. This class is not serializable by  :py:mod:`json`. Even though "foo" looks like a safe string there is no guarantee that an arbitrary byte buffer will cooperate with the file's character encoding let alone differentiating the types.

.. admonition:: Note: [2]

    The use of :py:class:`Negate<grave_settings.semantics.Negate>` here is usually not needed as the semantic manager classes usually provide a remove_semantic or similar method. :py:class:`Negate<grave_settings.semantics.Negate>` can be used to remove a semantic like you see above but this is only really useful if the semantics are being added to a collection that will later merge into a semantic context

This will output:

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.MyObject",
        "my_mapping": {
            "__class__": "grave_settings.helper_objects.KeySerializableDict",
            "kvps": [
                {
                    "__class__": "builtins.tuple",
                    "state": [
                        {
                            "__class__": "builtins.bytes",
                            "hex": "666f6f"
                        },
                        "bar"
                    ]
                }
            ]
        }
    }

Now lets look at a method for turning the semantic on only for the dictionary as the above will propagate the semantic to all object downstream of MyObject.


.. code-block:: python

    from grave_settings.abstract import Serializable
    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.semantics import AutoKeySerializableDictType, Negate
    from grave_settings.helper_objects import KeySerializableDict
    from grave_settings.formatter_settings import FormatterContext, AddSemantics


    class MyObject(Serializable):
        def __init__(self):
            self.my_mapping = {
                b'foo': 'bar'
            }

        def to_dict(self, context: FormatterContext, **kwargs) -> dict:
            my_mapping = AddSemantics(self.my_mapping, frame_semantics={AutoKeySerializableDictType(KeySerializableDict)})
            return {
                'my_mapping': my_mapping
            }


    formatter = JsonFormatter()
    formatter.add_semantics(Negate(AutoKeySerializableDictType))
    print(formatter.dumps(MyObject()))

The output is identical.

Let's acknowledge that MyObject might as well just create instances of :py:class:`KeySerializableDict<grave_settings.helper_objects.KeySerializableDict>` in it's :py:meth:`to_dict()` method explicitly instead of using semantics and then convert them back manually to regular objects. The semantic allows the formatter to decide if the transformation is necessary and makes the process automatic. This is the basic function of semantics.

