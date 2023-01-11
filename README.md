# Grave Settings
An extensible module for automatic serialization of python object hierarchies to storage. Supports arbitrary objects,
special ADTs and duck typing. Formats can be defined using the Formatter, Semantic, Route system.

Pre-defined formats:
- json (via built in json module)
- toml (read via tomlib, write enabled when tomli-w module is installed)
- bson (only tested experimentally)


## Features

- Save / Import types to reconstruct object hierarchies
- Preserve "is" relationships automatically by scanning object ids
- ADTs that support version management for updating old structures to new structures
- OrderedHandler objects allow for custom serialization / deserialization logic for types without using inheritance or duck typing
- Detect circular references
- Event handlers for finalizing serialization / deserialization (intended to fix circular references)
- Semantic objects for communicating options to the formatter (ex. security options for loading of arbitrary types)

<details><summary>Default standard handlers</summary>
<p>
Defining new handlers or adding functionality to the default handlers is easy, but some types have already been done:

| Name         | Description                                                  |
|--------------|--------------------------------------------------------------|
| Type         | built-in python type object                                  |
| NoneType     | None                                                         |
| Iterable     | General catch all for Iterable defined in collections module |
| Mapping      | General catch all for Mapping defined in collections module  |
| FunctionType | Python user-defined function                                 |
| date         | from datetime module                                         |
| datetime     | from datetime module                                         |
| timedelta    | from datetime module                                         |
| Enum         | from enum module                                             |

There is still a ways to go before most of the built in types have handlers. To see how the handlers work read:
[default_handlers.py](src/grave_settings/default_handlers.py)

</p>
</details>

## In progress
- Validation support
- Automated Qt GUI interface for editing settings objects


## Code Examples
Examples that demonstrate either serialization or deserialization are assumed to be invertible with 
similar logic

First we have a very simple object serialized without a handler, inheritance or duck typing

<table>
<tr>
<td>Using ConfigFile</td><td>Using Formatter</td>
</tr>
<tr>
<td>

```python
from pathlib import Path
from grave_settings.config_file import ConfigFile
from datetime import datetime

class MyObject:
    def __init__(self):
        self.attribute1 = 'test'
        self.attribute2 = datetime.now()


with ConfigFile(Path('text.json'), data=MyObject, formatter='json') as config:
    pass  # file will be saved automatically at the end of the with block
```

</td>
<td>

```python
from grave_settings.formatters.json import JsonFormatter
from datetime import datetime

class MyObject:
    def __init__(self):
        self.attribute1 = 'test'
        self.attribute2 = datetime.now()


formatter = JsonFormatter()
print(formatter.dumps(MyObject()))
```

</td>
</tr>
</table>

Output will look like this depending on the formatter specified:

<table>
<tr>
<td>json</td><td>toml</td>
</tr>
<tr>
<td>

```json
{
    "__class__": "__main__.MyObject",
    "attribute1": "test",
    "attribute2": {
        "__class__": "datetime.datetime",
        "state": [
            2023,
            1,
            11,
            8,
            1,
            4,
            825050
        ]
    }
}
```

</td>
<td>

```toml
__class__ = "__main__.MyObject"
attribute1 = "test"

[attribute2]
__class__ = "datetime.datetime"
state = [
    2023,
    1,
    11,
    8,
    14,
    18,
    503066,
]
```

</td>
</tr>
</table>

### ADTs and handlers

```python
from typing import Type

from grave_settings.abstract import Serializable, Route
from grave_settings.formatters.json import JsonFormatter
from datetime import datetime


class Color:  # required initialization parameters
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __str__(self):
        return f'Color(r={self.r}, g={self.g}, b={self.b})'

# Serialization / Deserialization functions are defined statically
def serialize_color(color: Color, route: Route, **kwargs):
    return {
        'r': color.r,
        'g': color.g,
        'b': color.b
    }


def deserialize_color(_type: Type[Color], dict_obj: dict, route: Route, **kwargs):
    return Color(dict_obj['r'], dict_obj['g'], dict_obj['b'])


class MyObject(Serializable):
    def __init__(self):
        # We reference the Color object
        self.attribute1 = Color(255, 255, 255)
        self.attribute2 = datetime.now()
        # The ADTs method will skip this attribute
        self.not_included = 'foo'

    @classmethod
    def check_in_serialization_route(cls, route: Route):
        route.handler.add_handler(Color, serialize_color)

    @classmethod
    def check_in_deserialization_route(cls, route: Route):
        route.handler.add_handler(Color, deserialize_color)

    def to_dict(self, route: Route, **kwargs) -> dict:
        return {
            'attribute1': self.attribute1,
            'attribute2': self.attribute2
        }

    def from_dict(self, state_obj: dict, route: Route, **kwargs):
        self.attribute1 = state_obj.pop('attribute1')
        self.attribute2 = state_obj['attribute2']


formatter = JsonFormatter()
obj_str = formatter.dumps(MyObject())
print(obj_str)
remade_obj = formatter.loads(obj_str)
print('-----------------')
print(remade_obj.attribute1)

```

