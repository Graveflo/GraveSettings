Using Handlers
================

The word "handler" is used... a lot on this page. Uppercase "Handler" refers to an object that is an instance of :py:class:`~grave_settings.handlers.Handler`. Lowercase "handler" refers to a callable that is added to a Handler object.

There are some situations where it is impractical, or I'll inaccurately say "impossible," to use inheritance to describe how a class should be converted to and from state objects. This is the main reason to use Handlers. Also, it can be easier to manage many instances of objects downstream from a parent object if the parent overrides a handler for them.

Lets look at an example:

.. code-block:: python

    from random import random
    from typing import Type

    from grave_settings.formatters.json import JsonFormatter

    class Color:
        def __init__(self, r, g, b):
            self.r = r
            self.g = g
            self.b = b
            self.random_number = random()

        def __str__(self):
            return f'Color(r={self.r}, g={self.g}, b={self.b})'

    formatter = JsonFormatter()
    obj_str = formatter.dumps(Color(255, 255, 255))
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj)

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.Color",
        "b": 255,
        "g": 255,
        "r": 255,
        "random_number": 0.9294795200396854
    }
    -----------------
    Color(r=255, g=255, b=255)

There is a problem here. It's not catastrophic, in this case, but it can be if we are not careful. Since the constructor or ``Color`` requires positional arguments the default deserialization handler is going to attempt to instantiate it and fail. The default Handler will use the ``__new__`` method to create the type without requiring the arguments and then set the attributes to the values that were serialized, but this means that **we do not call __init__ in this case**. If the ``__init__`` method does something important or sets up attributes that are not serialized this can lead to some unexpected behavior because some attributes will not have membership to the created object and some logic that is usually expected to take place may be skipped. Lets fix this.


Adding a default handler
--------------------------

Lets say that we did not want to serialize the ``random_number`` attribute of ``Color`` instances and we do not want to inherit from Color. Color does not have methods like ``to_dict`` and ``from_dict``, but actually, those methods are called by the default Handler if they are available. We can skip all of that by simply defining a new handler for this type.

There are a couple of different places we can add a handler for ``Color`` each with their advantages and disadvantages. We'll start with adding the handlers to a :py:class:`~grave_settings.formatter.Formatter`. This will effectively set them as defaults for the ``formatter`` object. Defaults can be overriden by further alterations to the Handlers (discussed later), but this is probably the best place to put catch-alls for a program.

.. code-block:: python

    from random import random
    from typing import Type

    from grave_settings.formatters.json import JsonFormatter


    class Color:
        def __init__(self, r, g, b):
            self.r = r
            self.g = g
            self.b = b
            self.random_number = random()

        def __str__(self):
            return f'Color(r={self.r}, g={self.g}, b={self.b})'


    def serialize_color(color: Color, *args, **kwargs):  # [2]
        return {
            'r': color.r,
            'g': color.g,
            'b': color.b
        }


    def deserialize_color(_type: Type[Color], dict_obj: dict, *args, **kwargs):  # [2]
        return Color(dict_obj['r'], dict_obj['g'], dict_obj['b'])


    formatter = JsonFormatter()
    formatter.serialization_handler.add_handlers_by_type_hints(serialize_color)  # [1]
    formatter.deserialization_handler.add_handlers_by_type_hints(deserialize_color)  # [1]
    obj_str = formatter.dumps(Color(255, 255, 255))
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj)

.. admonition:: Note [1]

    We are using the ``add_handlers_by_type_hints`` method to scan the type hint of the first parameter of the callable. The type of the first parameter will indicate which type the callable is associated with. The ``deserialization_handler`` by default is an instance of :py:class:`DeSerializationHandler<grave_settings.default_handlers.DeSerializationHandler>` which overrides this behavior to read the type inside the :py:class:`typing.Type` hint.

.. admonition:: Note [2]

    We are collapsing the positional arguments beyond the first to ``*args`` and the keyword arguments to ``**kwargs``. It is standard to have ``**kwargs`` on all handler functions / methods since the :py:class:`Processors<grave_settings.formatter.Processor>` will propagate ``**kwargs`` arguments through their process. The ``*args`` should always be a tuple of length 1. The argument that is passed will be an object of type :py:class:`FormatterContext<grave_settings.formatter_settings.FormatterContext>`. We are not using the :py:class:`FormatterContext<grave_settings.formatter_settings.FormatterContext>` in this example so I did not bother importing it and acknowledging it in the code, but it is important to know that it is there. If you wanted to do something like add :doc:`Semantics</api_reference/semantics>` to the context you accomplish this by interacting with this object.

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.Color",
        "r": 255,
        "g": 255,
        "b": 255
    }
    -----------------
    Color(r=255, g=255, b=255)

The handlers we added as defaults have changed the way Color is serialized and deserialized. Now there is no ``random_number`` attribute in the serialized object. Also since we defined a custom deserializing handler we are instantiating ``Color`` manually and thus we **are** calling ``__init__`` during the deserialization process this time.


