from types import MethodType
from typing import Mapping, Iterable, Type, Callable

from ordered_set import OrderedSet
from ram_util.modules import T
from ram_util.utilities import ext_str_fmt, get_first_parameter_type_hint


class HandlerNotFound(Exception):
    def __init__(self, key=None, *args, **kwargs):
        super().__init__()
        self.key = key
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return ext_str_fmt(self.__class__.__name__, {
            'key': self.key,
            'args': self.args,
            'kwargs': self.kwargs
        }.items())


class Handler(object):
    def __init__(self, *args, **kwargs):
        self.type_bank = {}
        # CAREFUL: initialize is called in the constructor here
        self.init_handler()
        self._default_handler = lambda x, *y, **z: self.default_handler(x, *y, **z)

    def init_handler(self):
        pass

    def update(self, handler: 'Handler'):
        self.type_bank.update(handler.type_bank)

    def add_handler(self, target_type, func_format):
        try:
            handlers = self.type_bank[target_type]
        except KeyError:
            handlers = OrderedSet()
            self.type_bank[target_type] = handlers
        handlers.append(func_format)

    def set_default_handler(self, target_type, func_format):
        try:
            handlers = self.type_bank[target_type]
            if func_format in handlers:
                handlers.remove(func_format)
            handlers.insert(0, func_format)
        except KeyError:
            self.add_handler(target_type, func_format)

    def handle_node(self, key, *args, **kwargs):
        try:
            return self.type_bank[key][0](key, *args, **kwargs)
        except KeyError:
            raise HandlerNotFound(key=key, *args, **kwargs)

    def handle(self, key, *args, **kwargs):
        try:
            ret = self.handle_node(key, *args, **kwargs)
        except HandlerNotFound:
            ret = self._default_handler(key, *args, **kwargs)
        return ret

    def default_handler(self, key, *args, **kwargs):
        raise HandlerNotFound(key=key, *args, **kwargs)


class OrderedHandler(Handler):
    def __init__(self, *args, **kwargs):
        self.type_defaults = {}  # strict types checked first
        self.cache = {}  # Strict types checked second
        # CAREFUL: initialize is called in the constructor here
        super(OrderedHandler, self).__init__(*args, **kwargs)

    def init_handler(self):
        pass

    def update(self, handler: 'OrderedHandler', update_order=True):
        handle_tb = handler.type_bank
        if update_order:
            self.type_bank = {k: v for k, v in self.type_bank.items() if k not in handle_tb}
        self.type_bank.update(handle_tb)
        for _type, _func in handle_tb.items():
            if update_order and _type in self.type_defaults:
                self.type_defaults.pop(_type)
            if _type in self.cache:
                self.cache.pop(_type)
        self.type_defaults.update(handler.type_defaults)
        self.cache.update(handler.cache)

    def add_handler(self, target_type, func_format, bind_as_method=False):
        if bind_as_method:
            func_format = MethodType(func_format, self)
        self.type_bank[target_type] = func_format

    def add_handlers(self, handlers: Mapping | Iterable):
        self.type_bank.update(handlers)

    def set_default_handler(self, target_type, func_format):
        self.type_defaults[target_type] = func_format

    def add_handlers_by_annotated_callable(self, *callables):
        self.add_handlers((get_first_parameter_type_hint(c), c) for c in callables)

    def get_key_func(self, key_type: Type):
        if key_type in self.type_defaults:
            return self.type_defaults[key_type]
        else:
            if key_type in self.cache:
                return self.cache[key_type]
            else:
                for t, f in reversed(self.type_bank.items()):
                    if issubclass(key_type, t):
                        self.cache[key_type] = f
                        return f
                raise HandlerNotFound()

    def handle_node(self, key, *args, **kwargs):
        f = self.get_key_func(key.__class__)
        return f(key, *args, **kwargs)

MHS = Callable[[object, T, ...], T]


class MroHandler(Handler):
    def __init__(self, *args, **kwargs):
        super(MroHandler, self).__init__(*args, **kwargs)
        self.type_bank: dict[Type, MHS] = {}
        self.cache: dict[Type, tuple[MHS]] = {}

    def update(self, handler: 'Handler'):
        super(MroHandler, self).update(handler)
        self.cache = {}

    def add_handler(self, target_type, func_format, bind_as_method=False, clear_cache=True):
        if bind_as_method:
            func_format = MethodType(func_format, self)
        self.type_bank[target_type] = func_format
        if clear_cache:
            self.cache = {}

    def add_handlers(self, handlers: Mapping | Iterable):
        self.type_bank.update(handlers)

    def add_handlers_by_annotated_callable(self, *callables):
        self.add_handlers((get_first_parameter_type_hint(c),c) for c in callables)

    def get_ordered_handlers(self, key):
        if key in self.cache:
            return self.cache[key]
        else:
            bs = tuple(self.type_bank[tt] for tt in reversed(key.__mro__) if tt in self.type_bank)
            if len(bs) <= 0:
                bs = (self._default_handler,)
            self.cache[key] = bs
            return bs

    def handle(self, key: Type | object, *args, instance=None, nest=None, **kwargs):
        if not isinstance(key, type):
            if instance is None:
                instance = key
            key = key.__class__

        for f in self.get_ordered_handlers(key):
            p_nest = f(instance, nest, *args, **kwargs)
            if p_nest is not None:
                nest = p_nest

        return nest

    def handles_object(self, test_obj) -> bool:
        hsrs = self.get_ordered_handlers(test_obj.__class__)
        if len(hsrs) == 1 and hsrs == (self._default_handler,):
            return False

        return True


class StackedHandler(Handler):
    """
    Allows for multiple handler instances to have a chance at handling a type while the default functionality is
    in the default instance of this object.
    """

    def __init__(self, *args, **kwargs):
        self.stack = []
        super(StackedHandler, self).__init__()

    def update(self, handler: 'StackedHandler'):
        self.stack.extend(handler.stack)
        super(StackedHandler, self).update(handler)

    def handle(self, key, *args, **kargs):
        found = False
        ret = None
        # Run add on handlers
        for fmt in reversed(self.stack):
            try:
                ret = fmt.handle_node(key, *args, **kargs)
                found = True
            except HandlerNotFound:
                pass
        # Run default handlers
        try:
            ret = self.handle_node(key, *args, **kargs)
        except HandlerNotFound:
            if not found:
                ret = self._default_handler(key, *args, **kargs)
        return ret

