from grave_settings.abstract import Serializable
from grave_settings.formatter_settings import Temporary
from grave_settings.framestack_context import FrameStackContext


class PreservedReferenceNotDissolvedError(Exception):
    pass


class KeySerializableDict(Serializable):
    __slots__ = 'wrapped_dict',

    def __init__(self, wrapped_dict: dict):
        self.wrapped_dict = wrapped_dict

    def to_dict(self, context: FrameStackContext, **kwargs) -> dict:
        t = Temporary
        return {
            'kvps': t([t(x) for x in self.wrapped_dict.items()])
        }

    def from_dict(self, obj: dict, context: FrameStackContext, **kwargs):
        self.wrapped_dict = dict(x for x in obj['kvps'])


class KeySerializableDictKvpList(KeySerializableDict):
    __slots__ = tuple()

    def to_dict(self, context: FrameStackContext, **kwargs) -> dict:
        t = Temporary
        return {
            'state': t([t({'key': k, 'value': v}) for k, v in self.wrapped_dict.items()])
            }

    def from_dict(self, obj: dict, context: FrameStackContext, **kwargs):
        self.wrapped_dict = {x['key']: x['value'] for x in obj['state']}


class KeySerializableDictNumbered(KeySerializableDict):
    __slots__ = tuple()

    def to_dict(self, context: FrameStackContext, **kwargs) -> dict:
        return {
            str(i): list(kv) for i, kv in enumerate(self.wrapped_dict.items())
        }

    def from_dict(self, obj: dict, context: FrameStackContext, **kwargs):
        self.wrapped_dict = dict(kv for i, kv in obj.items())
