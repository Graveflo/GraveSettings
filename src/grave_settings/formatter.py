# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import re
from abc import ABC, abstractmethod
from io import IOBase
from typing import Any, get_args, Self
from weakref import WeakSet

from ram_util.modules import load_type

from grave_settings.abstract import VersionedSerializable, Route
from grave_settings.default_handlers import DeSerializationHandler, SerializationHandler
from grave_settings.default_route import DefaultRoute
from grave_settings.handlers import MroHandler, OrderedHandler
from grave_settings.helper_objects import PreservedReferenceNotDissolvedError, KeySerializableDictNumbered, \
    PreservedReference, KeySerializableDict
from grave_settings.formatter_settings import FormatterSettings, Temporary
from grave_settings.semantics import *


class FormatterFrame:
    def __init__(self):
        self.key_path = []

    def update(self, obj: Self):
        self.key_path = obj.key_path.copy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.key_path.pop(-1)

    def __call__(self, path):
        self.key_path.append(path)
        return self


class IFormatter(ABC):
    def to_buffer(self, data, _io: IOBase, encoding='utf-8', route: Route = None):
        buffer = self.dumps(data, route=route)
        if encoding is not None and encoding != 'utf-8':
            buffer = buffer.encode(encoding)
        _io.write(buffer)

    def write_to_file(self, settings, path: str, encoding='utf-8', route: Route = None):
        if encoding == 'utf-8':
            f = open(path, 'w')
        else:
            f = open(path, 'wb')
        with f:
            # noinspection PyTypeChecker
            self.to_buffer(settings, f, encoding=encoding, route=route)

    def from_buffer(self, _io: IOBase, encoding='utf-8', route: Route = None):
        data = _io.read()
        if encoding is not None and encoding != 'utf-8':
            data = data.decode(encoding)
        return self.loads(data, route=route)

    def read_from_file(self, path: str, encoding='utf-8', route=None):
        if encoding == 'utf-8':
            f = open(path, 'r')
        else:
            f = open(path, 'rb')
        with f:
            # noinspection PyTypeChecker
            return self.from_buffer(f, encoding=encoding, route=route)

    @abstractmethod
    def serialized_obj_to_buffer(self, ser_obj) -> str | bytes:
        pass

    @abstractmethod
    def buffer_to_obj(self, buffer: str | bytes):
        pass

    def get_serialization_handler(self) -> OrderedHandler:
        return SerializationHandler()

    def get_deserialization_handler(self) -> OrderedHandler:
        return DeSerializationHandler()

    def get_serialization_route(self) -> Route:
        return DefaultRoute(self.get_serialization_handler())

    def get_deserialization_route(self) -> Route:
        return DefaultRoute(self.get_deserialization_handler())

    def dumps(self, obj: Any, route=None) -> str | bytes:
        if route is None:
            route = self.get_serialization_route()
        return self.serialized_obj_to_buffer(self.serialize(obj, route))

    def loads(self, buffer, route=None):
        if route is None:
            route = self.get_deserialization_route()
        return self.deserialize(self.buffer_to_obj(buffer), route)

    @abstractmethod
    def serialize(self, obj: Any, route: Route, **kwargs):
        pass

    @abstractmethod
    def deserialize(self, obj, route: Route, **kwargs):
        pass

    @abstractmethod
    def supports_semantic(self, semantic_class: Type[Semantic]) -> bool:
        pass

    @abstractmethod
    def add_semantic(self, symantec: Semantic):
        pass

    @abstractmethod
    def get_semantic(self, semantic_class: Type[T_S]) -> T_S:
        pass

    @abstractmethod
    def remove_semantic(self, semantic_class: Type[Semantic] | Semantic):
        pass

    @abstractmethod
    def has_semantic(self, semantic_class: Type[Semantic] | Semantic) -> bool:
        pass


