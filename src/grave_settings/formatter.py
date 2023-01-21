# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import os
from abc import ABC, abstractmethod
from io import IOBase
from traceback import format_tb
from weakref import WeakSet

from observer_hooks import notify
from ram_util.modules import load_type, format_class_str

from grave_settings.framestack_context import FrameStackContext
from grave_settings.default_handlers import DeSerializationHandler, SerializationHandler
from grave_settings.handlers import OrderedHandler, OrderedMethodHandler
from grave_settings.helper_objects import PreservedReferenceNotDissolvedError, KeySerializableDict
from grave_settings.formatter_settings import FormatterSpec, Temporary, FormatterContext, PreservedReference, NoRef
from grave_settings.semantics import *


class ProcessingException(Exception):
    def __init__(self, processor, obj=None, wrapped_exception: Exception = None, key_stack=None,
                 frame_semantics: Semantics = None, semantics: Semantics = None):
        super().__init__()
        self.processor: Processor = processor
        self.obj = obj
        self.wrapped_exception = wrapped_exception
        self.mains_obj = None
        if len(key_stack) > 0:
            key_stack_value = key_stack[-1]
        else:
            key_stack_value = None
        self.key_stack_value = key_stack_value
        self.frame_semantics = frame_semantics
        self.semantics = semantics
        if type(self.wrapped_exception) is ProcessingException:
            self.mains_obj = self.wrapped_exception.mains_obj
            self.wrapped_exception.mains_obj = None
        else:
            self.mains_obj = wrapped_exception

    def __str__(self):
        encounterd = list(str(self.wrapped_exception).split('\n'))
        encounterd[0] = f'\t{encounterd[0]}'
        encounterd = '\n\t'.join(encounterd)
        sem_str = ''
        if self.semantics:
            sems = Semantics.__str__(self.semantics)
            sem_str += sems
        if self.frame_semantics:
            frame_sems = Semantics.__str__(self.frame_semantics)
            sem_str += f'\n{frame_sems}'
        return f'Processing Key({self.key_stack_value}): {repr(self.obj)}\n{sem_str}\n\tEncountered ({format_class_str(self.wrapped_exception.__class__)}): {encounterd}'


class Processor:
    def __init__(self, root_obj, spec: FormatterSpec, context: FormatterContext):
        self.spec = spec
        self.root_obj = root_obj
        self.context = context
        self.semantics = self.context.semantic_context
        self.primitives = spec.get_primitive_types()
        self.special = spec.get_special_types()
        self.attribute = spec.get_attribute_types()
        self.set_default_semantics()

    def set_default_semantics(self):
        pass

    def it_quack(self, t_obj: type):
        ducks = True
        if v := self.semantics[IgnoreDuckTypingForType]:
            ducks = t_obj not in v
        if not ducks and (v := self.semantics[IgnoreDuckTypingForSubclasses]):
            ducks = not any(issubclass(t_obj, t.val) for t in v)
        return ducks

    def process(self, obj, **kwargs):
        pass

    def path_to_str(self):
        return self.spec.path_to_str(self.context.key_path)

    def dispose(self):
        self.context.finalize()
        self.semantics.parent = None
        self.root_obj = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dispose()


