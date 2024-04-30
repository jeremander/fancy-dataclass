from dataclasses import field, make_dataclass
from inspect import getfullargspec
from typing import Any, Callable, Optional, Tuple, TypeVar

from typing_extensions import ParamSpec


P = ParamSpec('P')
R = TypeVar('R')


def snake_case_to_camel_case(name: str) -> str:
    """Converts a string from snake case to camel case.

    Args:
        name: String to convert

    Returns:
        Camel-case version of the string"""
    capitalize = lambda s: (s[0].upper() + s[1:]) if s else ''
    return ''.join(map(capitalize, name.split('_')))

def func_dataclass(func: Callable[[Any], Any], method_name: str = '__call__', cls_name: Optional[str] = None, bases: Tuple[type, ...] = ()) -> type:
    """Wraps a function into a new dataclass type with a single method whose positional arguments (other than self) are equivalent to that of the given function, and whose kwargs are dataclass parameters.

    Args:
        func: Function to convert to a dataclass
        method_name: Name of method that will call the function
        cls_name: Name of the new type (if `None`, converts the function's name from snake case to camel case)
        bases: Base classes for the new type

    Returns:
        A new type inheriting from `bases` with the name `cls_name` and a single method `method_name`"""
    cls_name = cls_name or snake_case_to_camel_case(func.__name__)
    spec = getfullargspec(func)
    if spec.varkw is not None:
        raise TypeError('cannot use func_dataclass on a function with keyword arguments')
    defaults = spec.defaults or ()
    num_kwargs = len(defaults)
    num_args = len(spec.args) - num_kwargs
    kwarg_names = spec.args[num_args:]
    field_data = []
    def _default_to_default_factory(default: Any) -> Callable[[], Any]:
        return lambda: default
    for (kwarg, default) in zip(kwarg_names, defaults):
        if isinstance(default, (list, dict)):
            fld = field(default_factory=_default_to_default_factory(default))
        else:
            fld = field(default=default)
        field_data.append((kwarg, spec.annotations.get(kwarg, Any), fld))
    def method(self: Any, *args: Any) -> Any:
        kwargs = {kwarg: getattr(self, kwarg) for kwarg in kwarg_names}
        return func(*args, **kwargs)
    namespace = {method_name: method}
    return make_dataclass(cls_name, field_data, bases=bases, namespace=namespace)