class Formatter(IFormatter, ABC):
    FORMAT_SETTINGS = FormatterSettings()
    TYPES = FORMAT_SETTINGS.type_primitives | FORMAT_SETTINGS.type_special

    def __init__(self, settings: FormatterSettings = None):
        if settings is None:
            settings = self.FORMAT_SETTINGS.copy()
        self.settings = settings
        self.primitives = set(get_args(self.settings.type_primitives))
        self.special = set(get_args(self.settings.type_special))
        self.attribute = set(get_args(self.settings.type_attribute))

        self.serialization_handler = MroHandler()
        self.frame = FormatterFrame()
        self.id_cache = {}
        self.id_lifecycle_objects = []
        self.root_object = None
        self.preserved_refs = WeakSet()
        self.serialization_handler.add_handlers_by_annotated_callable(
            self.handle_user_list,
            self.handle_user_dict,
            self.handle_temporary
        )
        self.deserialization_handler = MroHandler()
        self.deserialization_handler.add_handlers_by_annotated_callable(
            self.handle_deserialize_list,
            self.handle_deserialize_dict
        )
        self.semantics: dict[Type[T_S], T_S] = {
            AutoKeySerializableDictType: AutoKeySerializableDictType(KeySerializableDict),
            AutoPreserveReferences: AutoPreserveReferences(True),
            DetonateDanglingPreservedReferences: DetonateDanglingPreservedReferences(True),
            ResolvePreservedReferences: ResolvePreservedReferences(True),
            PreserveSerializableKeyOrdering: PreserveSerializableKeyOrdering(False),
            SerializeNoneVersionInfo: SerializeNoneVersionInfo(False)
        }

    def supports_semantic(self, semantic_class: Type[Semantic]) -> bool:
        return semantic_class in {
            AutoKeySerializableDictType,
            AutoPreserveReferences,
            DetonateDanglingPreservedReferences,
            ResolvePreservedReferences,
            PreserveSerializableKeyOrdering,
            SerializeNoneVersionInfo,
            NotifyFinalizedMethodName,
            DoNotAllowImportingModules,
            ClassStringPassFunction
        }

    def add_semantic(self, semantic: Semantic):
        add_semantic(semantic, self.semantics)

    def get_semantic(self, semantic_class: Type[T_S]) -> T_S | list[T_S] | None:
        if semantic_class in self.semantics:
            return self.semantics[semantic_class]

    def remove_semantic(self, semantic_class: Type[Semantic] | Semantic):
        remove_semantic_from_dict(semantic_class, self.semantics)

    def has_semantic(self, semantic_class: Type[Semantic] | Semantic) -> bool:
        if isinstance(semantic_class, Semantic):
            return self.get_semantic(semantic_class.__class__) == semantic_class
        else:
            return semantic_class in self.semantics

    def path_to_str(self):
        return self.settings.path_to_str(self.frame.key_path)

    def str_to_path(self, path_str: str):
        return self.settings.str_to_path(path_str)

    def check_in_object(self, obj: T) -> PreservedReference | T:
        object_id = id(obj)

        if object_id in self.id_cache:
            return PreservedReference(obj=obj, ref=self.id_cache[object_id])
        else:
            self.id_cache[object_id] = self.path_to_str()
            self.id_lifecycle_objects.append(obj)
            return obj

    def get_route_semantic(self, route: Route, t_semantic: Type[T_S]) -> T_S | list[T_S] | None:
        if (v := route.get_semantic(t_semantic)) is not None:
            return v
        else:
            return self.get_semantic(t_semantic)

    def is_circular_ref(self, path: list | str) -> bool:
        if type(path) is str:
            path = self.settings.str_to_path(path)
        if len(path) > len(self.frame.key_path):
            return False
        for pf, rp in zip(self.frame.key_path, path):
            if pf != rp:
                return False
        return True

    def get_part_from_path(self, obj: TYPES, path: list | str) -> TYPES:
        if type(path) is str:
            path = self.settings.str_to_path(path)
        for key in path:
            obj = obj[key]
        return obj

    def handle_serialize_list_in_place(self, instance: list, route: Route, **kwargs):
        for i in range(len(instance)):
            with self.frame(i):
                instance[i] = self._serialize(instance[i], route.branch(), **kwargs)
        return instance

    def handle_serialize_dict_in_place(self, instance: dict, route: Route, **kwargs):
        auto_key_serializable_dict = self.get_route_semantic(route, AutoKeySerializableDictType)
        if auto_key_serializable_dict and any(x.__class__ not in self.attribute for x in instance.keys()):
            ksd = auto_key_serializable_dict.val(instance)
            ksd_route = route.branch()
            ksd_route.add_frame_semantic(AutoPreserveReferences(False))
            return self._serialize(ksd, ksd_route, **kwargs)
        else:
            for k, v in instance.items():
                with self.frame(k):
                    instance[k] = self._serialize(v, route.branch(), **kwargs)
            return instance

    def handle_user_list(self, instance: list, nest, route: Route, **kwargs):
        p_ref = self.check_in_object(instance)
        if p_ref is not instance:
            route.add_semantic(AutoPreserveReferences(False))
            return self._serialize(p_ref, route, **kwargs)
        else:
            return self.handle_serialize_list_in_place(instance.copy(), route, **kwargs)

    def handle_user_dict(self, instance: dict, nest, route: Route, **kwargs):
        p_ref = self.check_in_object(instance)
        if p_ref is not instance:
            route.add_semantic(AutoPreserveReferences(False))
            return self._serialize(p_ref, route, **kwargs)
        else:
            return self.handle_serialize_dict_in_place(instance.copy(), route, **kwargs)

    def handle_temporary(self, instance: Temporary, nest, route: Route, **kwargs):
        tv = instance.val
        if type(tv) is list:
            return self.handle_serialize_list_in_place(tv, route, **kwargs)
        elif type(tv) is dict:
            return self.handle_serialize_dict_in_place(tv, route, **kwargs)
        else:
            route.add_frame_semantic(AutoPreserveReferences(False))
            return self._serialize(tv, route, **kwargs)

    def _serialize(self, obj: Any, route: Route, **kwargs) -> TYPES:
        tobj = obj.__class__
        if tobj in self.primitives:
            return obj
        else:
            if tobj in self.special:
                return self.serialization_handler.handle(tobj, route, instance=obj, **kwargs)
            else:
                if hasattr(obj, 'check_in_serialization_route'):
                    obj.check_in_serialization_route(route)
                auto_preserve_references = self.get_route_semantic(route, AutoPreserveReferences)
                if auto_preserve_references:
                    p_ref = self.check_in_object(obj)
                    if p_ref is not obj:
                        obj = p_ref  # serialize the preserved reference instead
                ro = {self.settings.class_id: None}  # keeps placement
                if isinstance(obj, VersionedSerializable):
                    version_info = obj.get_conversion_manager().get_version_object(obj)
                    if self.get_route_semantic(route, SerializeNoneVersionInfo) or version_info is not None:
                        version_info_route = route.branch()
                        version_info_route.add_semantic(AutoPreserveReferences(False))
                        ro[self.settings.version_id] = self._serialize(version_info, version_info_route)
                ser_obj = route.handler.handle(obj, route, **kwargs)
                ser_obj_route = route.branch()
                ro.update(self._serialize(ser_obj, ser_obj_route))
                ro[self.settings.class_id] = route.obj_type_str
                return ro

    def serialize(self, obj: Any, route: Route, **kwargs):
        self.root_object = obj
        route.formatter_settings = self.settings
        ret = self._serialize(obj, route, **kwargs)
        self.finalize(route)
        return ret

    def load_type(self, route: Route, class_str: str) -> Type:
        allow_imports = not bool(self.get_route_semantic(route, DoNotAllowImportingModules))
        validation = self.get_route_semantic(route, ClassStringPassFunction)
        if validation:
            for validation_call in validation:
                if not validation_call.val(class_str):
                    raise SecurityException()
        return load_type(class_str, do_import=allow_imports)

    def run_semantics_through_path(self, route: Route, key_path: list) -> Route:
        start = self.root_object
        for key in key_path:
            if type(start) == dict and self.settings.class_id in start:
                _class = self.load_type(route, start[self.settings.class_id])
                if hasattr(_class, 'check_in_deserialization_route'):
                    _class.check_in_deserialization_route(route)
                    route = route.branch()
            start = start[key]
        return route

    def handle_deserialize_list(self, instance: list, nest, route: Route, **kwargs):
        for i in range(len(instance)):
            cv = instance[i]
            with self.frame(i):
                instance[i] = cv if type(cv) in self.primitives else self._deserialize(cv, route.branch(), **kwargs)
        return instance

    def handle_deserialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        version_info = None
        class_id = None
        type_obj = None
        if self.settings.class_id in instance:
            class_id = instance.pop(self.settings.class_id)
            type_obj = self.load_type(route, class_id)
            if hasattr(type_obj, 'check_in_deserialization_route'):
                type_obj.check_in_deserialization_route(route)

            if self.settings.version_id in instance:
                version_obj = instance.pop(self.settings.version_id)
                version_info = self._deserialize(version_obj, route.branch())

        for k, v in instance.items():
            if type(v) in self.primitives:
                instance[k] = v
            else:
                with self.frame(k):
                    path_route = route.branch()
                    instance[k] = self._deserialize(v, path_route, **kwargs)

        if class_id is not None:
            if version_info is not None and hasattr(type_obj, 'get_conversion_manager'):
                conversion_manager = type_obj.get_conversion_manager()
                instance = conversion_manager.update_to_current(instance, version_info)

            ret = route.handler.handle(type_obj, instance, route, **kwargs)
            if method_name := route.get_semantic(NotifyFinalizedMethodName):
                route.finalize.subscribe(getattr(ret, method_name.val))
            return ret
        else:
            return instance

    def _deserialize(self, obj: TYPES, route: Route, **kwargs):
        tobj = type(obj)
        if tobj in self.primitives:
            return obj
        elif tobj in self.special:
            ro = self.deserialization_handler.handle(obj, route, **kwargs)
            key_path = None
            if isinstance(ro, PreservedReference):
                resolve_preserved = self.get_route_semantic(route, ResolvePreservedReferences)
                detonate = self.get_route_semantic(route, DetonateDanglingPreservedReferences)
                if (not resolve_preserved) or self.is_circular_ref((key_path := self.settings.str_to_path(ro.ref))):
                    if detonate:
                        self.preserved_refs.add(ro)
                else:
                    if ro.ref in self.id_cache:
                        return self.id_cache[ro.ref]
                    if key_path is None:
                        key_path = self.settings.str_to_path(ro.ref)
                    section_parent = self.get_part_from_path(self.root_object, key_path[:-1])
                    section_key = key_path[-1]
                    section = section_parent[section_key]

                    preserve_frame = self.frame
                    self.frame = FormatterFrame()
                    self.frame.key_path = key_path

                    route = route.branch()
                    route.clear_branch()
                    route = self.run_semantics_through_path(route, key_path[:-1])
                    ro = self._deserialize(section, route, **kwargs)

                    self.frame.update(preserve_frame)

                    npo = PreservedReference(obj=ro, ref=self.path_to_str())
                    self.id_cache[npo.ref] = ro
                    section_parent[section_key] = npo
                    if detonate:
                        self.preserved_refs.add(npo)
            else:
                self.id_cache[self.path_to_str()] = ro
            return ro
        elif isinstance(obj, PreservedReference):
            return obj.obj
        else:
            return obj

    def deserialize(self, obj: TYPES, route: Route, **kwargs):
        self.root_object = obj
        route.formatter_settings = self.settings
        ret = self._deserialize(obj, route, **kwargs)
        self.finalize(route)
        return ret

    def finalize(self, route: Route):
        route.finalize(self.id_cache)
        route.clear()
        self.id_lifecycle_objects.clear()
        self.frame = FormatterFrame()
        self.root_object = None
        self.id_cache = {}
        if len(self.preserved_refs) > 0:
            raise PreservedReferenceNotDissolvedError()
