from grave_settings.abstract import Serializable, Route


class PreservedReferenceNotDissolvedError(Exception):
    pass


class KeySerializableDict(Serializable):
    __slots__ = 'wrapped_dict',

    def __init__(self, wrapped_dict: dict):
        self.wrapped_dict = wrapped_dict

    def to_dict(self, route: Route, **kwargs) -> dict:
        t = route.formatter_settings.temporary
        return {
            'kvps': t([t(x) for x in self.wrapped_dict.items()])
        }

    def from_dict(self, obj: dict, route: Route, **kwargs):
        self.wrapped_dict = dict(x for x in obj['kvps'])


class KeySerializableDictKvpList(KeySerializableDict):
    __slots__ = tuple()

    def to_dict(self, route: Route, **kwargs) -> dict:
        t = route.formatter_settings.temporary
        return {
            'state': t([t({'key': k, 'value': v}) for k, v in self.wrapped_dict.items()])
            }

    def from_dict(self, obj: dict, route: Route, **kwargs):
        self.wrapped_dict = {x['key']: x['value'] for x in obj['state']}


class KeySerializableDictNumbered(KeySerializableDict):
    __slots__ = tuple()

    def to_dict(self, route: Route, **kwargs) -> dict:
        return {
            str(i): list(kv) for i, kv in enumerate(self.wrapped_dict.items())
        }

    def from_dict(self, obj: dict, route: Route, **kwargs):
        self.wrapped_dict = dict(kv for i, kv in obj.items())


class PreservedReference(object):
    __slots__ = 'obj', 'ref', '__weakref__'

    def __init__(self, obj: None | object = None, ref=None):
        if ref is None:
            ref = id(obj)
        self.ref = ref
        self.obj = obj

    def __hash__(self):
        return hash(id(self.obj))


