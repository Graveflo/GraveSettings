Custom Formatter
======================

Lets use the python package :py:mod:configparser to build a custom formatter. This package is meant for "ini like" files but we will re-purpose it to make a custom format.

The first thing we have to do is decide which types are going to be "primitive" and which types are going to be "special". It looks to me like :py:mod:configparser doesnt have many default types, just strings and mappings. We'll expand on this.

Settings the Spec
--------------------

I've decided that I want string to work as close to how they do natively with the default setup in :py:mod:configparser except I want to be able to specify some extra types. I want ``bool(True)`` to automatically be converted to a python boolean and similar logic for ``int(0)`` and ``float(1.0)`` etc. To specify a string literal of the same text it would just look like this ``'bool(True)'`` and similarly any literal encapsulated in unescaped quotes will just be interpreted as a literal string.

We'll compare the Spec we make here to the json spec since it has a bit more going on with it. The json spec uses the default values so this is just the first couple lines of the abstract-ish :py:class:`~grave_settings.formatter_settings.FormatterSpec`.

.. code-block:: python
  :caption: Json spec

    class FormatterSpec:
        ROUTE_PATH_TRANSLATION = str.maketrans({
            '\\': '\\\\',
            '.': r'\.',
            '"': r'\"'
        })
        ROUTE_PATH_REGEX = re.compile(r'(?:[^\."]|"(?:\\.|[^"])*")+')
        PRIMITIVES = int | float | str | bool | NoneType
        SPECIAL = dict | list
        ATTRIBUTE = str

        TYPES = PRIMITIVES | SPECIAL

Since I want to do weird things like have no primitives (I cant say string is a primitive since strings have to be scanned to make sure they do not need to be escaped). I'll make a custom Spec to hold this information

.. code-block:: python
  :caption: Custom Spec

  class CustomSpec(FormatterSpec):
      PRIMITIVES = Never  # [1]
      SPECIAL = str | dict | list | bool | int | float | None  # [1]
      ATTRIBUTE = str  # [1]

      TYPES = PRIMITIVES | SPECIAL

      SPECIAL_REGEX = re.compile(r'^(int|float|None|bool|\'|\")')  # [2]

      def get_primitive_types(self) -> set:
          return set()

.. admonition:: Note [1]

  These values are not required. Previously they have been used for type hints and and other non-strict organizational purposes, but the default :py:class:`~grave_settings.formatter_settings.FormatterSpec` does use them in the methods :py:meth:`~grave_settings.formatter_settings.FormatterSpec.get_primitive_types` and :py:meth:`~grave_settings.formatter_settings.FormatterSpec.get_special_types` methods. The methods returning the correct values are all that matters

.. admonition:: Note [2]

  This regex will be used to tell if a string is following our custom rules or if it is just a literal string.

.. code-block:: python

  class CustomFormatter(Formatter):
      FORMAT_SETTINGS = CustomSpec()

      def serialized_obj_to_buffer(self, ser_obj: dict, context: FormatterContext) -> str:
          parser = configparser.ConfigParser()
          parser.optionxform = str
          parser.read_dict(ser_obj)
          strio = StringIO()
          parser.write(strio)
          strio.seek(0)
          return strio.read()

      def buffer_to_obj(self, buffer, context: FormatterContext):
          parser = configparser.ConfigParser()
          parser.optionxform = str
          return parser.read_string(buffer)

      def get_serializer(self, root_obj, context: FormatterContext) -> Serializer:
          return CustomSerializer(root_obj, self.spec.copy(), context)

Not looking amazing so far, we might want to put some finishing touches on this later, but lets move on to the actual serialization and deserialization logic. We are going to have to modify Serializer and Deserializer quite a bit since the format is so limited. Lets get serialization working first.


Custom Serializer
---------------------