class IFormatter(ABC):
    def to_buffer(self, data, _io: IOBase, encoding='utf-8', serializer: Processor = None):
        buffer = self.dumps(data, serializer=serializer)
        if encoding is not None and encoding != 'utf-8':
            buffer = buffer.encode(encoding)
        _io.write(buffer)

    def write_to_file(self, settings, path: str, encoding='utf-8', serializer: Processor = None):
        if encoding == 'utf-8':
            f = open(path, 'w')
        else:
            f = open(path, 'wb')
        with f:
            # noinspection PyTypeChecker
            self.to_buffer(settings, f, encoding=encoding, serializer=serializer)

    def from_buffer(self, _io: IOBase, encoding='utf-8', kwargs: dict | None = None, deserializer: Processor = None):
        data = _io.read()
        if encoding is not None and encoding != 'utf-8':
            data = data.decode(encoding)
        return self.loads(data, kwargs=kwargs, deserializer=deserializer)

    def read_from_file(self, path: str, encoding='utf-8', deserializer: Processor = None):
        if encoding == 'utf-8':
            f = open(path, 'r')
        else:
            f = open(path, 'rb')
        with f:
            # noinspection PyTypeChecker
            return self.from_buffer(f, encoding=encoding, deserializer=deserializer)

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

    def get_serialization_frame_context(self, handler: OrderedHandler = None) -> FrameStackContext:
        return FrameStackContext(self.get_serialization_handler(), Semantics())

    def get_deserialization_frame_context(self) -> FrameStackContext:
        return FrameStackContext(self.get_deserialization_handler(), Semantics())

    def get_serialization_context(self) -> FormatterContext:
        return FormatterContext(self.get_serialization_frame_context())

    def get_deserialization_context(self) -> FormatterContext:
        return FormatterContext(self.get_deserialization_frame_context())

    def dumps(self, obj: Any, kwargs: dict | None = None, serializer: Processor = None) -> str | bytes:
        return self.serialized_obj_to_buffer(self.serialize(obj, kwargs=kwargs, serializer=serializer))

    def loads(self, buffer, kwargs: dict | None = None, deserializer: Processor = None):
        return self.deserialize(self.buffer_to_obj(buffer), kwargs=kwargs, deserializer=deserializer)

    @abstractmethod
    def get_serializer(self, root_obj, context: FormatterContext) -> Processor:
        pass

    @abstractmethod
    def get_deserializer(self, root_obj, context: FormatterContext) -> Processor:
        pass

    def serialize(self, obj, kwargs: dict | None = None, serializer: Processor = None):
        if serializer is None:
            serializer = self.get_serializer(obj, self.get_serialization_context())
        with serializer:
            if kwargs:
                return serializer.process(obj, **kwargs)
            else:
                return serializer.process(obj)

    def deserialize(self, obj, kwargs: dict | None = None, deserializer: Processor = None):
        if deserializer is None:
            deserializer = self.get_deserializer(obj, self.get_deserialization_context())
        else:
            deserializer.root_obj = obj
        with deserializer:
            if kwargs:
                return deserializer.process(obj, **kwargs)
            else:
                return deserializer.process(obj)


