Settings Bases
=================

:doc:`Read the API Reference on these base classes</api_reference/bases>` to learn about their design and purpose.

I'll make a "the works" example of an object inheriting from :py:class:`~grave_settings.base.SlotSettings` and making use of as many of the features I can manage.


.. code-block:: python

    from grave_settings.base import SlotSettings
    from grave_settings.conversion_manager import ConversionManager
    from grave_settings.formatter_settings import FormatterContext
    from grave_settings.semantics import AutoPreserveReferences


    class Graph(SlotSettings):
        VERSION = '1'

        P_TITLE = 'title'
        P_LEGEND = 'legend'

        __slots__ = P_TITLE, P_LEGEND, 'data'
        _slot_rems = 'data',

        def __init__(self, data):
            super().__init__()
            self.title = None
            self.legend = None
            self.data = data

        @classmethod
        def check_in_serialization_context(cls, context: FormatterContext):
            context.add_semantics(AutoPreserveReferences(False))


    class Graph3D(Graph):
        VERSION = '2'

        P_THETA = 'theta'
        P_Z = 'z'

        __slots__ = P_THETA, P_Z, 'renderer'
        _slot_rems = 'renderer',

        def __init__(self, data):
            super().__init__(data)
            self.theta = 0
            self.z = 0

        @classmethod
        def get_conversion_manager(cls) -> ConversionManager:
            cm = super().get_conversion_manager()
            cm.add_converter('1', Graph3D, convert_1_to_2, '2')
            return cm


    def convert_1_to_2(state_obj: dict):
        theta = state_obj.pop('thetha')
        state_obj[Graph3D.P_THETA] = theta
        return state_obj


    from grave_settings.formatters.json import JsonFormatter

    formatter = JsonFormatter()
    print(formatter.dumps(Graph3D([])))
    old_str = '''
    {
        "__class__": "__main__.Graph3D",
        "__version__": {
            "__main__.Graph": "1",
            "__main__.Graph3D": "1"
        },
        "title": null,
        "legend": null,
        "thetha": 5,
        "z": 0
    }
    '''
    graph = formatter.loads(old_str)
    print('The deserialized value is: ', graph.theta)

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.Graph3D",
        "__version__": {
            "__main__.Graph": "1",
            "__main__.Graph3D": "2"
        },
        "title": null,
        "legend": null,
        "theta": 0,
        "z": 0
    }
    The deserialized value is:  5

.. note::

    The json string that is output is **NOT** the same as the string that is deserialized in the code. I changed it on purpose.

I'm not exactly sure what these data structures are supposed to represent. I'll call this poetry, but anyway, we see two classes; one inherits from the other. We see that they are defining their own ``__slots__`` and ``_slot_rems`` and this effects which attributes are serialized. We see that they are defining their version with the ``VERSION`` attribute and the version object in the output string records the version of the child class and the super class. We see that the super class is adding a semantic to the FrameContext for absolutely no reason. We see that the child class is installing a converter to it's ConversionManager that fixes a spelling error in version 1. We see that supplying a string that has the spelling error in it and the string ``"1"`` as its version information for that classes triggers the automatic conversion when the string is deserialized.

The convention of making the ``__slots__`` attribute names class level variables is by no means required, that is just a convention of mine as I like to have statically defined paths for static data.