.. code-block:: python

  class CustomSerializer(Serializer):
      def __init__(self, root_object, spec: CustomSpec, context: FormatterContext):
          super().__init__(root_object, spec, context)
          self.spec: CustomSpec = self.spec  # PyCharm bug
          self.handler.add_handlers_by_type_hints(
              self.handle_user_list,
              self.handle_user_float,
              self.handle_user_int,
              self.handle_user_bool,
              self.handle_user_none,
              self.handle_user_str,
          )
          context.spec = self.spec
          self.flat_dict = {}

      def handle_user_str(self, instance: str, **kwargs):
          if self.spec.SPECIAL_REGEX.match(instance) is None:
              return instance
          else:
              return repr(instance)

      def handle_serialize_dict_in_place(self, instance: dict, **kwargs):  # [1]
          instance = super().handle_serialize_dict_in_place(instance, **kwargs)
          self.skim_dict_for_flat_dict(instance)
          return instance

      def handle_serialize_default(self, instance: object, **kwargs):  # [2]
          instance = super().handle_serialize_default(instance, **kwargs)
          self.skim_dict_for_flat_dict(instance)
          return instance

      def skim_dict_for_flat_dict(self, instance: dict):
          prims = {k: v for k, v in instance.items() if type(v) is str}
          this_path = self.spec.path_to_str(self.context.key_path)
          if this_path in self.flat_dict:
              self.flat_dict[this_path].update(prims)
          else:
              self.flat_dict[this_path] = prims
          return prims

      def handle_user_list(self, instance: list, **kwargs):
          pass

      def handle_user_bool(self, instance: bool, **kwargs):
          return f'bool({instance})'

      def handle_user_int(self, instance: int, **kwargs):
          return f'int({instance})'

      def handle_user_float(self, instance: float, **kwargs):
          return f'float({instance})'

      def handle_user_none(self, instance: NoneType, **kwargs):
          return 'None'

      def process(self, obj=None, **kwargs):
          super().process(obj, **kwargs)
          if '' in self.flat_dict:
              self.flat_dict['MAIN'] = self.flat_dict.pop('')
          return self.flat_dict

.. note::

  Do not confuse the handler attribute of this ``CustomSerializer`` as the Handler that is is accessible from :py:class:`~grave_settings.formatter_settings.FormatterContext` through it's property ``handler``, truly belonging to :py:class:`~grave_settings.framestack_context.FrameStackContext`. The handler on ``CustomSerializer`` is part of the serialization process that decides a method handler for input types before they are passed through the user object Handler

.. admonition:: Note [1]

  The :py:class:`~grave_settings.formatter.Serializer` we are inheriting from ultimately calls ``handle_serialize_dict_in_place`` for both :py:class:`~grave_settings.formatter_settings.Temporary` dicts and user dicts. Overriding it and calling super will let all of the machinery for dicts in the super class do its thing and we will modify the data for our use case.

.. admonition:: Note [2]

  Custom objects go through the ``handle_serialize_default`` method in the super class so we will intercept this one also. If it were not for the :py:class:`~configparser.ConfigParser` disliking nested dictionaries we could probably side step most of this


The :py:class:`~configparser.ConfigParser` wants to work in terms of a flat dictionary with keys being the major sections in the ini file and the values being ``dict[str, str]``. This differs from how json and toml want their data structures set up but that is why we added a new attribute ``flat_dict`` and intercept the :py:meth:`~grave_settings.formatter.Serializer.process` method.

I have chosen to add ``handle_user_list`` later, and I would also like to change how the ``CustomSpec`` formats the key paths. Take a look at the example below:

.. code-block:: python

  formatter = CustomFormatter()
  d = formatter.dumps({
      'foo': 'bar',
      'baz': {
          'str': 'a string',
          'None': None,
          'bool': True,
          'int': 1,
          'custom handled': CustomFormatter,
          'pesky string': 'bool(True)',
          'quote char': "'",
          'other quote char': '"'
      }
  })
  print(d)

.. code-block::
  :caption: Output

  ["baz"."custom handled"]
  __class__ = abc.ABCMeta
  state = __main__.CustomFormatter

  ["baz"]
  str = a string
  None = None
  bool = bool(True)
  int = int(1)
  pesky string = 'bool(True)'
  quote char = "'"
  other quote char = '"'

  [MAIN]
  foo = bar


The first thing I notice is that the headers are in the reverse order I would like. Solving this is probably best done in post (using :py:class:`~configparser.ConfigParser` or the :py:class:`~grave_settings.formatter.Formatter`). The second thing is I dont like the quotes in the path names. We'll address both of these gripes later.

Custom DeSerializer
---------------------

