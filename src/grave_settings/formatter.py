# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import ABC, abstractmethod
from io import IOBase
from weakref import WeakSet

from ram_util.modules import load_type, format_class_str

from grave_settings.abstract import VersionedSerializable
from grave_settings.framestackcontext import FrameStackContext
from grave_settings.default_handlers import DeSerializationHandler, SerializationHandler
from grave_settings.handlers import OrderedHandler
from grave_settings.helper_objects import PreservedReferenceNotDissolvedError, KeySerializableDict
from grave_settings.formatter_settings import FormatterSpec, Temporary, FormatterContext, PreservedReference, NoRef
from grave_settings.semantics import *


class IFormatter(ABC):
    def to_buffer(self, data, _io: IOBase, encoding='utf-8'):
        buffer = self.dumps(data)
        if encoding is not None and encoding != 'utf-8':
            buffer = buffer.encode(encoding)
        _io.write(buffer)

    def write_to_file(self, settings, path: str, encoding='utf-8'):
        if encoding == 'utf-8':
            f = open(path, 'w')
        else:
            f = open(path, 'wb')
        with f:
            # noinspection PyTypeChecker
            self.to_buffer(settings, f, encoding=encoding)

    def from_buffer(self, _io: IOBase, encoding='utf-8'):
        data = _io.read()
        if encoding is not None and encoding != 'utf-8':
            data = data.decode(encoding)
        return self.loads(data)

    def read_from_file(self, path: str, encoding='utf-8'):
        if encoding == 'utf-8':
            f = open(path, 'r')
        else:
            f = open(path, 'rb')
        with f:
            # noinspection PyTypeChecker
            return self.from_buffer(f, encoding=encoding)

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

    def get_serialization_frame_context(self) -> FrameStackContext:
        return FrameStackContext(self.get_serialization_handler(), Semantics())

    def get_deserialization_frame_context(self) -> FrameStackContext:
        return FrameStackContext(self.get_deserialization_handler(), Semantics())

    def get_serialization_context(self) -> FormatterContext:
        return FormatterContext(self.get_serialization_frame_context())

    def get_deserialization_context(self) -> FormatterContext:
        return FormatterContext(self.get_deserialization_frame_context())

    def dumps(self, obj: Any) -> str | bytes:
        return self.serialized_obj_to_buffer(self.serialize(obj))

    def loads(self, buffer):
        return self.deserialize(self.buffer_to_obj(buffer))

    @abstractmethod
    def serialize(self, obj: Any, **kwargs):
        pass

    @abstractmethod
    def deserialize(self, obj, **kwargs):
        pass

    @abstractmethod
    def supports_semantic(self, semantic_class: Type[Semantic]) -> bool:
        pass


class Processor:
    def __init__(self, root_obj, spec: FormatterSpec, context: FormatterContext):
        self.spec = spec
        self.root_obj = root_obj
        self.context = context
        self.semantics = self.context.semantic_context
        self.primitives = spec.get_primitive_types()
        self.special = spec.get_special_types()
        self.attribute = spec.get_attribute_types()

    def path_to_str(self):
        return self.spec.path_to_str(self.context.key_path)

    def dispose(self):
        self.context.finalize()
        self.semantics.parent = None
        self.semantics = None
        self.root_obj = None
        self.context = None


