import os
from typing import Generic, Type, TypeVar, Callable, Any, Iterable, Self

from grave_settings.utilities import T, format_class_str


class SymantecNotSupportedError(Exception):
    pass


class SymantecConfigurationInvalid(Exception):
    pass


class SecurityException(Exception):
    pass


class OmitMeError(Exception):
    """
    raise this to retroactively refuse to be serialized as an attribute or dictionary key
    """
    pass


class Negate:
    __slots__ = 'semantic',

    def __init__(self, semantic):
        self.semantic = semantic

    def __neg__(self):
        return self.semantic


class Semantic(Generic[T]):
    """
    Semantics are meant to be "frozen" in that they do not change state after they have been initialized. They may be
    passed from context to context without respect for consistency or state and are expected to always have the same
    meaning no matter where and "when" they are.
    """
    __slots__ = 'val',
    COLLECTION: Type[set] | None = None
    C_T = TypeVar('C_T', bound=COLLECTION)

    def __init__(self, value: T):
        self.val = value

    def collection_add(self, collection):
        collection.add(self)

    def collection_remove(self, collection):
        collection.remove(self)

    @staticmethod
    def collection_copy(collection) -> C_T:
        return collection.copy()

    @staticmethod
    def collection_concatenate(first: C_T, second: C_T):
        return first | second

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

    def __str__(self):
        return f'{self.__class__.__name__}({self.val})'

    def __repr__(self):
        return f'{self.__class__.__name__}({repr(self.val)})'

    def __invert__(self):
        return Negate(self)


T_S = TypeVar('T_S', bound=Semantic)
T_S_E = TypeVar('T_S_E', bound=Semantic | Negate)


class Semantics:
    def __init__(self, semantics: dict[Type[T_S], T_S | set[T_S]] = None):
        if semantics is None:
            semantics = {}
        self.semantics = semantics
        self.parent: None | Semantics = None

    def update(self, semantics: Iterable[T_S_E]):
        self.add_semantics(*semantics)

    def add_semantics(self, *semantics: T_S_E):
        dict_obj = self.semantics
        for semantic in semantics:
            if type(semantic) is Negate:
                if type(semantic.semantic) is type:
                    self.pop(semantic.semantic)
                else:
                    self.remove_semantic(semantic.semantic)
                continue
            if semantic.COLLECTION is None:
                dict_obj[semantic.__class__] = semantic
            else:
                smc = semantic.__class__
                if smc in dict_obj:
                    semantic.collection_add(dict_obj[smc])
                else:
                    collect = smc.COLLECTION()
                    semantic.collection_add(collect)
                    dict_obj[smc] = collect

    def __getitem__(self, semantic_class: Type[T_S]) -> T_S | list[T_S] | None:
        if self.parent is None:
            return self.get_semantic(semantic_class)
        else:
            if (ps := self.parent.get_semantic(semantic_class)) is not None:
                if semantic_class.COLLECTION is None:
                    return ps
                else:
                    if s := self.get_semantic(semantic_class):
                        return semantic_class.collection_concatenate(ps, s)  # order matters for overwrite
                    else:
                        return ps
            return self.get_semantic(semantic_class)
    
    def get_semantic(self, semantic_class: Type[T_S]) -> T_S | list[T_S] | None:
        if semantic_class in self.semantics:
            return self.semantics[semantic_class]

    def __delitem__(self, key: Type[T_S]):
        self.pop(key)

    def pop(self, key: Type[T_S]):
        return self.semantics.pop(key)

    def remove_semantic(self, semantic: Semantic):
        smc = semantic.__class__
        dict_obj = self.semantics

        if smc in dict_obj:
            if smc.COLLECTION is None:
                if dict_obj[smc].val == semantic.val:
                    del self[smc]
            else:
                semantics = dict_obj[smc]
                items = tuple(ins for ins in semantics if ins.val == semantic.val)
                if len(semantics) == len(items):
                    del self[smc]
                for item in reversed(items):
                    item.collection_remove(semantics)

    def __contains__(self, item: Type[Semantic] | Semantic) -> bool:
        if self.parent is not None:
            if item in self.parent:
                return True
        if isinstance(item, Semantic):
            if item.COLLECTION is None:
                return self[item.__class__] == item
            else:
                if (v := self[item.__class__]) is None:
                    return False
                return item in v
        else:
            return item in self.semantics

    def copy(self) -> Self:
        sems = self.__class__(semantics=self.semantics.copy())
        return sems

    def __str__(self):
        sems = set()
        for semantic in self.semantics.values():
            if isinstance(semantic, Semantic):
                sems.add(str(semantic))
            else:
                sems.update(str(s) for s in semantic)
        sems_str = ', '.join(sems)
        return f'{self.__class__.__name__}({sems_str}, parent={str(self.parent)})'

    def __bool__(self):
        return len(self.semantics) > 0 or len(self.parent) > 0

    def __len__(self):
        return len(self.semantics)

    def __iter__(self):
        for sem in self.semantics.values():
            if isinstance(sem, Semantic):
                yield sem
            else:
                yield from sem


