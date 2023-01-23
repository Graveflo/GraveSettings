Circular References
=======================

Below are examples of dealing with circular references when using the built in functionality provided by the :py:class:`~grave_settings.semantics.AutoPreserveReferences` and :py:class:`~grave_settings.semantics.ResolvePreservedReferences` semantics (enabled by default). When these semantics are not used, circular references will simply blow up the execution stack and cause a :py:class:`RecursionError`

Basic Example - Failure
-------------------------

.. code-block:: python

    from grave_settings.abstract import Serializable
    from grave_settings.formatters.json import JsonFormatter


    class MyObject(Serializable):
        def __init__(self):
            self.foo = self

        def __str__(self):
            return f'MyObject(id={id(self)}, foo={id(self.foo)})'


    formatter = JsonFormatter()
    obj_str = formatter.dumps(MyObject())
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj)

The above code will crash and raise :py:class:`~grave_settings.helper_objects.PreservedReferenceNotDissolvedError`. This is the expected behavior because the :py:class:`~grave_settings.semantics.DetonateDanglingPreservedReferences` semantic is enabled by default. At the end of the deserialization process the ``foo`` attribute will hold an object of type :py:class:`~grave_settings.formatter_settings.PreservedReference` and we can take a look at it if we disable :py:class:`~grave_settings.semantics.DetonateDanglingPreservedReferences`

Looking at PreservedReference
--------------------------------

.. code-block:: python

    from grave_settings.abstract import Serializable
    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.semantics import DetonateDanglingPreservedReferences


    class MyObject(Serializable):
        def __init__(self):
            self.foo = self

        def __str__(self):
            return f'MyObject(id={id(self)}, foo={id(self.foo)})'


    formatter = JsonFormatter()
    formatter.add_semantics(DetonateDanglingPreservedReferences(False))
    obj_str = formatter.dumps(MyObject())
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj)
    print(remade_obj.foo)

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.MyObject",
        "foo": {
            "__class__": "grave_settings.formatter_settings.PreservedReference",
            "ref": ""
        }
    }
    -----------------
    MyObject(id=140376620921168, foo=140376620918976)
    PreservedReference(ref='', obj=None)

Since this circular reference is a simple as it gets, it may seem like an odd choice to not have some automatic remediation of our problem, here. In reality, I could not think of a good solution to automatically solving this problem that was reasonably efficient and could handle circular references nested in dicts, lists, managed / unmanaged objects, etc without enforcing strict rules about reference key paths and the interface of encapsulating objects like ``__getitem__`` or :py:meth:`object.__getattr__`. For now, we just have to take some extra steps to deal with them.

.. note::

    There is a notably inefficient automatic process for fixing preserved references build into :py:class:`~grave_settings.abstract.Serializable` but it needs a :py:class:`~grave_settings.semantics.NotifyFinalizedMethodName` semantic to activate it.

Fixing a circular reference
------------------------------

.. code-block:: python

    from grave_settings.abstract import Serializable
    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.formatter_settings import PreservedReference, FormatterContext
    from grave_settings.semantics import NotifyFinalizedMethodName


    class MyObject(Serializable):
        def __init__(self):
            self.foo = self

        @classmethod
        def check_in_deserialization_context(cls, context: FormatterContext):
            context.add_frame_semantics(NotifyFinalizedMethodName('finalize'))  # [1]

        def finalize(self, context: FormatterContext) -> None:
            if isinstance(self.foo, PreservedReference):
                self.foo = context.check_ref(self.foo)  # [2]

        def __str__(self):
            return f'MyObject(id={id(self)}, foo={id(self.foo)})'


    formatter = JsonFormatter()
    obj_str = formatter.dumps(MyObject())
    print(obj_str)
    remade_obj = formatter.loads(obj_str)
    print('-----------------')
    print(remade_obj)

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.MyObject",
        "foo": {
            "__class__": "grave_settings.formatter_settings.PreservedReference",
            "ref": ""
        }
    }
    -----------------
    MyObject(id=140552547823568, foo=140552547823568)

.. admonition:: Note [1]

    We add :py:class:`~grave_settings.semantics.NotifyFinalizedMethodName` to the frame to inform the formatter that the method ``finalize`` is responsible for ensuring the deserialization is wrapped up. It is in ``finalize`` that we will fix the circular reference

.. admonition:: Note [2]

    The :py:class:`~grave_settings.formatter_settings.FormatterContext` has methods that make swapping a :py:class:`~grave_settings.formatter_settings.PreservedReference` for its actual value easy.

.. note::

    Adding the :py:class:`~grave_settings.semantics.NotifyFinalizedMethodName` semantic to the frame without defining ``finalize()`` will call the base-classes :py:meth:`~grave_settings.abstract.Serializable.finalize` method.