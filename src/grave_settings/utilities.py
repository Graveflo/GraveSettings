import builtins
import inspect
import sys
import types
from inspect import signature
from typing import Type, Callable, Any, Generator, Iterable, TypeVar

T = TypeVar('T')


def unwrap_slots_to_base(base: Type, target_class: Type, include_base=False) -> set:
    names = set()
    if target_class is not base:
        if hasattr(target_class, '__slots__'):
            names.update(target_class.__slots__)
        for cls in target_class.__bases__:
            n_names = unwrap_slots_to_base(base, cls)
            n_names.update(names)
            names = n_names
    elif include_base:
        if hasattr(base, '__slots__'):
            names.update(base.__slots__)
    return names


# TODO: This is vulnerable to circular references blowing up the execution stack
def build_attribute_string(k_v_p_attrs: Iterable[tuple[str, object]]) -> str:
    return ",".join(f'{k}={v}' for k, v in k_v_p_attrs)


def generate_slots_kvps(obj: object, base=object):
    for k in unwrap_slots_to_base(object, obj.__class__):
        if hasattr(obj, k):
            yield k, obj.__getattribute__(k)


def ext_str_slots(obj: object, base=object, generator=generate_slots_kvps):
    vals_list = build_attribute_string(generator(obj, base=base))
    return f'{obj.__class__.__name__}({vals_list})'


def ext_str_fmt(name, vals_gen):
    return f'{name}({build_attribute_string(vals_gen)})'


def ex_str(obj: object):
    if hasattr(obj, '__dict__'):
        vals_list = ",".join(f'{k}={obj.__getattribute__(k)}' for k in vars(obj))
        return f'{obj.__class__.__name__}({vals_list})'
    else:
        return ext_str_slots(obj)


def format_class_str(x):
    module = x.__module__
    return f'{module}.{x.__name__}'


def generate_type_hierarchy_to_base(base: Type[T], target_class: Type) -> Generator[Type[T], None, None]:
    if issubclass(target_class, base) and target_class is not base:
        for cls in target_class.__bases__:
            yield from generate_type_hierarchy_to_base(base, cls)
        yield target_class


def load_type(str_type, do_import=True):
    type_comp = str_type.split('.')
    module_name = '.'.join(type_comp[:-1])
    try:
        cls = sys.modules[module_name]
        return cls.__dict__[type_comp[-1]]
    except KeyError:
        pass
    if type_comp[0] == 'builtins':
        try:
            return builtins.__dict__[type_comp[-1]]
        except KeyError:
            pass
        return types.__dict__[type_comp[-1]]
    if do_import:
        __import__(module_name, {}, locals(), ['*'], 0)
        return sys.modules[module_name].__dict__[type_comp[-1]]
    else:
        raise PermissionError()


def get_type_hints(func: Callable) -> tuple[Any]:
    return tuple(a if (a := x.annotation) is not inspect._empty else Any for x in signature(func).parameters.values())


def get_first_parameter_type_hint(func: Callable) -> Type:
    if (p := next(iter(signature(func).parameters.values())).annotation) is not inspect._empty:
        return p
    else:
        raise NotImplementedError(f'The callable {func} does not have type annotations on its first parameter')

