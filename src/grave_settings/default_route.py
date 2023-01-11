# - * -coding: utf - 8 - * -
"""


@author: ☙ Ryan McConnell ❧
"""
from typing import Self, Type

from observer_hooks import EventHandler
from grave_settings.abstract import Route
from grave_settings.formatter_settings import FormatterSettings
from grave_settings.semantics import Semantic, remove_semantic_from_dict, T_S


class DefaultRoute(Route):
    #__slots__ = 'key_path', 'logical_path', 'id_cache', 'handler', '_finalize'

    def __init__(self, handler, finalize_handler: EventHandler = None):
        super().__init__(handler, finalize_handler=finalize_handler)
        self.frame_semantics = None
        self.semantics = None
        self.formatter_settings: FormatterSettings | None = None

    def clear(self):
        super().clear()
        self.semantics = None
        self.frame_semantics = None

    def add_frame_semantic(self, semantic: Semantic):
        if self.frame_semantics is None:
            self.frame_semantics = {}
        self.frame_semantics[semantic.__class__] = semantic

    def add_semantic(self, semantic: Semantic):
        if self.semantics is None:
            self.semantics = {}
        self.semantics[semantic.__class__] = semantic

    def remove_frame_semantic(self, semantic: Type[Semantic] | Semantic):
        remove_semantic_from_dict(semantic, self.frame_semantics)

    def remove_semantic(self, semantic: Type[Semantic] | Semantic):
        remove_semantic_from_dict(semantic, self.semantics)

    def get_semantic(self, t_semantic: Type[T_S]) -> T_S | None:
        if self.frame_semantics is not None:
            if t_semantic in self.frame_semantics:
                return self.frame_semantics[t_semantic]
        elif self.semantics is not None:
            if t_semantic in self.semantics:
                return self.semantics[t_semantic]

    def new(self, finalize_event: EventHandler) -> Self:
        return self.__class__(self.handler, finalize_handler=finalize_event)

    def branch(self):
        r = self.new(self._finalize)  # we want to maintain a handle to the root frame's finalize EventHandler
        if self.semantics is not None:
            r.semantics = self.semantics.copy()
        r.formatter_settings = self.formatter_settings
        return r





