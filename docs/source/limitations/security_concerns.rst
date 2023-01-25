Security Concerns
====================

This section is a wip. Here are some basic examples of *some* security concerns when all the unsafe Semantics are turned on

Importing dropped files
--------------------------

Without any restrictions on importing files a malicious actor could drop a python file in a location that is importable and then reference the module they dropped in a config file. This will run arbitrary code in the module

Replacing functions by name
------------------------------

If you are using a bare python object instead of something like :py:class:`~grave_settings.base.SlotSettings` a malicious user could add a settings key to the file that has the same name as a python method on that object. The methods name might get overriden by the object they described in the file and then that method is called it will call the deserialized object, not the objects method. This can be used for arbitrary code execution.

Accessing built in functions
-------------------------------

Although importing can be disabled with the :py:class:`~grave_settings.semantics.DoNotAllowImportingModules` this does not stop someone from using the builtins to their advantage. In fact it is probably possible to do something like reference the ``__import__`` function in python and then manipulate the object structure to trick client code into doing an import anyway. Blocking imports does not affect modules that re currently loaded in the system modules list. This can be hard to track and a surprising amount of objects / functions etc may be available to an attacker even with this limitation.

Do-something constructors
---------------------------

Objects that have constructors that "do something" may be exploited by this system because simply declaring the state of the objects can give an attacker a directive that they can use to structure an attack in a file. If they know that simply instantiating a object of type X has the effect Y and the type is importable then they can make Y happen simply by describing the object.
