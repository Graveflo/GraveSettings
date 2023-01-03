# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from abc import abstractmethod, ABC
from io import IOBase
from types import NoneType
from typing import Any, get_args, Union, Never

from ram_util.modules import format_class_str

from ram_util.utilities import OrderedMroHandler

from grave_settings import P_TYPE, P_ID, P_VERSION
from grave_settings.abstract import IASettings, VersionedSerializable
from grave_settings.fmt_util import Route, KeySerializableDict

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


def proto_serialize(obj: Any, route: Route, **kwargs):
    with route:
        tobj = type(obj)


class SymantecNotSupportedError(Exception):
    pass


class SymantecConfigurationInvalid(Exception):
    pass


class Symantec:
    pass


class PreserveDictionaryOrdering(Symantec):
    '''
    Keep the ordering of dictionary objects consistent between the format and the python object hierarchy
    '''
    pass


class AutoKeySerializableDict(Symantec):
    '''
    Automatically scan dictionary objects to ensure their keys are serializable as native format keys. If not they
    are converted to KeySerializableDict objects (represented as an array of tuples (key, value))
    '''
    pass


class Indentation(Symantec):
    '''
    Specified indentation formatting if applicable
    '''
    def __init__(self, val: int):
        self.val = val


class Mulitwrite(Symantec):
    '''
    This will write/ read the config file in chunks, lines or sub sections in order to preserve memory. Otherwise the
    formatter may serialize or deserialize the entire object tree in one go.
    '''
    pass


class AutoPreserveReferences(Symantec):
    '''
    The formatter will keep track of objects that are referenced more than once in the object hierarchy and automatically
    convert subsequent instanced of the same object to a PreservedReference
    '''
    pass

class DetonateDanglingPreservedReferences(Symantec):
    '''
    This will call a method that raises an exception if any tracked PreservedReference has not been flagged for garbage
    collection at the end of the deserialization process. It can be used to test if all the PreservedReference objects
    have been replaced by their correct reference since they should all be de-referenced by the end of the process.
    '''
    pass


class PreScanPreservedReferences(Symantec):
    '''
    Load the entire object tree before scanning for preserved references. This is a method of deserialization that
    avoids temporarily assigning PreservedReference objects to live objects
    '''
    pass


class ResolvePreservedReferences(Symantec):
    '''
    Preserved References are resolved by the formatter and never given to the object. This may be slower. but
    it ensures that the object will never have a property set that is of type PreservedReference. When this is not
    present the formatter should not resolve the preserved references. Objects can resolve them by subscribing to the
    Route objects
    '''
    pass


class FormatterSettings:
    def __init__(self, str_id=P_ID, version_id=P_VERSION, class_id=P_TYPE):
        self.str_id = str_id
        self.version_id = version_id
        self.class_id = class_id


class IFormatter(ABC):
    def write_to_buffer(self, settings: IASettings, _io: IOBase, encoding=None):
        pass

    def write_to_file(self, settings: IASettings, path: str):
        with open(path, 'w') as f:
            # noinspection PyTypeChecker
            self.write_to_buffer(settings, f)

    @abstractmethod
    def serialize(self, obj: Any, route: Route, **kwargs):
        pass

    @abstractmethod
    def  deserialize(self, obj, route: Route, **kwargs):
        pass

    @abstractmethod
    def supports_symantec(self) -> bool:
        pass

    @abstractmethod
    def register_symantec(self, symantec: Symantec):
        pass


class Formatter(IFormatter):
    PRIMITIVES = int | float | str | bool | NoneType
    SPECIAL = dict | list
    TYPES = PRIMITIVES | SPECIAL
    ATTRIBUTE_TYPES = Union[str, Never]

    def convert_route_to_reference_string(self, route: Route) -> str:
        return '.'.join(str(x) for x in route.key_path)

    def __init__(self, settings: FormatterSettings = None):
        if settings is None:
            settings = FormatterSettings()
        self.settings = settings
        self.primitives = set(get_args(self.PRIMITIVES))
        self.special = set(get_args(self.SPECIAL))
        self.attribute = set(get_args(self.ATTRIBUTE_TYPES))
        self.serialization_handler = OrderedMroHandler()
        self.serialization_handler.add_handlers_by_annotated_callable(
            self.handle_serialize_list,
            self.handle_serialize_dict
        )
        self.deserialization_handler = OrderedMroHandler()
        self.deserialization_handler.add_handlers_by_annotated_callable(
            self.handle_serialize_list,
            self.handle_deserialize_dict
        )
        self.auto_preserve_references = True
        self.auto_key_serializable_dict = True

    def supports_symantec(self) -> bool:
        return True

    def register_symantec(self, symantec: Symantec):
        pass

    def handle_serialize_list(self, instance: list, nest, route: Route, **kwargs):
        return [self.serialize(x[1], route.branch(path=x[0]), **kwargs) for x in enumerate(instance)]

    def handle_serialize_dict(self, instance: dict, nest, route: Route, **kwargs):
        if self.auto_key_serializable_dict and any(x.__class__ not in self.attribute for x in instance.keys()):
            return route.handler.handle(KeySerializableDict(instance), route)
        else:
            return dict((k, self.serialize(v, route.branch(path=k), **kwargs)) for k, v in instance.items())

    def handle_deserialize_list(self, instance: list, route: Route, **kwargs):
        pass

    def handle_deserialize_dict(self, instance: dict, route: Route, **kwargs):
        pass

    def serialize(self, obj: Any, route: Route, **kwargs) -> TYPES:
        # when we call serialize we call branch on the route objec
        with route:
            tobj = obj.__class__
            if tobj in self.primitives:
                return obj
            else:
                if self.auto_preserve_references:
                    obj = route.check_in_object(obj, self.convert_route_to_reference_string)
                    tobj = obj.__class__
                if tobj in self.special:
                    return self.serialization_handler.handle(tobj, route, instance=obj, **kwargs)
                else:
                    # This is probably a place where the route needs to be altered for the object
                    new_route = route.branch(obj=obj)
                    ro = self.serialize(route.handler.handle(obj, new_route, **kwargs), new_route)
                    ro[self.settings.class_id] = format_class_str(tobj)
                    if isinstance(obj, VersionedSerializable):
                        version_info = obj.get_version()
                        ro[self.settings.version_id] = self.serialize(version_info, route.branch(obj=version_info))
                    return ro

    def deserialize(self, obj: TYPES, route: Route, **kwargs):
        with route:
            tobj = type(obj)
            if tobj in self.primitives:
                return obj
            elif tobj in self.special:
                return self.deserialization_handler.handle(obj, route, **kwargs)
            else:
                raise ValueError(f'First-pass deserialization created unhandled type: {tobj}')



class JsonFormatter(Formatter):
    pass