class SemanticContext(Semantics):
    def __init__(self, semantics: Semantics):
        super().__init__(semantics=semantics.semantics.copy())
        self.stack = []

    def add_frame_semantics(self, *semantic: T_S_E):
        if self.parent is None:
            self.parent = Semantics()
        self.parent.add_semantics(*semantic)

    def remove_frame_semantic(self, semantic: Type[Semantic] | Semantic):
        if self.parent is not None:
            if type(semantic) is type:
                self.parent.pop(semantic)
            else:
                self.parent.remove_semantic(semantic)

    def add_semantics(self, *semantics: T_S_E):
        if self.semantics is None:
            self.semantics = {}
        return super().add_semantics(*semantics)
    
    def get_semantic(self, semantic_class: Type[T_S]) -> T_S | list[T_S] | None:
        if self.semantics is None:
            return None
        return super().get_semantic(semantic_class)

    def __getitem__(self, semantic_class: Type[T_S]) -> T_S | list[T_S] | None:
        if self.semantics is None:
            if self.parent is None:
                return None
            return self.parent[semantic_class]
        return super().__getitem__(semantic_class)

    def remove_semantic(self, semantic: Type[Semantic] | Semantic):
        if self.semantics is None:
            return
        super().remove_semantic(semantic)

    def copy_semantics(self):
        sems = self.semantics.copy()
        for k, v in sems.items():
            if k.COLLECTION is not None:
                sems[k] = k.collection_copy(v)
        return sems

    def context_push(self):
        self.stack.append(self.copy_semantics())
        self.stack.append(self.parent)
        self.parent = None

    def context_pop(self):
        self.parent = self.stack.pop(-1)
        self.semantics = self.stack.pop(-1)

    def __enter__(self) -> Self:
        self.context_push()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context_pop()

    def __str__(self):
        bs = [f'Semantic Context ({format_class_str(self.__class__)})']
        for s in self.stack:
            bs.append(f'\t{s}')
        return os.linesep.join(bs)


class IgnoreDuckTypingForType(Semantic[Type]):
    """
    Disables duck typing in the formatter for a specific class. This is to take care of naming clashes with types that
    happen to share the same name as the built-in methods
    """
    pass


class IgnoreDuckTypingForSubclasses(Semantic[Type]):
    """
    Disables duck typing in the formatter for a specific class. This is to take care of naming clashes with types that
    happen to share the same name as the built-in methods
    """
    pass


class OmitMe(Semantic):
    """
    Used to inform that an object's parent should not include this object as a member. It's probably a bad idea to overuse
    this, but it is meant for flagging objects that should never be serialized or represented in an objects state
    """
    def __init__(self):
        raise NotImplementedError('This is not meant to be instantiated. Raise OmitMeError if you want this functionality')


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


class OverrideClassString(Semantic[str]):
    """
    The default class string is overriden by a custom value when serializing
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
    pass


class AutoPreserveReferences(Semantic[bool]):
    """
    The formatter will keep track of objects that are referenced more than once in the object hierarchy and automatically
    convert subsequent instanced of the same object to a PreservedReference
    """
    pass


class EnforceReferenceLifecycle(Semantic[bool]):
    """
    Ensures that an object id that is used to cache an object for PreservedReferences is not re-used by the interpreter
    by maintaining a reference to all objects cached for the duration of the operation.
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
    context objects
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
    COLLECTION = set


class KeySemanticsTemplate(Semantic[dict[Any, Iterable[Semantic]]]):
    pass

