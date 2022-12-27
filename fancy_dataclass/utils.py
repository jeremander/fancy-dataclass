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

class DataclassMixin:
    """Mixin class that adds some functionality to a dataclass (for example, conversion to/from JSON or argparse arguments.
    This class provides a `wrap_dataclass` decorator which can be used to wrap an existing dataclass into one that provides the mixin's functionality."""
    @classmethod
    def wrap_dataclass(cls: Type[T], tp: Type[T]) -> Type[T]:
        """Given a dataclass type, constructs a new type that is a subclass of this mixin class and is otherwise the same."""
        check_dataclass(tp)
        if issubclass(tp, cls):  # the type is already a subclass of this one, so just return it
            return tp
        # otherwise, create a new type that inherits from this class
        return type(tp.__name__, (tp, cls), {})
    def _replace(self: T, **kwargs: Any) -> T:
        """Constructs a new object with the provided fields modified."""
        assert hasattr(self, '__dataclass_fields__'), f'{obj_class_name(self)} is not a dataclass type'
        d = {field.name : getattr(self, field.name) for field in dataclasses.fields(self)}
        for (key, val) in kwargs.items():
            if (key in d):
                d[key] = val
            else:
                raise TypeError(f'{key!r} is not a valid field for {obj_class_name(self)}')
        return self.__class__(**d)  # type: ignore
    @classmethod
    def get_subclass_with_name(cls: Type[T], typename: str) -> Type[T]:
        """Gets the subclass of this class with the given name.
        Riases a TypeError if no such subclass exists."""
        return get_subclass_with_name(cls, typename)