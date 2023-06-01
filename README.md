# Grave Settings

A library for automatic serialization of python object hierarchies to storage. Most python objects are 
compatible without any extra code, and there are several tools for fine-grain control.

The framework uses either duck typing or strong typing to allow objects define custom behaviors and defines a Formatter 
class to allow for user defined input/output formats

Pre-defined formats:
- json (via built in json module)
- toml (read via tomlib, write enabled when tomli-w module is installed)
- bson (only tested experimentally)

Red the [documenation](https://ilikescaviar.github.io/GraveSettings/) for examples and important considerations.

## Install

```
pip install grave-settings
```

## Features

- Save / Import types to reconstruct object hierarchies
- Preserve "is" relationships automatically by scanning object ids
- Abstractions for object version management for easing continuous deployment
- OrderedHandler objects allow for custom serialization / deserialization logic for types without using inheritance or duck typing
- Detect circular references
- Event handlers for finalizing serialization / deserialization (intended to fix circular references)
- Semantic objects for communicating options to the formatter (ex. security options for loading of arbitrary types)

<details><summary>Default standard handlers</summary>
<p>
Defining new handlers or adding functionality to the default handlers is easy, but some types have already been done:

| Name               | Description                                                  |
|--------------------|--------------------------------------------------------------|
| Type               | built-in python type object                                  |
| NoneType           | None                                                         |
| Iterable           | General catch all for Iterable defined in collections module |
| Mapping            | General catch all for Mapping defined in collections module  |
| FunctionType       | Python user-defined function                                 |
| date               | from datetime module                                         |
| datetime           | from datetime module  (experimental timezone support)        |
| timedelta          | from datetime module                                         |
| Enum               | from enum module                                             |
| partial            | builtin partial class                                        |
| bytes              | builtin bytes data                                           |
| Complex / Rational | builtin numerical classes                                    |
| Path               | from pathlib                                                 |

There is still a ways to go before most of the built in types have handlers. To see how the handlers work read:
[default_handlers.py](src/grave_settings/default_handlers.py)

</p>
</details>

## In progress
- Validation support
- Automated Qt GUI interface for editing settings objects


## Code Example
Here is a quick example that serializes and then deserializes a custom object hierarchy with the default built in classes


```python
from datetime import date

from grave_settings.formatters.toml import TomlFormatter


class Color:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __str__(self):
        return f'Color(r={self.r}, g={self.g}, b={self.b})'


class MyObject:
    def __init__(self):
        self.integer = 1
        self.string = 'b'
        self.function = print  # demonstrates handling a function
        self.type_object = int  # demonstrates handling a type
        # demonstrates handling a list of date objects
        self.dates = [date(year=2022, month=1, day=1), date(year=2023, month=2, day=2)]
        # demonstrates handling a nested object
        self.color = Color(255, 255, 255)

formatter = TomlFormatter()
obj_str = formatter.dumps(MyObject())
print(obj_str)
```

This will output:

```toml
__class__ = "__main__.MyObject"
integer = 1
string = "b"

[function]
__class__ = "types.FunctionType"
state = "builtins.print"

[type_object]
__class__ = "builtins.type"
state = "builtins.int"

[[dates]]
__class__ = "datetime.date"
state = [
    2022,
    1,
    1,
]

[[dates]]
__class__ = "datetime.date"
state = [
    2023,
    2,
    2,
]

[color]
__class__ = "__main__.Color"
r = 255
g = 255
b = 255
```

Now if we take this string and deserialize it with the same (or equivalent) formatter:

```python
from grave_settings.formatters.toml import TomlFormatter
formatter = TomlFormatter()
remade_obj = formatter.loads(obj_str)
print(f'''
integer = {remade_obj.integer}
string = {remade_obj.string}
function = {remade_obj.function}
type_object = {remade_obj.type_object}
dates = {remade_obj.dates}
color = {remade_obj.color}
''')
```

We get:

```
integer = 1
string = b
function = <built-in function print>
type_object = <class 'int'>
dates = [datetime.date(2022, 1, 1), datetime.date(2023, 2, 2)]
color = Color(r=255, g=255, b=255)
```

It is recommended to use the Serializable type (in this module) or handlers instead of using the naked objects like above.
Read the documentation for more on this.