Config File Example
======================

Config files are the high-level type that are meant to manage most of the use cases of the framework. You are encouraged to extend ConfigFile to suit your needs

Basic Example
-----------------

.. code-block:: python

    import os
    from pathlib import Path
    from grave_settings.config_file import ConfigFile
    from datetime import datetime

    if os.path.exists('test.json'):
        print(f'I dont want to overwrite your file: "test.json"')
        exit()


    class MyObject:
        def __init__(self):
            self.attribute1 = 'test'
            self.attribute2 = datetime.now()


    with ConfigFile(Path('test.json'), data=MyObject, formatter='json') as config:
        pass  # file will be saved automatically at the end of the with block

    with open('test.json', 'r') as f:
        print(f.read())

    os.remove('test.json')

.. code-block::
  :caption: Output

    {
        "__class__": "__main__.MyObject",
        "attribute1": "test",
        "attribute2": {
            "__class__": "datetime.datetime",
            "state": [
                2023,
                1,
                24,
                16,
                31,
                46,
                143836
            ]
        }
    }

First we defined a type that will be our container. This type is ``MyObject``. The class is given to the :py:class:`~grave_settings.config_file.ConfigFile` constructor as the named parameter ``data``. The reason we pass the type in is, if the file already existed and contained serialized data we don't want to instantiate ``MyObject`` just to throw it out immediately with a replacement. Also, we want the deserialization process to anticipate the file containing data that describes an object of the correct type to avoid attacks (this is only a very basic security measure) but more precisely to avoid errors. If the type in the file does not match the type supplied by the ``data`` kwarg a :py:class:`~grave_settings.semantics.SecurityException` is raised. This behavior exists because of the logic in :py:meth:`~grave_settings.config_file.ConfigFile.get_deserialization_context`.

When the file does not exist and there is no data to reconstruct the object of type ``MyObject`` it is created by :py:meth:`~grave_settings.config_file.ConfigFile.__enter__` by calling :py:meth:`~grave_settings.config_file.ConfigFile.instantiate_data`. As long as the type doesnt have positional arguments, this should be fine.


A less basic example
-----------------------

Lets make our object hierarchy more complex.

.. code-block:: python

    import os
    from pathlib import Path
    from grave_settings.config_file import ConfigFile

    paths = [Path('test.json'), Path('pen1.json'), Path('pen2.json')]

    for path in paths:
        if path.exists():
            print(f'I dont want to overwrite your file: "test.json"')
            exit()


    class Color:
        def __init__(self, r, g, b):
            self.r = r
            self.g = g
            self.b = b


    class Pen:
        def __init__(self, color: Color = None, width: int = 1):
            self.color = color
            self.width = width


    class MyObject:
        def __init__(self):
            self.foreground_color = Color(255, 0, 0)
            self.background_color = Color(255, 255, 255)
            self.active_pen = None
            self.pens: list[Pen] = []

        def select_pen(self, index: int):
            self.active_pen = self.pens[index]
            self.foreground_color = self.active_pen.color

        def add_pen(self, pen: Pen):
            self.pens.append(pen)


    def make_pen_config(fn: Path, pen: Pen) -> ConfigFile:
        cfg = ConfigFile(fn, formatter='json')
        cfg.data = pen
        return cfg


    with ConfigFile(Path('test.json'), data=MyObject, formatter='json') as config:
        obj: MyObject = config.data
        obj.add_pen(Pen(color=Color(23, 25, 25)))
        obj.add_pen(Pen(color=Color(45, 45, 45), width=2))
        config.add_config_dependency(make_pen_config(Path('pen1.json'), obj.pens[0]))
        config.add_config_dependency(make_pen_config(Path('pen2.json'), obj.pens[1]))
        obj.select_pen(0)

    for path in paths:
        print(f'---------- {path} -----------')
        with open(path, 'r') as f:
            print(f.read())
        os.remove(path)

.. note::

    This demo is meant to show how linking :py:class:`~grave_settings.config_file.ConfigFile` can be done. The manner in which is is done here a questionable but it's hard to find a good example that is simple. I just want to make it clear that linking config files should be something that has a lot more structure around it or it probably is not necessary in your program.

.. code-block::

    ---------- test.json -----------
    {
        "__class__": "__main__.MyObject",
        "active_pen": {
            "__class__": "grave_settings.config_file.LogFileLink",
            "rel_path": {
                "__class__": "pathlib.PosixPath",
                "path": "/home/ryan/.config/JetBrains/PyCharm2022.3/scratches/pen1.json",
                "abs": false,
                "rel_path": "pen1.json"
            },
            "config": {
                "__class__": "grave_settings.config_file.ConfigFile",
                "formatter_t": {
                    "__class__": "abc.ABCMeta",
                    "state": "grave_settings.formatters.json.JsonFormatter"
                },
                "data_t": {
                    "__class__": "builtins.type",
                    "state": "__main__.Pen"
                }
            }
        },
        "background_color": {
            "__class__": "__main__.Color",
            "b": 255,
            "g": 255,
            "r": 255
        },
        "foreground_color": {
            "__class__": "__main__.Color",
            "b": 25,
            "g": 25,
            "r": 23
        },
        "pens": [
            {
                "__class__": "grave_settings.formatter_settings.PreservedReference",
                "ref": "\"active_pen\""
            },
            {
                "__class__": "grave_settings.config_file.LogFileLink",
                "rel_path": {
                    "__class__": "pathlib.PosixPath",
                    "path": "/home/ryan/.config/JetBrains/PyCharm2022.3/scratches/pen2.json",
                    "abs": false,
                    "rel_path": "pen2.json"
                },
                "config": {
                    "__class__": "grave_settings.config_file.ConfigFile",
                    "formatter_t": {
                        "__class__": "grave_settings.formatter_settings.PreservedReference",
                        "ref": "\"active_pen\".\"config\".\"formatter_t\""
                    },
                    "data_t": {
                        "__class__": "grave_settings.formatter_settings.PreservedReference",
                        "ref": "\"active_pen\".\"config\".\"data_t\""
                    }
                }
            }
        ]
    }
    ---------- pen1.json -----------
    {
        "__class__": "__main__.Pen",
        "color": {
            "__class__": "__main__.Color",
            "b": 25,
            "g": 25,
            "r": 23
        },
        "width": 1
    }
    ---------- pen2.json -----------
    {
        "__class__": "__main__.Pen",
        "color": {
            "__class__": "__main__.Color",
            "b": 45,
            "g": 45,
            "r": 45
        },
        "width": 2
    }

Lets point out something important about :py:meth:`~grave_settings.config_file.ConfigFile.add_config_dependency`, as of right now nothing is shared between the config files. This includes semantics and references. This means that "is" relationships are not shared between config files. This can be done, but I'm not sure if I need it enough to work out the kinks. It should be doable within the :py:class:`~grave_settings.config_file.ConfigFile`.