Dynamically add handler during processing
---------------------------------------------

Lets take a look at adding handlers during processing. This has niche applications. It can save a lot of time if you have custom unmanaged objects that live under an managed object and you want the managed object to provide the logic for the unmanaged objects that it references. We will make a managed object, by using inheritance, that will take the responsibility of providing handlers for it's child objects.

.. code-block:: python

    from random import random
    from typing import Type

    from grave_settings.abstract import Serializable
    from grave_settings.formatter_settings import FormatterContext, Temporary
    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.handlers import OrderedHandler


    class Color:
        def __init__(self, r, g, b):
            self.r = r
            self.g = g
            self.b = b
            self.random_number = random()

        def __str__(self):
            return f'Color(r={self.r}, g={self.g}, b={self.b})'


    def serialize_color(color: Color, *args, **kwargs):
        return Temporary({  # [2]
            'r': color.r,
            'g': color.g,
            'b': color.b
        })


    def deserialize_color(_type: Type[Color], dict_obj: dict, *args, **kwargs):
        return Color(dict_obj['r'], dict_obj['g'], dict_obj['b'])


    class MyColors(Serializable):
        def __init__(self):
            self.color = Color(255, 255, 2555)

        @classmethod
        def check_in_serialization_context(cls, context: FormatterContext):
            handler = OrderedHandler()
            handler.add_handler(Color, serialize_color)
            context.handler = handler  # [1]

        @classmethod
        def check_in_deserialization_context(cls, context: FormatterContext):
            handler = OrderedHandler()
            handler.add_handler(Color, deserialize_color)
            context.handler = handler  # [1]


    formatter = JsonFormatter()
    obj_str = formatter.dumps(MyColors())
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj.color)

.. admonition:: Note [1]

    The reason we create an entirely new :py:class:`OrderedHandlers<grave_settings.handlers.OrderedHandler>` for this task is so the handlers do no propagate backwards. If we change the current Handler object then stack frames before the current frame will also be effected. Updating the handler during processing usually only effects down-stream objects and may negatively impact upstream objects. The ``handler`` attribute is a :py:class:`property` and setting the property automatically does a ``merge``, ``update_order`` operation on the new Handler with the previous Handler thus maintaining all the previous handlers but allowing the new :py:class:`~grave_settings.handlers.OrderedHandler` to override functionality.

.. admonition:: Note [2]

    :py:class:`~grave_settings.formatter_settings.Temporary` objects are special wrappers that inform the formatter that the data object it encapsulates is created for the sole purpose of communicating object structure. The object wrapped in the :py:class:`~grave_settings.formatter_settings.Temporary` instance **cannot** belong to a user object. The formatter will use this information to save memory, by mutating it in-place. Temporary objects are also dereferenced mid-process and because of this their object-ids become available for re-use. Without the :py:class:`~grave_settings.semantics.EnforceReferenceLifecycle` semantic (enabled by default) these object references will cause all kinds of mix ups in the formatter when :py:class:`~grave_settings.semantics.AutoPreserveReferences` is enabled (default). Temporary objects inform the formatter to skip all of this nonsense and will never attempt to reference them. Any time you have a data structure that was created for the sole purpose of communicating structure to the formatter you will want to wrap it in a Temporary object. The default :py:class:`~grave_settings.default_handlers.SerializationHandler` will automatically wrap the object returned by a handler, but since we are swapping the Handler out for :py:class:`OrderedHandlers<grave_settings.handlers.OrderedHandler>` ([1]) in this case we should manually wrap it.

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.MyColors",
        "color": {
            "__class__": "__main__.Color",
            "r": 255,
            "g": 255,
            "b": 2555
        }
    }
    -----------------
    Color(r=255, g=255, b=2555)

We see this output is the same as the previous except the color object is within ``MyColors`` and this class provides the logic for handling ``Color`` objects.

Using the MroHandler
----------------------

.. note::

    This is not currently used in this package

I use the MroHandler to decouple the creation of GUI settings windows (wip) from the settings objects. They blend the functionality of handlers with cooperative concepts from method overloading. MroHandlers are just like the OrderedHandler except all of the available handlers are run on an object for each of the classes in its mro and the output of each handler is passed to the next in a special positional argument named ``nest``

.. code-block:: python

    from grave_settings.handlers import MroHandler

    class A:
        def get_list(self):
            return [1, 2, 3]

    class B(A):
        def get_dict(self):
            return {
                'foo': 'bar'
            }

    def handle_a(instance: A, nest):
        if nest is None:
            nest = {}
        nest['list'] = instance.get_list()
        return nest

    def handle_b(instance: B, nest):
        if nest is None:
            nest = {}
        nest['dict'] = instance.get_dict()
        return nest

    handler = MroHandler()
    handler.add_handlers_by_type_hints(handle_a)
    handler.add_handlers_by_type_hints(handle_b)

    print(handler.handle(B()))

output: ``{'list': [1, 2, 3], 'dict': {'foo': 'bar'}}``
