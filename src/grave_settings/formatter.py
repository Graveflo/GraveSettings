# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import re
from functools import singledispatchmethod
from types import NoneType
from typing import Any, get_args, Union, Never, Type

from observer_hooks.block_events import BlockSideEffects
from ram_util.modules import format_class_str, load_type

from ram_util.utilities import MroHandler

from grave_settings import P_TYPE, P_ID, P_VERSION
from grave_settings.abstract import VersionedSerializable
from grave_settings.fmt_util import Route, KeySerializableDict, IFormatter, T_S, PreservedReference
from grave_settings.semantics import *

JSON_PRIMITIVES = int | float | str | bool | NoneType
JSON_TYPES = dict | list | JSON_PRIMITIVES

#
# def deserialize_object_json(state_object: JSON_TYPES, route: Route, **kwargs) -> Any:
#     with route:
#         if type(state_object) == dict:
#             if P_TYPE in state_object:
#                 ret = route.handler.handle(state_object, **kwargs)
#             else:
#                 objects_last = {}
#                 stateless_first = {}
#                 for k, v in state_object.items():
#                     if type(v) == dict and 'type' in v:
#                         objects_last[k] = v
#                     else:
#                         stateless_first[k] = v
#                 return_vec = {k: deserialize_object_json(v, **kwargs) for k, v in stateless_first.items()}
#                 ret = return_vec | {k: deserialize_object_json(v, **kwargs) for k, v in objects_last.items()}
#         else:
#             if type(state_object) == list:
#                 return [deserialize_object_json(x, **kwargs) for x in state_object]
#             else:
#                 return state_object
#


class FormatterSettings:
    def __init__(self, str_id=P_ID, version_id=P_VERSION, class_id=P_TYPE):
        self.str_id = str_id
        self.version_id = version_id
        self.class_id = class_id


class Formatter(IFormatter):
    PRIMITIVES = int | float | str | bool | NoneType
    SPECIAL = dict | list
    TYPES = PRIMITIVES | SPECIAL
    ATTRIBUTE_TYPES = Union[str, Never]
    ROUTE_PATH_TRANSLATION = str.maketrans({
        '\\': '\\\\',
        '.': r'\.',
        '"': r'\"'
    })
    ROUTE_PATH_REGEX = re.compile(r'(?:[^\."]|"(?:\\.|[^"])*")+')

    def __init__(self, settings: FormatterSettings = None):
        if settings is None:
            settings = FormatterSettings()
        self.settings = settings
        self.primitives = set(get_args(self.PRIMITIVES))
        self.special = set(get_args(self.SPECIAL))
        self.attribute = set(get_args(self.ATTRIBUTE_TYPES))
        self.serialization_handler = MroHandler()
        self.key_path = []
        self.id_cache = {}
        self.root_object = None
        self.serialization_handler.add_handlers_by_annotated_callable(
            self.handle_serialize_list,
            self.handle_serialize_dict
        )
        self.deserialization_handler = MroHandler()
        self.deserialization_handler.add_handlers_by_annotated_callable(
            self.handle_deserialize_list,
            self.handle_deserialize_dict
        )
        self.semantics: dict[Type[T_S], T_S] = {
            AutoKeySerializableDict: AutoKeySerializableDict(True),
            AutoPreserveReferences: AutoPreserveReferences(True),
            DetonateDanglingPreservedReferences: DetonateDanglingPreservedReferences(True),
            ResolvePreservedReferences: ResolvePreservedReferences(True)
        }

    def supports_symantec(self, semantic_class: Type[Semantic]) -> bool:
        return semantic_class in {
            AutoKeySerializableDict,
            AutoPreserveReferences
        }

    def register_symantec(self, symantec: Semantic):
        self.semantics[symantec.__class__] = symantec

    def get_semantic(self, semantic_class: Type[T_S]) -> T_S:
        return self.semantics[semantic_class]

    def convert_path_to_str(self) -> str:
        parts = (str(part) if type(part) == int else f'"{part.translate(self.ROUTE_PATH_TRANSLATION)}"'
                 for part in self.key_path)
        return '.'.join(parts)

    def convert_str_to_path(self, reference: str) -> list:
        return list(p[1:-1] if p.startswith('"') and p.endswith('"') else int(p)
                    for p in self.ROUTE_PATH_REGEX.findall(reference))

    def check_in_object(self, obj: T) -> PreservedReference | T:
        object_id = id(obj)
        if object_id in self.id_cache:
            return PreservedReference(obj=obj, ref=self.id_cache[object_id])
        else:
            self.id_cache[object_id] = self.convert_path_to_str()
            return obj

    def get_route_semantic(self, route: Route, t_semantic: Type[T_S]) -> T_S:
        if (v := route.get_semantic(t_semantic)) is not None:
            return v
        else:
            return self.get_semantic(t_semantic)

    def check_for_circular_reference(self, path: list | str) -> bool:
        if type(path) is str:
            path = self.convert_str_to_path(path)
        if len(path) > len(self.key_path):
            return False
        for pf, rp in zip(self.key_path, path):
            if pf != rp:
                return False
        return True

    def get_part_from_path(self, obj: TYPES, path: list | str) -> TYPES:
        if type(path) is str:
            path = self.convert_str_to_path(path)
        for key in path:
            obj = obj[key]
        return obj

    def handle_serialize_list(self, instance: list, nest, route: Route, **kwargs):
        lis: list[Any] = [None] * len(instance)  # Type hint is just to suppress annoying linting engine
        for i in range(len(instance)):
            self.key_path.append(i)
            lis[i] = self.serialize(instance[i], route.branch(), **kwargs)
            self.key_path.pop(-1)
        return lis

    def handle_serialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        auto_key_serializable_dict = self.get_route_semantic(route, AutoKeySerializableDict)
        if auto_key_serializable_dict and any(x.__class__ not in self.attribute for x in instance.keys()):
            ksd = KeySerializableDict(instance)
            return self.serialize(ksd, route.branch(), **kwargs)
        else:
            ret = {}
            for k, v in instance.items():
                self.key_path.append(k)
                ret[k] = self.serialize(v, route.branch(), **kwargs)
                self.key_path.pop(-1)
            return ret

    def serialize(self, obj: Any, route: Route, **kwargs) -> TYPES:
        if self.root_object is None:
            self.root_object = obj
            route.finalize.subscribe(self.finalize)
        with route:
            tobj = obj.__class__
            if tobj in self.primitives:
                return obj
            else:
                auto_preserve_references = self.get_route_semantic(route, AutoPreserveReferences)
                if auto_preserve_references:
                    obj = self.check_in_object(obj)
                    tobj = obj.__class__
                if tobj in self.special:
                    return self.serialization_handler.handle(tobj, route, instance=obj, **kwargs)
                else:
                    ro = {self.settings.class_id: format_class_str(tobj)}
                    if isinstance(obj, VersionedSerializable):
                        version_info = obj.get_conversion_manager().get_version_object(obj)
                        version_info_route = route.branch()
                        version_info_route.register_semantic(AutoPreserveReferences(False))
                        ro[self.settings.version_id] = self.serialize(version_info, version_info_route)
                    new_route = route.branch()
                    ro.update(self.serialize(route.handler.handle(obj, new_route, **kwargs), new_route))
                    return ro

    def handle_deserialize_list(self, instance: list, nest, route: Route, **kwargs):
        for i in range(len(instance)):
            cv = instance[i]
            self.key_path.append(i)
            instance[i] = cv if type(cv) in self.primitives else self.deserialize(cv, route.branch(), **kwargs)
            self.key_path.pop(-1)
        return instance

    def handle_deserialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        version_info = None
        class_id = None
        if self.settings.class_id in instance:
            class_id = instance.pop(self.settings.class_id)
            if self.settings.version_id in instance:
                version_obj = instance.pop(self.settings.version_id)
                version_info = self.deserialize(version_obj, route.branch())

        for k, v in instance.items():
            if type(v) in self.primitives:
                instance[k] = v
            else:
                self.key_path.append(k)
                path_route = route.branch()
                with BlockSideEffects(path_route.finalize_frame):  # finalization only happens after an object is made
                    instance[k] = self.deserialize(v, path_route, **kwargs)
                self.key_path.pop(-1)

        if class_id is not None:
            type_obj = load_type(class_id)
            if version_info is not None and hasattr(type_obj, 'get_conversion_manager'):
                conversion_manager = type_obj.get_conversion_manager()
                instance = conversion_manager.update_to_current(instance, version_info)

            if hasattr(type_obj, 'check_in_deserialization_route'):
                type_obj.check_in_deserialization_route(route)
            return route.handler.handle(type_obj, instance, route, **kwargs)
        else:
            return instance

    def deserialize(self, obj: TYPES, route: Route, **kwargs):
        if self.root_object is None:
            self.root_object = obj
            route.finalize.subscribe(self.finalize)
        with route:
            tobj = type(obj)
            if tobj in self.primitives:
                return obj
            elif tobj in self.special:
                ro = self.deserialization_handler.handle(obj, route, **kwargs)
                key_path = None
                if isinstance(ro, PreservedReference):
                    resolve_preserved = self.get_route_semantic(route, ResolvePreservedReferences)
                    detonate = self.get_route_semantic(route, DetonateDanglingPreservedReferences)
                    if (not resolve_preserved) or \
                        self.check_for_circular_reference((key_path := self.convert_str_to_path(ro.ref))):
                        if detonate:
                            route.finalize.subscribe(ro.detonate)
                    else:
                        if ro.ref in self.id_cache:
                            return self.id_cache[ro.ref]
                        if detonate:
                            route.finalize_frame.subscribe(ro.detonate)
                        if key_path is None:
                            key_path = self.convert_str_to_path(ro.ref)
                        section_parent = self.get_part_from_path(self.root_object, key_path[:-1])
                        section_key = key_path[-1]
                        section = section_parent[section_key]

                        preserve_key_path = self.key_path
                        self.key_path = key_path

                        # TODO: Whats missing here is the semantics from higher level objects since we skip them
                        route = route.branch()
                        ro = self.deserialize(section, route, **kwargs)
                        self.key_path = preserve_key_path
                        npo = PreservedReference(obj=ro, ref=self.convert_path_to_str())
                        self.id_cache[npo.ref] = ro
                        section_parent[section_key] = npo
                        if detonate:
                            route.finalize.subscribe(npo.detonate)
                else:
                    self.id_cache[self.convert_path_to_str()] = ro
                return ro
            elif isinstance(obj, PreservedReference):
                return obj.obj
            else:
                return obj

    def finalize(self, *args):
        self.key_path = []
        self.root_object = None
        self.id_cache = {}


class JsonFormatter(Formatter):
    pass
