Handler Objects
=================

Handlers are objects that perform a similar function to :py:func:`singledispatch<functools.singledispatch>` which is part of the python standard library. The :py:class:`OrderedHandler<grave_settings.handlers.OrderedHandler>` is most similar to :py:func:`singledispatch<functools.singledispatch>` in that it will look at the first argument of a call and use its type to pick a callable to transfer the arguments to and then return the result of that call. There are three types of handlers in this module, but only the :py:class:`OrderedHandler<grave_settings.handlers.OrderedHandler>` is used in this package. There are other handlers that I have made too, but I haven't used or tested them in a while so I only included the relevant ones.

I think it is more confusing to explain how these classes work then it is to just show some examples. They are not complicated, but they are deeply integrated into this module so knowing the interface is important.

In short :py:class:`Handler<grave_settings.handlers.Handler>` is used to hold a collection of candidate callables that can be used to handle a type of input. The item at position 0 is the item with the highest priority. It is up to the client code to maintain the priority of handlers and make use of the data structures. Basically, it remembers a collection of handlers that are associated with a type and provides the set of handlers that is most specific for the type input.

:py:class:`OrderedHandler<grave_settings.handlers.OrderedHandler>` only stores one callable per type.

:py:class:`MroHandler<grave_settings.handlers.MroHandler>` will run all handlers for each handler that exactly matches an input type for each class in the inputs mro. The order is from parent class to base class. This has the effect of (almost) emulating overriding an inherited method if ``super()`` were called immediately in each overriden method.

OrderedHandler
----------------

.. code-block:: python

    from grave_settings.handlers import OrderedHandler

    handler = OrderedHandler()
    handler.handle([1, 2, 3])

This will raise a :py:class:`HandlerNotFound<grave_settings.handlers.HandlerNotFound>` exception because... we never added and handlers.

A basic handler
^^^^^^^^^^^^^^^^

.. code-block:: python

    from grave_settings.handlers import OrderedHandler


    def handle_list(key: list):
        print(key)


    handler = OrderedHandler()
    handler.add_handler(list, handle_list)
    handler.handle([1, 2, 3])

This will print ``[1, 2, 3]``

Subclass matching:
^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from grave_settings.handlers import OrderedHandler

    class A:
        def __init__(self, foo):
            self.foo = foo

    class B(A):
        pass

    def handle_a(key: A, arg1):
        print(f'Handled: {key.foo} - {arg1}')

    handler = OrderedHandler()
    handler.add_handler(A, handle_a)
    handler.handle(B('bar'), 'this is an arg')

This will print ``Handled: bar - this is an arg``

.. note::

    Extra arguments passed to the ``handle()`` will be forwarded to the handler

Only one handler is chosen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code-block:: python

    from grave_settings.handlers import OrderedHandler

    class A:
        def __init__(self, foo):
            self.foo = foo

    class B(A):
        pass

    def handle_a(key: A, arg1):
        print(f'Handled: {key.foo} - {arg1}')

    def handle_b(key: A, arg1):
        print(f'tomato')

    handler = OrderedHandler()
    handler.add_handler(A, handle_a)
    handler.add_handler(B, handle_b)
    handler.handle(B('bar'), 'this is an arg')

This will print ``tomato```

Order matters not specificity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from grave_settings.handlers import OrderedHandler

    class A:
        def __init__(self, foo):
            self.foo = foo

    class B(A):
        pass

    def handle_a(key: A, arg1):
        print(f'Handled: {key.foo} - {arg1}')

    def handle_b(key: A, arg1):
        print(f'tomato')

    handler = OrderedHandler()
    handler.add_handler(B, handle_b)
    handler.add_handler(A, handle_a)
    handler.handle(B('bar'), 'this is an arg')

This will print ``Handled: bar - this is an arg``

.. note::

    The only thing that is different between this example and the previous is the order in which ``handle_a`` and ``handle_b`` were added to the handler. Since both of them will match the :py:func:`isinstance` check the most recent catch will end up being the chosen handler

Using type hints
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from grave_settings.handlers import OrderedHandler

    def handle_list(key: list):
        print('list', key)

    def handle_dict(key:dict):
        print('dict', key)

    handler = OrderedHandler()
    handler.add_handlers_by_type_hints(handle_list, handle_dict)
    handler.handle([1, 2, 3])

This will print ``list [1, 2, 3]``


OrderedMethodHandler
----------------------

The forms prior can have a problem if you want to define a method that will behave as a handler in a subclass of the Handler object or in a class that will hold a reference to the Handler object. This is an issue because adding a method will add a :py:class:`boundmethod` which actually holds a reference to the method's object. This will create a circular reference.

.. note::

    Nothing is stopping you from doing this and creating circular references. I cant even tell you why you should care beyond the general garbage collection stuff. Use your best judgement.

.. code:: python

    from grave_settings.handlers import OrderedMethodHandler

    class MyHandler(OrderedMethodHandler):
        def init_handler(self):
            self.add_handlers_by_type_hints(self.handle_list, self.handle_dict)

        def handle_list(self, key: list):
            print('list', key)

        def handle_dict(self, key: dict):
            print('dict', key)

        def handle(self, *args, **kwargs):
            return super().handle(self, *args, **kwargs)

    handler = MyHandler()
    handler.handle([1, 2, 3])

The OrderedMethodHandler can safely add methods as handlers and they will be converted to their bare functions. This means that the ``handle`` method will be expecting self to be passed twice to it (once implicitly by the interpreter and once explicitly by you). If we know that all of the handlers are going to be methods of this object we can just override ``handle`` and pass the object reference there.

Or maybe not
^^^^^^^^^^^^^^

.. code-block:: python

    from grave_settings.handlers import OrderedMethodHandler

    class MyHandler(OrderedMethodHandler):
        def init_handler(self):
            self.add_handlers_by_type_hints(self.handle_list, self.handle_dict)

        def handle_list(self, key: list):
            print('list', key)

        def handle_dict(self, key: dict):
            print('dict', key)

        def handle(self, *args, **kwargs):
            return super().handle(self, *args, **kwargs)

    handler = MyHandler()

    def handle_set(handler: MyHandler, key: set):
        print('set', key)

    handler.add_handlers_by_type_hints(handle_set)
    handler.handle({1, 2, 3})

The above design can be clunky because dynamically added callables are forced to have an odd signature. There are several combinations of approaches that work best depending on the situation.

Conclusion
------------

Handlers are used to make a repository of callable functions that respond to objects based on their type. The most important feature is their ability to dynamically rearrange/re-order associations at runtime.