class Serializer(Processor):
    def __init__(self, root_object, spec: FormatterSpec, context: FormatterContext):
        super().__init__(root_object, spec, context)
        self.root_object = root_object
        self.id_lifecycle_objects = []

        self.handler = OrderedHandler()
        self.handler.add_handlers_by_annotated_callable(
            self.handle_serialize_default,
            self.handle_user_list,
            self.handle_user_dict
        )

    def check_in_object(self, obj: T) -> PreservedReference | T:
        object_id = id(obj)
        id_cache = self.context.id_cache
        if object_id in id_cache:
            return PreservedReference(obj=obj, ref=id_cache[object_id])
        else:
            id_cache[object_id] = self.path_to_str()
            if self.semantics[EnforceReferenceLifecycle]:
                self.id_lifecycle_objects.append(obj)
            return obj

    def handle_serialize_list_in_place(self, instance: list, **kwargs):
        for i in range(len(instance)):
            with self.context(i), self.semantics:
                instance[i] = self.serialize(instance[i], **kwargs)
        return instance

    def handle_serialize_dict_in_place(self, instance: dict, **kwargs):
        auto_key_serializable_dict = self.semantics[AutoKeySerializableDictType]
        if auto_key_serializable_dict and any(x.__class__ not in self.attribute for x in instance.keys()):
            ksd = auto_key_serializable_dict.val(instance)
            with self.semantics:
                self.context.add_frame_semantic(AutoPreserveReferences(False))
                return self.serialize(ksd, **kwargs)
        else:
            auto_key_semantics = self.semantics[KeySemanticsTemplate]
            if not auto_key_semantics:
                auto_key_semantics = False
            for k, v in instance.items():
                with self.context(k), self.semantics:
                    if auto_key_semantics:
                        if k in auto_key_semantics.val:
                            tuple(map(self.context.add_frame_semantic, auto_key_semantics.val[k]))
                    instance[k] = self.serialize(v, **kwargs)
            return instance

    def handle_user_list(self, instance: list, **kwargs):
        p_ref = self.check_in_object(instance)
        if p_ref is not instance:
            self.context.add_semantic(AutoPreserveReferences(False))
            return self.serialize(p_ref, **kwargs)
        else:
            return self.handle_serialize_list_in_place(instance.copy(), **kwargs)

    def handle_user_dict(self, instance: dict, **kwargs):
        p_ref = self.check_in_object(instance)
        if p_ref is not instance:
            self.context.add_semantic(AutoPreserveReferences(False))
            return self.serialize(p_ref, **kwargs)
        else:
            return self.handle_serialize_dict_in_place(instance.copy(), **kwargs)

    def handle_noref(self, instance: NoRef, **kwargs):
        tv = instance.val
        self.context.add_frame_semantic(AutoPreserveReferences(False))
        return self.serialize(tv, **kwargs)

    def handle_temporary(self, instance: Temporary, **kwargs):
        tv = instance.val
        if type(tv) is list:
            return self.handle_serialize_list_in_place(tv, **kwargs)
        elif type(tv) is dict:
            return self.handle_serialize_dict_in_place(tv, **kwargs)
        else:
            self.context.add_frame_semantic(AutoPreserveReferences(False))
            return self.serialize(tv, **kwargs)

    def handle_serialize_default(self, instance: Any, **kwargs):
        if hasattr(instance, 'check_in_serialization_context'):
            instance.check_in_serialization_context(self.context)
        auto_preserve_references = self.semantics[AutoPreserveReferences]
        if auto_preserve_references:
            p_ref = self.check_in_object(instance)
            if p_ref is not instance:
                instance = p_ref  # serialize the preserved reference instead
        ro = {self.spec.class_id: None}  # keeps placement
        if isinstance(instance, VersionedSerializable):
            version_info = instance.get_conversion_manager().get_version_object(instance)
            if self.semantics[SerializeNoneVersionInfo] or version_info is not None:
                with self.semantics:
                    self.context.add_semantic(AutoPreserveReferences(False))
                    ro[self.spec.version_id] = self.serialize(version_info)
        ser_obj = self.context.handler.handle(instance, self.context, **kwargs)
        with self.semantics:
            ro.update(self.serialize(ser_obj))
        if ocs := self.semantics[OverrideClassString]:
            class_str = ocs.val
        else:
            class_str = format_class_str(instance.__class__)
        ro[self.spec.class_id] = class_str
        return ro

    def serialize(self, obj: Any, **kwargs):
        tobj = obj.__class__
        if tobj in self.primitives:
            return obj
        else:
            if tobj in self.special:
                return self.handler.handle(obj, **kwargs)
            elif issubclass(tobj, Temporary):
                return self.handle_temporary(obj, **kwargs)
            elif issubclass(tobj, NoRef):
                return self.handle_noref(obj, **kwargs)
            else:
                return self.handle_serialize_default(obj, **kwargs)

    def dispose(self):
        super().dispose()
        self.handler = None
        self.id_lifecycle_objects = None