<details><summary>Output</summary>
<p>

```json
{
    "__class__": "__main__.MyObject",
    "attribute1": {
        "__class__": "__main__.Color",
        "r": 255,
        "g": 255,
        "b": 255
    },
    "attribute2": {
        "__class__": "datetime.datetime",
        "state": [
            2023,
            1,
            11,
            10,
            36,
            42,
            827550
        ]
    }
}
-----------------
Color(r=255, g=255, b=255)
```

</p>
</details>

- serialize_color and deserialize_color do not need to be module level functions. They just need to have the same signature.
- check_in_serialization_route and check_in_deserialization_route are special methods that allow an object to manipulate the Route object before the object is processed
- check_in_deserialization_route in particular must be a class level function / method
- because of how Route works, the Color object will be handled by the functions we added for all child objects in the hierarchy

### Preserved "is" references

```python
from grave_settings.abstract import Serializable
from grave_settings.formatters.json import JsonFormatter


class MyObject(Serializable):
    def __init__(self):
        self.foo = [1, 2, 3]
        self.bar = self.foo


formatter = JsonFormatter()
obj_str = formatter.dumps(MyObject())
print(obj_str)
remade_obj = formatter.loads(obj_str)
print('-----------------')
print(remade_obj.foo is remade_obj.bar)
```

<details><summary>Output</summary>
<p>

```json
{
    "__class__": "__main__.MyObject",
    "bar": [
        1,
        2,
        3
    ],
    "foo": {
        "__class__": "grave_settings.helper_objects.PreservedReference",
        "ref": "\"bar\""
    }
}
-----------------
True
```

</p>
</details>

- Identical (not equivalent) objects are references instead of being serialized twice
- The "ref" object (string in this case) is handled by the Formatter object. This one uses mapping keys in either str or int form.
- The final print statement shows that the remade object maintains the "is" relationship between foo and bar


### Circular reference

```python
from grave_settings.abstract import Serializable, Route
from grave_settings.formatters.json import JsonFormatter
from grave_settings.helper_objects import PreservedReference
from grave_settings.semantics import NotifyFinalizedMethodName


class MyObject(Serializable):
    def __init__(self, foo=None):
        if foo is None:
            foo = MyObject(foo=self)
        self.foo = foo

    @classmethod
    def check_in_deserialization_route(cls, route: Route):
        route.add_frame_semantic(NotifyFinalizedMethodName('finalize'))

    def finalize(self, id_map: dict[str, PreservedReference]) -> None:
        if isinstance(self.foo, PreservedReference):
            self.foo = id_map[self.foo.ref]


formatter = JsonFormatter()
obj_str = formatter.dumps(MyObject())
print(obj_str)
remade_obj = formatter.loads(obj_str)
print('-----------------')
print(remade_obj.foo.foo is remade_obj)
```

<details><summary>Output</summary>
<p>

```json
{
    "__class__": "__main__.MyObject",
    "foo": {
        "__class__": "__main__.MyObject",
        "foo": {
            "__class__": "grave_settings.helper_objects.PreservedReference",
            "ref": ""
        }
    }
}
-----------------
True
```

</p>
</details>

- In this case the root objects "foo" attribute references an object who's "foo" attribute references the root object
- This case involves a Semantic (NotifyFinalizedMethodName), specifically a frame semantic, which only applies to the object it is added in and not any sub objects in the hierarchy
- NotifyFinalizedMethodName registers the method named "finalize" as the objects finalizer
- finalizers run when the serialization / deserialization process has completed in the formatter but before the Route object is cleared
- finalizers run in the order they are registered
- ref = "" references the root object in this case
- Since this object inherits from Serializable the "finalize" method is an override, the base class version does the same thing but in a brute-force fashion for all attributes
  - Note that the base class method will not work if the circular reference exists in a container like a list, dict unmanaged object. In this case you will have to fix the circular reference in a custom method like the above