class Serializer(Processor):
    def __init__(self, root_object, spec: FormatterSpec, context: FormatterContext):
        super().__init__(root_object, spec, context)
        self.root_object = root_object
        self.id_lifecycle_objects = []

        self.handler = OrderedMethodHandler()
        # noinspection PyTypeChecker
        self.handler.add_handlers_by_type_hints(
            self.handle_serialize_default,
            self.handle_noref,
            self.handle_temporary,
            self.handle_user_list,
            self.handle_user_dict
        )

    def set_default_semantics(self):
        self.semantics.add_semantics(AutoKeySerializableDictType(KeySerializableDict),
                                     AutoPreserveReferences(True),
                                     PreserveSerializableKeyOrdering(False),
                                     SerializeNoneVersionInfo(False),
                                     EnforceReferenceLifecycle(True))

    def supports_semantic(self, semantic_class: Type[Semantic]) -> bool:
        return semantic_class in {
            AutoKeySerializableDictType,
            AutoPreserveReferences,
            PreserveSerializableKeyOrdering,
            SerializeNoneVersionInfo,
            EnforceReferenceLifecycle,
            KeySemanticsTemplate,
            OverrideClassString,
            IgnoreDuckTypingForType,
            IgnoreDuckTypingForSubclasses,
            OmitMe
        }

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
            rems = []
            if not auto_key_semantics:
                auto_key_semantics = False
            for k, v in instance.items():
                with self.context(k), self.semantics:
                    if auto_key_semantics:
                        if k in auto_key_semantics.val:
                            tuple(map(self.context.add_frame_semantic, auto_key_semantics.val[k]))
                    try:
                        instance[k] = self.serialize(v, **kwargs)
                    except OmitMeError:
                        rems.append(k)
            for rem in rems:
                instance.pop(rem)
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

    def template_object_serialize(self, template_dict: dict, instance, **kwargs):
        ser_obj = self.context.handler.handle(instance, self.context, **kwargs)
        with self.semantics:
            template_dict.update(self.serialize(ser_obj, **kwargs))
        if ocs := self.semantics[OverrideClassString]:
            class_str = ocs.val
        else:
            class_str = format_class_str(instance.__class__)
        template_dict[self.spec.class_id] = class_str
        return template_dict

    def handle_serialize_default(self, instance: object, **kwargs):
        ducks = self.it_quack(instance.__class__)
        if ducks and hasattr(instance, 'check_in_serialization_context'):
            instance.check_in_serialization_context(self.context)
        auto_preserve_references = self.semantics[AutoPreserveReferences]
        if auto_preserve_references:
            p_ref = self.check_in_object(instance)
            if p_ref is not instance:
                instance = p_ref  # serialize the preserved reference instead
        ro = {self.spec.class_id: None}  # keeps placement
        if ducks and hasattr(instance, 'get_version_object'):
            version_info = instance.get_version_object()
            if self.semantics[SerializeNoneVersionInfo] or version_info is not None:
                with self.semantics:
                    self.context.add_semantic(AutoPreserveReferences(False))
                    ro[self.spec.version_id] = self.serialize(version_info)
        return self.template_object_serialize(ro, instance, **kwargs)

    def process(self, obj, **kwargs):
        return self.serialize(obj, **kwargs)

    def serialize(self, obj: Any, **kwargs):
        try:
            tobj = obj.__class__
            if tobj in self.primitives:
                return obj
            else:
                return self.handler.handle(self, obj, **kwargs)
        except ProcessingException as e:
                esp = e.mains_obj
                raise ProcessingException(self, obj=obj, wrapped_exception=e, key_stack=self.context.key_path,
                                          semantics=self.context.semantic_context,
                                          frame_semantics=self.context.semantic_context.parent) from esp  # these stack recursively
        except Exception as e:
            raise ProcessingException(self, obj=obj, wrapped_exception=e, key_stack=self.context.key_path,
                                      semantics=self.context.semantic_context,
                                      frame_semantics=self.context.semantic_context.parent)

    def dispose(self):
        super().dispose()
        self.id_lifecycle_objects = []


