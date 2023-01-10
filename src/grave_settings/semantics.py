from functools import singledispatch
from typing import Generic, Type

from ram_util.utilities import T


class SymantecNotSupportedError(Exception):
    pass


class SymantecConfigurationInvalid(Exception):
    pass


class Semantic(Generic[T]):
    def __init__(self, value: T):
        self.val = value

    def __bool__(self):
        return bool(self.val)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        if other.val != self.val:
            return False
        return True

    def __hash__(self):
        return hash(hash(self.__class__) + hash(self.val))


@singledispatch
def remove_semantic_from_dict(semantic: Type[Semantic], dict_obj: dict[Type[Semantic], Semantic]):
    if semantic in dict_obj:
        dict_obj.pop(semantic)


@remove_semantic_from_dict.register
def _(semantic: Semantic, dict_obj: dict[Type[Semantic], Semantic]):
    smc = semantic.__class__
    if smc in dict_obj:
        if dict_obj[smc].val == semantic.val:
            dict_obj.pop(smc)


class PreserveDictionaryOrdering(Semantic[bool]):
    '''
    Keep the ordering of dictionary objects consistent between the format and the python object hierarchy
    '''
    pass


class PreserveSerializableKeyOrdering(Semantic[bool]):
    '''
    Similar to PreserveDictionaryOrdering but for serializable objects. This includes auto-serialized objects.
    '''
    pass


class SerializeNoneVersionInfo(Semantic[bool]):
    '''
    If this is False then versioned objects that have null version information will not serialize their version
    information. The result is a cleaner file, but it is not always the case that null version information is the same
    as being unversioned
    '''
    pass

class AutoKeySerializableDictType(Semantic[Type]):
    '''
    Automatically scan dictionary objects to ensure their keys are serializable as native format keys. If not they
    are replaced by a wrapper type whose factory is supplied to this semantic's constructor
    '''
    pass


class Indentation(Semantic[int]):
    '''
    Specified indentation formatting if applicable
    '''
    def __init__(self, val: int):
        super().__init__(val)



class Mulitwrite(Semantic[bool]):
    '''
    This will write/ read the config file in chunks, lines or sub sections in order to preserve memory. Otherwise the
    formatter may serialize or deserialize the entire object tree in one go.
    '''
    pass


class AutoPreserveReferences(Semantic[bool]):
    '''
    The formatter will keep track of objects that are referenced more than once in the object hierarchy and automatically
    convert subsequent instanced of the same object to a PreservedReference
    '''
    pass


class DetonateDanglingPreservedReferences(Semantic[bool]):
    '''
    This will call a method that raises an exception if any tracked PreservedReference has not been flagged for garbage
    collection at the end of the deserialization process. It can be used to test if all the PreservedReference objects
    have been replaced by their correct reference since they should all be de-referenced by the end of the process.
    '''
    pass


class ResolvePreservedReferences(Semantic[bool]):
    '''
    Preserved References are resolved by the formatter and never given to the object. This may be slower. but
    it ensures that the object will never have a property set that is of type PreservedReference. When this is not
    present the formatter should not resolve the preserved references. Objects can resolve them by subscribing to the
    Route objects
    '''
    pass


class NotifyFinalizedMethodName(Semantic[str]):
    pass

# TODO: add a semantic that restrics loading types for cyber security resons (maybe wait until validator is done?)