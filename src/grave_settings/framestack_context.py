import os

from grave_settings.handlers import OrderedHandler
from grave_settings.semantics import SemanticContext, Semantics


class FrameStackContext(SemanticContext):
    def __init__(self, handler: OrderedHandler, semantics: Semantics):
        super().__init__(semantics)
        self.handler = handler

    def clear(self):
        self.handler = None

    def set_handler(self, handler: OrderedHandler, merge: bool = True, update_order=True):
        if merge and self.handler is not None and self.handler is not handler:
            handler.update(self.handler, update_order=update_order)
        self.handler = handler

    def __enter__(self):
        self.stack.append(self.handler)
        super().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)
        self.handler = self.stack.pop(-1)

    def __str__(self):
        return super().__str__() + f'{os.linesep}{self.handler}'
