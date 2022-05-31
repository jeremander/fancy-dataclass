import dataclasses
from dataclasses import is_dataclass, make_dataclass
import importlib
from typing import Any, Callable, List, Sequence, Tuple, Type, TypeVar, Union

T = TypeVar('T')

Constructor = Callable[[Any], Any]


def all_subclasses(cls: Type[T]) -> List[Type[T]]:
    """Gets all subclasses of a given class, including the class itself."""
    subclasses = [cls]
    for subcls in cls.__subclasses__():
        subclasses += all_subclasses(subcls)
    # for some arcane reason, we need to resolve the ids of the classes to prevent strange behavior
    [id(subcls) for subcls in subclasses]
    return subclasses

def issubclass_safe(type1: type, type2: type) -> bool:
    """Attempts to call issubclass(type1, type2).
    This can raise a TypeError if type1 is something like a GenericAlias.
    This function will catch such errors and return False."""
    try:
        return issubclass(type1, type2)
    except TypeError:
        return False

def obj_class_name(obj: Any) -> str:
    """Gets the name of the class of an object."""
    return obj.__class__.__name__

def fully_qualified_class_name(cls: type) -> str:
    """Given a class, gets its fully qualified class name (includes module and class name)."""
    return str(cls).split("'")[-2]

def get_subclass_with_name(cls: Type[T], name: str) -> Type[T]:
    """If a given name is a subclass of cls, returns the corresponding subclass.
    Otherwise, raises a ValueError."""
    fully_qualified = '.' in name
    cls_name = fully_qualified_class_name(cls) if fully_qualified else cls.__name__
    if (cls_name == name):
        return cls
    if fully_qualified:  # import the module
        toks = name.split('.')
        mod_name, cls_name = '.'.join(toks[:-1]), toks[-1]
        importlib.import_module(mod_name)
    for subcls in all_subclasses(cls):
        subcls_name = fully_qualified_class_name(subcls) if fully_qualified else subcls.__name__
        if (subcls_name == name):
            return subcls
    else:
        raise ValueError(f'{name} is not a known subclass of {cls.__name__}')

def check_dataclass(cls: type) -> None:
    """Checks if a type is a dataclass, raising a TypeError otherwise."""
    if (not is_dataclass(cls)):
        raise TypeError(f'{cls.__name__} is not a dataclass')

def make_dataclass_with_constructors(cls_name: str, fields: Sequence[Union[str, Tuple[str, type]]], constructors: Sequence[Constructor]) -> type:
    """Type factory for dataclasses with custom constructors.
        cls_name: name of the type
        fields: list of the field names, or field names with types
        constructors: list of one-argument constructors for each field"""
    def __init__(self, *args: Any) -> None:
        # take inputs and wrap them in the provided constructors
        for (field, cons, arg) in zip(dataclasses.fields(self), constructors, args):
            setattr(self, field.name, cons(arg))
    tp = make_dataclass(cls_name, fields, init = False)
    tp.__init__ = __init__  # type: ignore
    # store the field names in a tuple, to match the behavior of namedtuple
    tp._fields = tuple(field.name for field in dataclasses.fields(tp))
    return tp
