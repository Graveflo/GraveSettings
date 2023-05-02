from types import MethodType
from typing import Mapping, Iterable, Type, Callable, Self
from ordered_set import OrderedSet

from grave_settings.utilities import ext_str_fmt, get_type_hints, T


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

    def init_handler(self):
        pass

    def add_handlers_by_type_hints(self, *callables):
        self.add_handlers((get_type_hints(c)[0], c) for c in callables)

    def add_handlers(self, handlers: Mapping | Iterable):
        self.type_bank.update(handlers)

    def update(self, handler: Self):
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

    def get_key_func(self, item: Type):
        try:
            return self.type_bank[item]
        except KeyError:
            raise HandlerNotFound(key=item)

    def handle_node(self, key, *args, **kwargs):
        try:
            key_func = self.get_key_func(key)
        except KeyError:
            raise HandlerNotFound(key=key, *args, **kwargs)
        return key_func[0](key, *args, **kwargs)

    def handle(self, key, *args, **kwargs):
        return self.handle_node(key, *args, **kwargs)

    def __contains__(self, item):
        try:
            self.get_key_func(item)
            return True
        except HandlerNotFound:
            return False


class OrderedHandler(Handler):
    def __init__(self, *args, **kwargs):
        self.cache = {}  # types checked second
        # CAREFUL: initialize is called in the constructor here
        super(OrderedHandler, self).__init__(*args, **kwargs)

    def init_handler(self):
        pass

    def update(self, handler: 'OrderedHandler', update_order=True):
        if update_order:
            handle_tb = self.type_bank
            handle_ref = handler.type_bank
        else:
            handle_tb = handler.type_bank
            handle_ref = self.type_bank
        if update_order:
            self.type_bank = {k: v for k, v in handle_ref.items() if k not in handle_tb}
        self.type_bank.update(handle_tb)

        for _type, _func in handle_tb.items():
            if _type in self.cache:
                self.cache.pop(_type)
        self.cache.update(handler.cache)

    def add_handler(self, target_type, func_format, bind_as_method=False):
        if bind_as_method:
            func_format = MethodType(func_format, self)
        self.type_bank[target_type] = func_format

    def __contains__(self, item: Type):
        if item in self.cache:
            return True
        else:
            for t in self.type_bank:
                if issubclass(item, t):
                    return True
        return False

    def get_key_func(self, key_type: Type):
        if key_type in self.cache:
            return self.cache[key_type]
        else:
            for t, f in reversed(self.type_bank.items()):
                if issubclass(key_type, t):
                    self.cache[key_type] = f
                    return f
            raise HandlerNotFound()

    def handle_node(self, key, *args, **kwargs):
        try:
            return self.get_key_func(key)(key, *args, **kwargs)
        except HandlerNotFound as e:
            e.args = args
            e.kwargs = kwargs
            e.key = key
            raise e

    def handle(self, key, *args, **kwargs):
        try:
            return self.get_key_func(key.__class__)(key, *args, **kwargs)
        except HandlerNotFound as e:
            e.args = args
            e.kwargs = kwargs
            e.key = key
            raise e


class OrderedMethodHandler(OrderedHandler):
    def add_handlers_by_type_hints(self, *callables: MethodType):
        self.add_handlers((get_type_hints(c)[0], c.__func__) if isinstance(c, MethodType) else (get_type_hints(c)[1],c) for c in callables)

    def handle_node(self, pass_self, key, *args, **kwargs):
        f = self.get_key_func(key.__class__)
        return f(pass_self, key, *args, **kwargs)

    def handle(self, pass_self, instance, *args, **kwargs):
        return self.handle_node(pass_self, instance, *args, **kwargs)


MHS = Callable[[object, T, ...], T]


class MroHandler(Handler):
    def __init__(self, *args, **kwargs):
        super(MroHandler, self).__init__(*args, **kwargs)
        self.type_bank: dict[Type, MHS] = self.type_bank
        self.cache: dict[Type, tuple[MHS]] = {}
    def update(self, handler: Handler):
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

    def get_ordered_handlers(self, key):
        if key in self.cache:
            return self.cache[key]
        else:
            bs = tuple(self.type_bank[tt] for tt in reversed(key.__mro__) if tt in self.type_bank)
            if len(bs) <= 0:
                bs = tuple()
            self.cache[key] = bs
            return bs

    def handle(self, instance, *args, **kwargs):
        return self.handle_custom(instance.__class__, instance, None,  *args, **kwargs)

    def __contains__(self, item: Type):
        if item in self.cache:
            return True
        else:
            for t in self.type_bank:
                if issubclass(item, t):
                    return True
        return False

    def handle_custom(self, key: type, instance, nest, *args, **kwargs):
        for f in self.get_ordered_handlers(key):
            p_nest = f(instance, nest, *args, **kwargs)
            if p_nest is not None:  # dont overwrite Nones
                nest = p_nest
        return nest



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