Lets see if we can turn that string back into a python object.

.. code-block:: python

  class CustomDeSerializer(DeSerializer):
      def __init__(self, root_object: dict, spec: FormatterSpec, context: FormatterContext):
          super().__init__(root_object, spec, context)
          self.spec: CustomSpec = self.spec  # PyCharm bug
          self.handler.add_handlers_by_type_hints(self.handle_string)
          self.secondary_handler.add_handlers_by_type_hints(self.handle_secondary_prim)

      @DeSerializer.root_obj.setter
      def root_obj(self, root_obj):  # [1]
          root_obj = {k: v for k, v in root_obj.items()}
          if None in root_obj:
              root_obj.pop(None)
          if 'MAIN' in root_obj:
              main = {k: v for k, v in root_obj.pop('MAIN').items()}
          else:
              main = {}
          main.update(self.expand(root_obj))
          self._root_obj = main

      def expand(self, base: dict):  # [2]
          work = {}
          str_2_p = self.spec.str_to_path
          for k, v in base.items():
              nest = work
              p_nest = nest

              path = str_2_p(k)
              for part in path:
                  if part not in nest:
                      nest[part] = {}
                  p_nest = nest
                  nest = nest[part]
              v = {k: v for k, v in v.items()}
              p_nest[path[-1]].update(v)
          return work

      def handle_string(self, instance: str, **kwargs):  # [3]
          if (match := self.spec.SPECIAL_REGEX.match(instance)) is None:
              return instance
          else:
              start = match.groups()[0]
              if start == 'int':
                  return int(instance[4:-1])
              elif start == 'bool':
                  return bool(instance[5:-1])
              elif start == 'None':
                  return None
              elif start == 'float':
                  return float(instance[5:-1])
              else:
                  return literal_eval(instance)

      def handle_secondary_prim(self, instance: bool | int | float | NoneType, **kwargs):  # [4]
          return instance

.. admonition:: Note [1]

  This is overriding :py:class:`~grave_settings.formatter.Processor`'s property. This is a simple way to turn the "flattened" dictionary-like object into a nested dictionary structure. The :py:class:`~configparser.ConfigParser` adds some extra stuff into dictionary-like object is uses, so they are stripped out

.. admonition:: Note [2]

  This is the method that will convert the key paths in the flattened dictionary to the nested dictionary. Unfortunestly the dictionary-like objects do not cooperate fully with the interface of a dictionary so they cannot be left as-is

.. admonition:: Note [3]

  There is almost certainly a better way to do this, but hey, this is just an example. This undoes our custom strings that are meant to represent types

.. admonition:: Note [4]

  This handler is attached to the ``secondary_handler``. The :py:class:`~grave_settings.formatter.DeSerializer` has two handlers. This is for dealing with things like :py:class:`~grave_settings.formatter_settings.PreservedReference` and caching object paths for fixing reference issues. This method keeps the primitives from being cached for references since this is meant only for higher level objects.

Now lets ass this method to the custom formatter:

.. code-block:: python

      def get_deserializer(self, root_obj, context) -> CustomDeSerializer:
        return CustomDeSerializer(root_obj, self.spec.copy(), context)

and we'll try to deserialize our string:

.. code-block:: python

  formatter = CustomFormatter()
  d = formatter.dumps({
      'foo': 'bar',
      'baz': {
          'str': 'a string',
          'None': None,
          'bool': True,
          'int': 1,
          'custom handled': CustomFormatter,
          'pesky string': 'bool(True)',
          'quote char': "'",
          'other quote char': '"'
      }
  })
  import pprint
  pprint.pprint(formatter.loads(d))

.. code-block::
  :caption: Output

    {'baz': {'None': None,
             'bool': True,
             'custom handled': <class '__main__.CustomFormatter'>,
             'int': 1,
             'other quote char': '"',
             'pesky string': 'bool(True)',
             'quote char': "'",
             'str': 'a string'},
     'foo': 'bar'}


Wrapping things up
--------------------

Finally, we have the full code with some of the blemishes patched up.

