Circular References
=======================

Below are examples of dealing with circular references when using the built in functionality provided by the :py:class:`AutoPreserveReferences<grave_settings.semantics.AutoPreserveReferences>` and :py:class:`ResolvePreservedReferences<grave_settings.semantics.ResolvePreservedReferences>` semantics (enabled by default). When these semantics are not used, circular references
will simply blow up the execution stack and cause a :py:class:`builtins.RecursionError`

Lets look at a basic example of a circular reference. Here is some code that serializes a circular reference:

