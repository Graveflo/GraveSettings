# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
import re
from functools import singledispatchmethod
from types import NoneType
from typing import Any, get_args, Union, Never, Type

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

    def convert_route_to_reference_string(self, route: Route) -> str:
        parts = (str(part) if type(part) == int else f'"{part.translate(self.ROUTE_PATH_TRANSLATION)}"'
                 for part in route.key_path)
        return '.'.join(parts)

    def convert_reference_to_route_path(self, reference: str) -> list:
        return list(p[1:-1] if p.startswith('"') and p.endswith('"') else int(p)
                    for p in self.ROUTE_PATH_REGEX.findall(reference))

    def __init__(self, settings: FormatterSettings = None):
        if settings is None:
            settings = FormatterSettings()
        self.settings = settings
        self.primitives = set(get_args(self.PRIMITIVES))
        self.special = set(get_args(self.SPECIAL))
        self.attribute = set(get_args(self.ATTRIBUTE_TYPES))
        self.serialization_handler = MroHandler()
        self.serialization_handler.add_handlers_by_annotated_callable(
            self.handle_serialize_list,
            self.handle_serialize_dict
        )
        self.deserialization_handler = MroHandler()
        self.deserialization_handler.add_handlers_by_annotated_callable(
            self.handle_serialize_list,
            self.handle_deserialize_dict
        )
        self.semantics: dict[Type[T_S], T_S] = {
            AutoKeySerializableDict: AutoKeySerializableDict(True),
            AutoPreserveReferences: AutoPreserveReferences(True),
            DetonateDanglingPreservedReferences: DetonateDanglingPreservedReferences(True)
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

    def get_route_semantic(self, route: Route, t_semantic: Type[T_S]) -> T_S:
        if (v := route.get_semantic(t_semantic)) is not None:
            return v
        else:
            return self.get_semantic(t_semantic)

    def handle_serialize_list(self, instance: list, nest, route: Route, **kwargs):
        return [self.serialize(x[1], route.branch(path=str(x[0])), **kwargs) for x in enumerate(instance)]

    def handle_serialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        auto_key_serializable_dict = self.get_route_semantic(route, AutoKeySerializableDict)
        if auto_key_serializable_dict and any(x.__class__ not in self.attribute for x in instance.keys()):
            return route.handler.handle(KeySerializableDict(instance), route)
        else:
            return dict((k, self.serialize(v, route.branch(path=k), **kwargs)) for k, v in instance.items())

    def serialize(self, obj: Any, route: Route, **kwargs) -> TYPES:
        # when we call serialize we call branch on the route object
        with route:
            tobj = obj.__class__
            if tobj in self.primitives:
                return obj
            else:
                auto_preserve_references = self.get_route_semantic(route, AutoPreserveReferences)
                if auto_preserve_references:
                    obj = route.check_in_object(obj, self.convert_route_to_reference_string)
                    tobj = obj.__class__
                if tobj in self.special:
                    return self.serialization_handler.handle(tobj, route, instance=obj, **kwargs)
                else:
                    new_route = route.branch(obj=obj)
                    ro = self.serialize(route.handler.handle(obj, new_route, **kwargs), new_route)
                    ro[self.settings.class_id] = format_class_str(tobj)
                    if isinstance(obj, VersionedSerializable):
                        version_info = obj.get_version()
                        version_info_route = route.branch(obj=version_info)
                        version_info_route.register_semantic(AutoPreserveReferences(False))
                        ro[self.settings.version_id] = self.serialize(version_info, version_info_route)
                    return ro

    def handle_deserialize_list(self, instance: list, nest, route: Route, **kwargs):
        return [x if type(x) in self.primitives else self.deserialize(x, route.branch(path=i), **kwargs)
                for i, x in enumerate(instance)]

    def check_for_circular_reference(self, route: Route, path_str: str) -> bool:
        ref_path = self.convert_reference_to_route_path(path_str)
        if len(ref_path) > len(route.key_path):
            return False
        for pf, rp in zip(route.key_path, ref_path):
            if pf != rp:
                return False
        return True

    @singledispatchmethod
    def get_part_from_path(self, obj: TYPES, keys: list) -> TYPES:
        for key in keys:
            obj = obj[key]
        return obj

    @get_part_from_path.register
    def get_part_from_path(self, obj: TYPES, path_str: str) -> TYPES:
        keys = self.convert_reference_to_route_path(path_str)
        return self.get_part_from_path(obj, keys)

    def handle_deserialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        version_info = None
        class_id = None
        if self.settings.class_id in instance:
            class_id = instance.pop(self.settings.class_id)
            if self.settings.version_id:
                version_obj = instance.pop(self.settings.version_id)
                version_info = self.deserialize(version_obj, route.branch(obj=version_obj))
        primitives = {}
        objects = {}
        for k, v in instance.items():
            if type(v) in self.primitives:
                primitives[k] = v
            else:
                objects[k] = v
        del instance
        objects = {k: self.deserialize(v, route.branch(path=k), **kwargs) for k, v in objects.items()}
        objects.update(primitives)
        if class_id is not None:
            type_obj = load_type(class_id)
            if version_info is not None and hasattr(type_obj, 'get_conversion_manager'):
                conversion_manager = type_obj.get_conversion_manager()
                objects = conversion_manager.update_to_current(objects, version_info)

            if hasattr(type_obj, 'check_in_deserialization_route'):
                type_obj.check_in_deserialization_route(route)
            return route.handler.handle(class_id, objects, route.branch(obj=objects))
        else:
            return objects

    def deserialize(self, obj: TYPES, route: Route, **kwargs):
        with route:
            tobj = type(obj)
            if tobj in self.primitives:
                return obj
            elif tobj in self.special:
                ro = self.deserialization_handler.handle(obj, route, **kwargs)
                if isinstance(ro, PreservedReference):
                    resolve_preserved = self.get_route_semantic(route, ResolvePreservedReferences)
                    detonate = self.get_route_semantic(route, DetonateDanglingPreservedReferences)
                    if (not resolve_preserved) or self.check_for_circular_reference(route, ro.ref):
                        if detonate:
                            route.finalize.subscribe(ro.detonate)
                    else:
                        if detonate:
                            route.finalize_frame.subscribe(ro.detonate)
                        key_path = self.convert_reference_to_route_path(ro.ref)
                        section_parent = self.get_part_from_path(obj, key_path[:-1])
                        section_key = key_path[-1]
                        section = section_parent[section_key]
                        # TODO: Whats missing here is the semantics from higher level objects since we skip them
                        route = route.branch_skip(key_path, obj=section)
                        roi = self.deserialize(section, route)
                        section_parent[section_key] = PreservedReference(obj=roi, ref=ro.ref)
                        ro = roi
                return ro
            elif isinstance(obj, PreservedReference):
                return obj.obj
            else:
                raise ValueError(f'First-pass deserialization created unhandled type: {tobj}')
    

class JsonFormatter(Formatter):
    pass