class DeSerializer(Processor):
    def __init__(self, root_object, spec: FormatterSpec, context: FormatterContext):
        super().__init__(root_object, spec, context)
        self.root_object = root_object
        self.preserved_refs = WeakSet()

        self.handler = OrderedMethodHandler()
        # noinspection PyTypeChecker
        self.handler.add_handlers_by_type_hints(
            self.handle_deserialize_list,
            self.handle_deserialize_dict,
            self.handle_deserialize_preserved_referece
        )
        self.secondary_handler = OrderedMethodHandler()
        # noinspection PyTypeChecker
        self.secondary_handler.add_handlers_by_type_hints(
            self.cache_instance_ref,
            self.handle_secondary_preserved_reference
        )

    def set_default_semantics(self):
        self.semantics.add_semantics(DetonateDanglingPreservedReferences(True),
                                     ResolvePreservedReferences(True))

    def load_type(self, class_str: str) -> Type:
        allow_imports = not bool(self.semantics[DoNotAllowImportingModules])
        validation = self.semantics[ClassStringPassFunction]
        if validation:
            for validation_call in validation:
                if not validation_call.val(class_str):
                    raise SecurityException()
        return load_type(class_str, do_import=allow_imports)

    def supports_semantic(self, semantic_class: Type[Semantic]) -> bool:
        return semantic_class in {
            DetonateDanglingPreservedReferences,
            ResolvePreservedReferences,
            NotifyFinalizedMethodName,
            DoNotAllowImportingModules,
            ClassStringPassFunction,
            KeySemanticsTemplate,
            IgnoreDuckTypingForType,
            IgnoreDuckTypingForSubclasses
        }

    def run_semantics_through_path(self, key_path: list) -> Semantics:
        start = self.root_object
        save_semantic_contex = self.context.semantic_context
        self.context.key_path.clear()
        semantics = Semantics()
        self.context.semantic_context = semantics
        for key in key_path:
            if type(start) == dict and self.spec.class_id in start:
                _class = self.load_type(start[self.spec.class_id])  # NOTE: This is why we use check for semantics
                if self.it_quack(_class) and hasattr(_class, 'check_in_deserialization_context'):
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
        ducks = True
        version_info = None
        class_id = None
        type_obj = None
        if self.spec.class_id in instance:
            class_id = instance.pop(self.spec.class_id)
            type_obj = self.load_type(class_id)
            ducks = self.it_quack(type_obj)
            if ducks and hasattr(type_obj, 'check_in_deserialization_context'):
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
            if ducks and (version_info is not None) and hasattr(type_obj, 'check_convert_update'):
                if ti := type_obj.check_convert_update(instance, self.load_type, version_info):
                    instance = ti
                    self.notify_settings_converted(class_id)
            ret = self.context.handler.handle_node(type_obj, instance, self.context, **kwargs)
            if method_name := self.semantics[NotifyFinalizedMethodName]:
                self.context.finalize.subscribe(getattr(ret, method_name.val))
            return ret
        else:
            return instance

    def handle_deserialize_preserved_referece(self, instance: PreservedReference, **kwargs):
        return instance.obj

    def handle_deserialize_default(self, instance: object, **kwargs):
        return instance

    def handle_secondary_preserved_reference(self, instance: PreservedReference, **kwargs):
        key_path = None  # Dont delete this

        resolve_preserved = self.semantics[ResolvePreservedReferences]
        detonate = self.semantics[DetonateDanglingPreservedReferences]
        if (not resolve_preserved) or self.spec.is_circular_ref((key_path := self.spec.str_to_path(instance.ref)),
                                                                self.context.key_path):
            if detonate:
                self.preserved_refs.add(instance)
            return instance
        else:
            if v := self.context.check_ref(instance):
                return v
            if key_path is None:
                key_path = self.spec.str_to_path(instance.ref)
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
            return ro

    def cache_instance_ref(self, instance: object, **kwargs):
        self.context.id_cache[self.path_to_str()] = instance
        return instance

    def process(self, obj, **kwargs):
        return self.deserialize(obj, **kwargs)

    def deserialize(self, obj, **kwargs):
        try:
            tobj = type(obj)
            if tobj in self.primitives:
                return obj
            else:
                ro = self.handler.handle(self, obj, **kwargs)
                return self.secondary_handler.handle(self, ro, **kwargs)
        except ProcessingException as e:
            esp = e.mains_obj
            raise ProcessingException(self, obj=obj, wrapped_exception=e, key_stack=self.context.key_path,
                                      semantics=self.context.semantic_context,
                                      frame_semantics=self.context.semantic_context.parent) from esp  # these stack recursively
        except Exception as e:
            raise ProcessingException(self, obj=obj, wrapped_exception=e, key_stack=self.context.key_path,
                                      semantics=self.context.semantic_context,
                                      frame_semantics=self.context.semantic_context.parent)

    def dispose(self):
        super().dispose()
        if len(self.preserved_refs) > 0:
            raise PreservedReferenceNotDissolvedError()

    @notify(pass_ref=True, no_origin=True)
    def notify_settings_converted(self, class_type: Type):
        pass


class Formatter(IFormatter, ABC):
    FORMAT_SETTINGS = FormatterSpec()
    TYPES = FORMAT_SETTINGS.type_primitives | FORMAT_SETTINGS.type_special

    def __init__(self, spec: FormatterSpec = None):
        if spec is None:
            spec = self.FORMAT_SETTINGS.copy()
        self.spec = spec
        self.semantics = Semantics()
        self.serialization_handler = SerializationHandler()
        self.deserializer_handler = DeSerializationHandler()

    def get_serialization_handler(self) -> OrderedHandler:
        return self.serialization_handler

    def get_deserialization_handler(self) -> OrderedHandler:
        return self.deserializer_handler

    def get_serializer(self, root_obj, context) -> Serializer:
        s =  Serializer(root_obj, self.spec.copy(), context)
        s.semantics.update(self.semantics)
        return s

    def get_deserializer(self, root_obj, context) -> DeSerializer:
        d = DeSerializer(root_obj, self.spec.copy(), context)
        d.semantics.update(self.semantics)
        return d
