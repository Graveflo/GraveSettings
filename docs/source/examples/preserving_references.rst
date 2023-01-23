Preserving References
======================

Preserving references means maintaining "is" relationships through the serialization / deserialization process. The automatic preserving of references is managed by the Processors and the behavior is set by the following semantics:

:py:class:`~grave_settings.semantics.AutoPreserveReferences`

.. literalinclude:: ../../../src/grave_settings/semantics.py
   :pyobject: AutoPreserveReferences

:py:class:`~grave_settings.semantics.ResolvePreservedReferences`

.. literalinclude:: ../../../src/grave_settings/semantics.py
   :pyobject: ResolvePreservedReferences

:py:class:`~grave_settings.semantics.DetonateDanglingPreservedReferences`

.. literalinclude:: ../../../src/grave_settings/semantics.py
   :pyobject: DetonateDanglingPreservedReferences

:py:class:`~grave_settings.semantics.EnforceReferenceLifecycle`


.. literalinclude:: ../../../src/grave_settings/semantics.py
   :pyobject: EnforceReferenceLifecycle

.. note::

    I think it would be a bad idea to turn off :py:class:`~grave_settings.semantics.EnforceReferenceLifecycle`. The only rational for doing this I can think of would be to save on some time and memory complexity, but compared to the rest of the process this semantic is not expensive. It is confusing to determine when this semantic is necessary and its function is a safety net. It attempts to protect the Processor from mixing up object ids, so when this semantic is turned off and the processor gets confused this will lead to data loss, crashes and undefined behavior as objects will be incorrectly referencing each other.

Simple example
----------------

Lets serialize a data structure with duplicate references

.. code-block:: python

    from grave_settings.formatters.json import JsonFormatter

    some_list = [1, 2, 3]
    some_dict = {
        'foo': some_list,
        'bar': some_list
    }

    formatter = JsonFormatter()
    print(formatter.dumps(some_dict))

.. code-block::
  :caption: Output

   {
        "foo": [
            1,
            2,
            3
        ],
        "bar": {
            "__class__": "grave_settings.formatter_settings.PreservedReference",
            "ref": "\"foo\""
        }
    }

.. note::

    The preserved reference object is simple but the a note about the ``ref`` attribute. It is not guaranteed that the ``ref`` attribute will follow any particular format, and so, we should not look at it directly or use it to make decisions without consulting the :py:class:`~grave_settings.formatter_settings.FormatterSpec`. In most cases the :py:class:`~grave_settings.formatter_settings.FormatterSpec` or :py:class:`~grave_settings.formatter_settings.FormatterContext` will expose methods that act as an abstraction layer. This is just an FYI that a formatter or file format may be set up to use a different :py:class:`~grave_settings.formatter_settings.FormatterSpec` then what you may be anticipating if you choose to look at the ``ref`` value directly.

This way when the structure is deserialized ``foo`` and ``bar`` will be associated with the same list object as opposed to two separate lists with the same values. Note that this can be weird if you are deserializing :doc:`/examples/circular_references`


Not preserving references
---------------------------

Lets have a quick look at the output if the :py:class:`~grave_settings.semantics.AutoPreserveReferences` semantic was disabled

.. code-block:: python

    from grave_settings.formatters.json import JsonFormatter
    from grave_settings.semantics import AutoPreserveReferences

    some_list = [1, 2, 3]
    some_dict = {
        'foo': some_list,
        'bar': some_list
    }

    formatter = JsonFormatter()
    formatter.add_semantics(AutoPreserveReferences(False))  # [1]
    print(formatter.dumps(some_dict))

.. code-block::
  :caption: Output

    {
        "foo": [
            1,
            2,
            3
        ],
        "bar": [
            1,
            2,
            3
        ]
    }

Disabling preserved references dynamically
--------------------------------------------

Now lets say that you have two objects that reference two two separately identical objects. With one list you want to preserve the reference but with the other you do not. How to we accomplish this?

.. code-block:: python

    from grave_settings.formatter_settings import NoRef
    from grave_settings.formatters.json import JsonFormatter


    class Foo:
        def __init__(self):
            self.list1 = [1, 2, 3]
            self.list2 = [1, 2, 3]

        def to_dict(self, *args, **kwargs):
            return {
                'list1': self.list1,
                'list2': NoRef(self.list2)
            }


    class Bar:
        def __init__(self, foo: Foo):
            self.list1 = foo.list1
            self.list2 = foo.list2
            self.foo = foo

        def to_dict(self, *args, **kwargs):
            return {
                'list1': self.list1,
                'list2': NoRef(self.list2),
                'foo': self.foo
            }


    formatter = JsonFormatter()
    print(formatter.dumps(Bar(Foo())))


.. code-block::
  :caption: Output

    {
        "__class__": "__main__.Bar",
        "list1": [
            1,
            2,
            3
        ],
        "list2": [
            1,
            2,
            3
        ],
        "foo": {
            "__class__": "__main__.Foo",
            "list1": {
                "__class__": "grave_settings.formatter_settings.PreservedReference",
                "ref": "\"list1\""
            },
            "list2": [
                1,
                2,
                3
            ]
        }
    }

By wrapping the lists in :py:class:`~grave_settings.formatter_settings.NoRef` objects the formatter is instructed to disable preserved references for this object.

.. note::

    :py:class:`~grave_settings.formatter_settings.NoRef` is a simple subclass of :py:class:`~grave_settings.formatter_settings.AddSemantics` which acts in a similar manner, but allows you to attach arbitrary semantics to the wrapped object.

.. warning::

    The same effect can be achieved for the above by using :py:class:`~grave_settings.formatter_settings.Temporary` instead of :py:class:`~grave_settings.formatter_settings.NoRef` but this is only because it is a special case. If the list contained python objects or any other values that the formatter may transform during its operation, then the original objects will have data overriden. This is because :py:class:`~grave_settings.formatter_settings.Temporary` signals to the formatter that, not only is the object not referencable, but it also can safely be mutated and destroyed. It "belongs" to the formatter after the formatter unwraps it. :py:class:`~grave_settings.formatter_settings.Temporary` is typically used in :doc:`handlers</examples/using_handlers>`