.. code-block:: python

    import configparser
    import datetime
    from ast import literal_eval
    from io import StringIO
    from types import NoneType
    from typing import Never, Iterable
    import re

    from grave_settings.abstract import Serializable
    from grave_settings.formatter import Formatter, Serializer, DeSerializer
    from grave_settings.formatter_settings import FormatterContext, FormatterSpec


    class CustomSpec(FormatterSpec):
        PRIMITIVES = Never
        SPECIAL = str | dict | list | bool | int | float | None
        ATTRIBUTE = str

        TYPES = PRIMITIVES | SPECIAL

        SPECIAL_REGEX = re.compile(r'^(int|float|None|bool|\'|\")')

        def get_primitive_types(self) -> set:
            return set()

        def path_to_str(self, key_path: Iterable) -> str:
            return '.'.join(p.translate(self.ROUTE_PATH_TRANSLATION) for p in key_path)

        def str_to_path(self, reference: str) -> list:
            return list(p for p in self.ROUTE_PATH_REGEX.findall(reference))


    class ListAsDict(Serializable):
        __slots__ = 'list',

        def __init__(self, li: list=None):
            self.list = li

        def to_dict(self, context: FormatterContext, **kwargs) -> dict:
            return {str(i): v for i, v in enumerate(self.list)}

        def from_dict(self, state_obj: dict, context: FormatterContext, **kwargs):
            li = []
            for i in range(len(state_obj)):
                li.append(state_obj[str(i)])
            self.list = li


    class CustomSerializer(Serializer):
        def __init__(self, root_object, spec: CustomSpec, context: FormatterContext):
            super().__init__(root_object, spec, context)
            self.spec: CustomSpec = self.spec  # PyCharm bug
            self.handler.add_handlers_by_type_hints(
                self.handle_user_list,
                self.handle_user_float,
                self.handle_user_int,
                self.handle_user_bool,
                self.handle_user_none,
                self.handle_user_str,
            )
            context.spec = self.spec
            self.flat_dict = {}

        def handle_user_str(self, instance: str, **kwargs):
            if self.spec.SPECIAL_REGEX.match(instance) is None:
                return instance
            else:
                return repr(instance)

        def handle_serialize_dict_in_place(self, instance: dict, **kwargs):  # [1]
            instance = super().handle_serialize_dict_in_place(instance, **kwargs)
            self.skim_dict_for_flat_dict(instance)
            return instance

        def handle_serialize_default(self, instance: object, **kwargs):  # [2]
            instance = super().handle_serialize_default(instance, **kwargs)
            self.skim_dict_for_flat_dict(instance)
            return instance

        def skim_dict_for_flat_dict(self, instance: dict):
            prims = {k: v for k, v in instance.items() if type(v) is str}
            this_path = self.spec.path_to_str(self.context.key_path)
            if this_path in self.flat_dict:  # [3]
                prims.update(self.flat_dict[this_path])
            self.flat_dict[this_path] = prims
            return self.flat_dict[this_path]

        def handle_serialize_list_in_place(self, instance: list, **kwargs):
            return self.handle_serialize_default(ListAsDict(li=instance))

        def handle_user_bool(self, instance: bool, **kwargs):
            return f'bool({instance})'

        def handle_user_int(self, instance: int, **kwargs):
            return f'int({instance})'

        def handle_user_float(self, instance: float, **kwargs):
            return f'float({instance})'

        def handle_user_none(self, instance: NoneType, **kwargs):
            return 'None'

        def process(self, obj=None, **kwargs):
            super().process(obj, **kwargs)
            if '' in self.flat_dict:
                self.flat_dict['MAIN'] = self.flat_dict.pop('')
            return self.flat_dict


    class CustomDeSerializer(DeSerializer):
        def __init__(self, root_object: dict, spec: FormatterSpec, context: FormatterContext):
            super().__init__(root_object, spec, context)
            self.spec: CustomSpec = self.spec  # PyCharm bug
            self.handler.add_handlers_by_type_hints(self.handle_string)
            self.secondary_handler.add_handlers_by_type_hints(self.handle_secondary_prim, self.handle_secondary_list_as_dict)

        @DeSerializer.root_obj.setter
        def root_obj(self, root_obj):  # [1]
            root_obj = {k: v for k, v in root_obj.items()}
            if None in root_obj:
                root_obj.pop(None)
            if 'MAIN' in root_obj:
                main = {k: v for k, v in root_obj.pop('MAIN').items()}
            else:
                main = {}
            main.update(self.expand(root_obj))
            self._root_obj = main

        def expand(self, base: dict):  # [2]
            work = {}
            str_2_p = self.spec.str_to_path
            for k, v in base.items():
                nest = work
                p_nest = nest

                path = str_2_p(k)
                for part in path:
                    if part not in nest:
                        nest[part] = {}
                    p_nest = nest
                    nest = nest[part]
                v = {k: v for k, v in v.items()}
                p_nest[path[-1]].update(v)
            return work

        def handle_string(self, instance: str, **kwargs):  # [3]
            if (match := self.spec.SPECIAL_REGEX.match(instance)) is None:
                return instance
            else:
                start = match.groups()[0]
                if start == 'int':
                    return int(instance[4:-1])
                elif start == 'bool':
                    return bool(instance[5:-1])
                elif start == 'None':
                    return None
                elif start == 'float':
                    return float(instance[5:-1])
                else:
                    return literal_eval(instance)

        def handle_secondary_prim(self, instance: bool | int | float | NoneType, **kwargs):  # [4]
            return instance

        def handle_secondary_list_as_dict(self, instance: ListAsDict, **kwargs):
            return instance.list


    class CustomFormatter(Formatter):
        FORMAT_SETTINGS = CustomSpec()

        def serialized_obj_to_buffer(self, ser_obj: dict, context: FormatterContext) -> str:
            parser = configparser.ConfigParser()
            parser.optionxform = str
            parser.read_dict({k: v for k, v in reversed(ser_obj.items())})
            strio = StringIO()
            parser.write(strio)
            strio.seek(0)
            return strio.read()

        def buffer_to_obj(self, buffer, context: FormatterContext):
            parser = configparser.ConfigParser(default_section=None)
            parser.optionxform = str
            parser.read_string(buffer)
            return parser

        def get_serializer(self, root_obj, context: FormatterContext) -> Serializer:
            return CustomSerializer(root_obj, self.spec.copy(), context)

        def get_deserializer(self, root_obj, context) -> CustomDeSerializer:
            return CustomDeSerializer(root_obj, self.spec.copy(), context)

    formatter = CustomFormatter()
    d = formatter.dumps({
        'foo': 'bar',
        'baz': {
            'str': 'a string',
            'None': None,
            'bool': True,
            'int': 1,
            'custom handled': CustomFormatter,
            'datetime': datetime.datetime.now(),
            'pesky string': 'bool(True)',
            'quote char': "'",
            'other quote char': '"',
            'a list': [1, 2, 3, 4, 5]
        }
    })
    print(d)
    import pprint

    pprint.pprint(formatter.loads(d))


