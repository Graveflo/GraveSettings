Formatters
===========



The implementation of Formatter would be fairly straight forward if it were not for two issues, one affecting serialization and the other deserialization. Both issues involve preserving object references.

The serialization process has to keep track of all the ids that may be references more then once, but it does not know where an object "comes from." (maybe link to Temporary documentation here) By this I mean it has no knowledge of if a "dict" object it observes was created in a handler, to_dict() method (during the serialization process) or if is referenced by the original object hierarchy. It is highly encouraged to treat these two kinds of object differently because recognizing which objects are equal relies on determining their uniqueness. We do this by reading it's object id with the built-in id() function. The problem is that if we dereference an object after we cached its object id, when a new object is created it will probably take the id of the object that was just dereferenced causing incorrect connections between referenced objects. This is mitigated by making sure that all objects who's ids are cached ultimately have the same "lifecycle" as all other objects that are cached. This is easy enough, we just add them to a set (this can be turned off since it *shouldn't* be necessary).

# TODO: implement and link to semantic

 Here in lies the next problem. If we add all the objects that are processed to a set to maintain their lifecycle then we are pretty much doubling our memory footprint (or worse as you'll see). We can also do destructive things to the temporary objects because it can be assumed that once they are given to the formatter they "belong" to the formatter since they dont belong to anyone else at that point. We can save even more hassle by overwriting the container objects in place instead of creating yet another copy of the structure (we could at least avoid caching their reference at this
 point though). If we can distinguish between Temporary objects that are just meant to communicate structure to the formatter and objects that are a part of the user's data hierarchy the woes disappear, so we do this. The serialization method has the added complication of being aware of Temporary objects because it saves a lot of trouble, all things considered.