class DeSerializer(Processor):
    def __init__(self, root_object, spec: FormatterSpec, context: FormatterContext):
        super().__init__(root_object, spec, context)
        self.root_object = root_object
        self.preserved_refs = WeakSet()

        self.handler = OrderedHandler()
        self.handler.add_handlers_by_annotated_callable(
            self.handle_deserialize_list,
            self.handle_deserialize_dict
        )

    def load_type(self, class_str: str) -> Type:
        allow_imports = not bool(self.semantics[DoNotAllowImportingModules])
        validation = self.semantics[ClassStringPassFunction]
        if validation:
            for validation_call in validation:
                if not validation_call.val(class_str):
                    raise SecurityException()
        return load_type(class_str, do_import=allow_imports)

    def run_semantics_through_path(self, key_path: list) -> Semantics:
        start = self.root_object
        save_semantic_contex = self.context.semantic_context
        self.context.key_path.clear()
        semantics = Semantics()
        self.context.semantic_context = semantics
        for key in key_path:
            if type(start) == dict and self.spec.class_id in start:
                _class = self.load_type(start[self.spec.class_id])
                if hasattr(_class, 'check_in_deserialization_context'):
                    _class.check_in_deserialization_context(self.context)
            start = start[key]
        self.context.semantic_context = save_semantic_contex
        return semantics

    def handle_deserialize_list(self, instance: list, **kwargs):
        for i in range(len(instance)):
            cv = instance[i]
            with self.context(i), self.semantics:
                instance[i] = cv if type(cv) in self.primitives else self.deserialize(cv, **kwargs)
        return instance

    def handle_deserialize_dict(self, instance: dict, **kwargs):
        version_info = None
        class_id = None
        type_obj = None
        if self.spec.class_id in instance:
            class_id = instance.pop(self.spec.class_id)
            type_obj = self.load_type(class_id)
            if hasattr(type_obj, 'check_in_deserialization_context'):
                type_obj.check_in_deserialization_context(self.context)

            if self.spec.version_id in instance:
                version_obj = instance.pop(self.spec.version_id)
                with self.semantics:
                    version_info = self.deserialize(version_obj)

        for k, v in instance.items():
            if type(v) in self.primitives:
                instance[k] = v
            else:
                with self.context(k), self.semantics:
                    instance[k] = self.deserialize(v, **kwargs)

        if class_id is not None:
            if version_info is not None and hasattr(type_obj, 'get_conversion_manager'):
                conversion_manager = type_obj.get_conversion_manager()
                instance = conversion_manager.update_to_current(instance, version_info)

            ret = self.context.handler.handle(type_obj, instance, self.context, **kwargs)
            if method_name := self.semantics[NotifyFinalizedMethodName]:
                self.context.finalize.subscribe(getattr(ret, method_name.val))
            return ret
        else:
            return instance

    def deserialize(self, obj, **kwargs):
        tobj = type(obj)
        if tobj in self.primitives:
            return obj
        elif tobj in self.special:
            ro = self.handler.handle(obj, **kwargs)
            key_path = None
            if isinstance(ro, PreservedReference):
                resolve_preserved = self.semantics[ResolvePreservedReferences]
                detonate = self.semantics[DetonateDanglingPreservedReferences]
                if (not resolve_preserved) or self.spec.is_circular_ref((key_path := self.spec.str_to_path(ro.ref)),
                                                                        self.context.key_path):
                    if detonate:
                        self.preserved_refs.add(ro)
                else:
                    if v := self.context.check_ref(ro):
                        return v
                    if key_path is None:
                        key_path = self.spec.str_to_path(ro.ref)
                    section_parent = self.spec.get_part_from_path(self.root_object, key_path[:-1])
                    section_key = key_path[-1]
                    section = section_parent[section_key]

                    preserve_key_path = self.context.key_path
                    self.context.key_path = key_path

                    semantics = self.run_semantics_through_path(key_path[:-1])
                    with self.context(section_key), self.semantics:
                        self.semantics.update(semantics)
                        ro = self.deserialize(section, **kwargs)

                    self.context.key_path = preserve_key_path

                    npo = PreservedReference(obj=ro, ref=self.path_to_str())
                    self.context.id_cache[npo.ref] = ro
                    section_parent[section_key] = npo
                    if detonate:
                        self.preserved_refs.add(npo)
            else:
                self.context.id_cache[self.path_to_str()] = ro
            return ro
        elif isinstance(obj, PreservedReference):
            return obj.obj
        else:
            return obj

    def dispose(self):
        super().dispose()
        self.handler = None
        if len(self.preserved_refs) > 0:
            raise PreservedReferenceNotDissolvedError()


class Formatter(IFormatter, ABC):
    FORMAT_SETTINGS = FormatterSpec()
    TYPES = FORMAT_SETTINGS.type_primitives | FORMAT_SETTINGS.type_special

    def __init__(self, spec: FormatterSpec = None):
        if spec is None:
            spec = self.FORMAT_SETTINGS.copy()
        self.spec = spec
        self.semantics = Semantics(semantics={
            AutoKeySerializableDictType: AutoKeySerializableDictType(KeySerializableDict),
            AutoPreserveReferences: AutoPreserveReferences(True),
            DetonateDanglingPreservedReferences: DetonateDanglingPreservedReferences(True),
            ResolvePreservedReferences: ResolvePreservedReferences(True),
            PreserveSerializableKeyOrdering: PreserveSerializableKeyOrdering(False),
            SerializeNoneVersionInfo: SerializeNoneVersionInfo(False),
            EnforceReferenceLifecycle: EnforceReferenceLifecycle(True)
        })

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
            ClassStringPassFunction,
            EnforceReferenceLifecycle,
            KeySemanticsTemplate,
            OverrideClassString
        }

    def get_serializer(self, root_obj, context) -> Serializer:
        return Serializer(root_obj, self.spec.copy(), context)

    def serialize(self, obj: Any, **kwargs):
        context = self.get_serialization_context()
        context.semantic_context.update(self.semantics)
        serializer = self.get_serializer(obj, context)
        ret = serializer.serialize(obj, **kwargs)
        serializer.dispose()
        return ret

    def get_deserializer(self, root_obj, context) -> DeSerializer:
        return DeSerializer(root_obj, self.spec.copy(), context)

    def deserialize(self, obj: TYPES, **kwargs):
        context = self.get_deserialization_context()
        context.semantic_context.update(self.semantics)
        deserializer = self.get_deserializer(obj, context)
        ret = deserializer.deserialize(obj, **kwargs)
        deserializer.dispose()
        return ret