.. code-block::
  :caption: Output

    [MAIN]
    foo = bar

    [baz]
    str = a string
    None = None
    bool = bool(True)
    int = int(1)
    pesky string = 'bool(True)'
    quote char = "'"
    other quote char = '"'

    [baz.a list]
    __class__ = __main__.ListAsDict
    0 = int(1)
    1 = int(2)
    2 = int(3)
    3 = int(4)
    4 = int(5)

    [baz.datetime]
    __class__ = datetime.datetime

    [baz.datetime.state]
    __class__ = __main__.ListAsDict
    0 = int(2023)
    1 = int(1)
    2 = int(24)
    3 = int(1)
    4 = int(35)
    5 = int(25)
    6 = int(79852)

    [baz.custom handled]
    __class__ = abc.ABCMeta
    state = __main__.CustomFormatter


    {'baz': {'None': None,
             'a list': [1, 2, 3, 4, 5],
             'bool': True,
             'custom handled': <class '__main__.CustomFormatter'>,
             'datetime': datetime.datetime(2023, 1, 24, 1, 35, 25, 79852),
             'int': 1,
             'other quote char': '"',
             'pesky string': 'bool(True)',
             'quote char': "'",
             'str': 'a string'},
     'foo': 'bar'}

.. admonition:: Final Note

  What a mouthful! Who made this stupid framework?

This implementation has several problems including that escaping "bad strings" is not given any consideration, but I think it did a decent job hitting the concepts needed to extend the formatting classes.
