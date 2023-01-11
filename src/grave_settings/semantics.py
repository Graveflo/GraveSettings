from functools import singledispatch
from typing import Generic, Type, TypeVar, Callable

from ram_util.utilities import T


class SymantecNotSupportedError(Exception):
    pass


class SymantecConfigurationInvalid(Exception):
    pass


class SecurityException(Exception):
    pass


class Semantic(Generic[T]):
    VALUE_OVERWRITES = True

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
def _(semantic: Semantic, dict_obj: dict[Type[Semantic], Semantic | list[Semantic]]):
    smc = semantic.__class__
    if smc in dict_obj:
        if smc.VALUE_OVERWRITES:
            if dict_obj[smc].val == semantic.val:
                dict_obj.pop(smc)
        else:
            semantics = dict_obj[smc]
            idxs = list(i for i, ins in enumerate(semantics) if ins.val == semantic.val)
            if len(semantics) == len(idxs):
                return remove_semantic_from_dict(smc, dict_obj)
            for idx in reversed(idxs):
                semantics.pop(idx)


def add_semantic(semantic: Semantic, dict_obj: dict[Type[Semantic]]):
    if semantic.VALUE_OVERWRITES:
        dict_obj[semantic.__class__] = semantic
    else:
        smc = semantic.__class__
        if smc in dict_obj:
            dict_obj[smc].append(semantic)
        else:
            dict_obj[smc] = [semantic]


class PreserveDictionaryOrdering(Semantic[bool]):
    """
    Keep the ordering of dictionary objects consistent between the format and the python object hierarchy
    """
    pass


class PreserveSerializableKeyOrdering(Semantic[bool]):
    """
    Similar to PreserveDictionaryOrdering but for serializable objects. This includes auto-serialized objects.
    """
    pass


class SerializeNoneVersionInfo(Semantic[bool]):
    """
    If this is False then versioned objects that have null version information will not serialize their version
    information. The result is a cleaner file, but it is not always the case that null version information is the same
    as being unversioned
    """
    pass


class AutoKeySerializableDictType(Semantic[Type]):
    """
    Automatically scan dictionary objects to ensure their keys are serializable as native format keys. If not they
    are replaced by a wrapper type whose factory is supplied to this semantic's constructor
    """
    pass


class Indentation(Semantic[int]):
    """
    Specified indentation formatting if applicable
    """
    def __init__(self, val: int):
        super().__init__(val)


class MultiWrite(Semantic[bool]):
    """
    This will write/ read the config file in chunks, lines or subsections in order to preserve memory. Otherwise, the
    formatter may serialize or deserialize the entire object tree in one go.
    """
    pass


class AutoPreserveReferences(Semantic[bool]):
    """
    The formatter will keep track of objects that are referenced more than once in the object hierarchy and automatically
    convert subsequent instanced of the same object to a PreservedReference
    """
    pass


class DetonateDanglingPreservedReferences(Semantic[bool]):
    """
    This will call a method that raises an exception if any tracked PreservedReference has not been flagged for garbage
    collection at the end of the deserialization process. It can be used to test if all the PreservedReference objects
    have been replaced by their correct reference since they should all be de-referenced by the end of the process.
    """
    pass


class ResolvePreservedReferences(Semantic[bool]):
    """
    Preserved References are resolved by the formatter and never given to the object. This may be slower. but
    it ensures that the object will never have a property set that is of type PreservedReference. When this is not
    present the formatter should not resolve the preserved references. Objects can resolve them by subscribing to the
    Route objects
    """
    pass


class NotifyFinalizedMethodName(Semantic[str]):
    """
    This can be used as a frame semantic while de-serializing to get a callback on a method designated by the argument.
    The argument should be the method name as it is a member of the current object. The signature or the callback
    should match the signature of Serializable's finalize method. currently:
    (self, id_map: dict) -> None:

    The id_map will be a dictionary of reference ids to de-serialized objects. The references ids should be consistent
    with PreservedReference's "ref" member variable.
    """
    pass


class DoNotAllowImportingModules(Semantic[bool]):
    """
    When de-serializing, do not import modules that are not currently loaded in the system path. This will disallow the
    loading of arbitrary python modules if they are not already loaded.
    """
    pass


class ClassStringPassFunction(Semantic[Callable[[str], bool]]):
    """
    Define a function that will return a boolean specifying the acceptability of a class path string. If the function
    returns false the class/module will not be imported, executed or instantiated and instead a SecurityException will
    be raised.
    """
    VALUE_OVERWRITES = False
    pass


T_S = TypeVar('T_S', bound=Semantic)
