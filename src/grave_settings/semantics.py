from typing import Generic

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


class PreserveDictionaryOrdering(Semantic[bool]):
    '''
    Keep the ordering of dictionary objects consistent between the format and the python object hierarchy
    '''
    pass


class AutoKeySerializableDict(Semantic[bool]):
    '''
    Automatically scan dictionary objects to ensure their keys are serializable as native format keys. If not they
    are converted to KeySerializableDict objects (represented as an array of tuples (key, value))
    '''
    pass


class Indentation(Semantic[int]):
    '''
    Specified indentation formatting if applicable
    '''
    def __init__(self, val: T):
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


class PreScanPreservedReferences(Semantic[bool]):
    '''
    Load the entire object tree before scanning for preserved references. This is a method of deserialization that
    avoids temporarily assigning PreservedReference objects to live objects
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

# TODO: add a semantic that restrics loading types for cyber security resons