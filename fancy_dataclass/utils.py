"""Various utility functions and classes."""

import dataclasses
from dataclasses import is_dataclass, make_dataclass
import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, List, Optional, Sequence, Tuple, Type, TypeVar, Union

from typing_extensions import Self, TypeGuard


if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar('T')

Constructor = Callable[[Any], Any]
AnyPath = str | Path


def safe_dict_update(d1: Dict[str, Any], d2: Dict[str, Any]) -> None:
    """Updates the first dict with the second, in-place.

    Args:
        d1: First dict, to be updated
        d2: Second dict

    Raises:
        ValueError: If any dict keys overlap"""
    for (key, val) in d2.items():
        if key in d1:
            raise ValueError(f'duplicate key {key!r}')
        d1[key] = val

def all_subclasses(cls: Type[T]) -> List[Type[T]]:
    """Gets all subclasses of a given class, including the class itself.

    Args:
        cls: Input class

    Returns:
        List of subclasses of the input class"""
    subclasses = [cls]
    for subcls in cls.__subclasses__():
        subclasses += all_subclasses(subcls)
    # for some arcane reason, we need to resolve the ids of the classes to prevent strange behavior
    [id(subcls) for subcls in subclasses]
    return subclasses

def issubclass_safe(type1: type, type2: type) -> bool:
    """Calls `issubclass(type1, type2)`, returning `False` if an error occurs.

    Args:
        type1: First type
        type2: Second type

    Returns:
        `True` if `type1` is a subclass of `type2`

    Raises:
        TypeError: If `type1` is something like a `GenericAlias`"""
    try:
        return issubclass(type1, type2)
    except TypeError:
        return False

def obj_class_name(obj: object) -> str:
    """Gets the name of the class of an object.

    Args:
        obj: A Python object

    Returns:
        Name of the object's class"""
    return obj.__class__.__name__

def fully_qualified_class_name(cls: type) -> str:
    """Gets the fully qualified name of a class (including full module path and class name).

    Args:
        cls: A Python class

    Returns:
        Fully qualified name of the class"""
    return str(cls).split("'")[-2]

def get_subclass_with_name(cls: Type[T], name: str) -> Type[T]:
    """Gets the subclass of a class with the given name.

    Args:
        cls: A Python class
        name: Name of the subclass

    Returns:
        Subclass of `cls` with the given name

    Raises:
        ValueError: If no subclass with the given name exists"""
    fully_qualified = '.' in name
    cls_name = fully_qualified_class_name(cls) if fully_qualified else cls.__name__
    if cls_name == name:
        return cls
    if fully_qualified:  # import the module
        toks = name.split('.')
        mod_name, cls_name = '.'.join(toks[:-1]), toks[-1]
        importlib.import_module(mod_name)
    for subcls in all_subclasses(cls):
        subcls_name = fully_qualified_class_name(subcls) if fully_qualified else subcls.__name__
        if subcls_name == name:
            return subcls
    else:
        raise ValueError(f'{name} is not a known subclass of {cls.__name__}')

def check_dataclass(cls: type) -> TypeGuard[Type['DataclassInstance']]:
    """Checks whether a given type is a dataclass, raising a `TypeError` otherwise.

    Args:
        cls: A Python type

    Raises:
        TypeError: If the given type is not a dataclass"""
    if not is_dataclass(cls):
        raise TypeError(f'{cls.__name__} is not a dataclass')
    return True

def make_dataclass_with_constructors(cls_name: str, fields: Sequence[Union[str, Tuple[str, type]]], constructors: Sequence[Constructor], **kwargs: Any) -> Type['DataclassInstance']:
    """Type factory for dataclasses with custom constructors.

    Args:
        cls_name: Name of the dataclass type
        fields: List of field names, or pairs of field names and types
        constructors: List of one-argument constructors for each field
        kwargs: Additional keyword arguments to pass to `dataclasses.make_dataclass`

    Returns:
        A dataclass type with the given fields and constructors"""
    def __init__(self: 'DataclassInstance', *args: Any) -> None:
        # take inputs and wrap them in the provided constructors
        for (field, cons, arg) in zip(dataclasses.fields(self), constructors, args):
            setattr(self, field.name, cons(arg))
    tp = make_dataclass(cls_name, fields, init = False, **kwargs)
    tp.__init__ = __init__  # type: ignore
    # store the field names in a tuple, to match the behavior of namedtuple
    tp._fields = tuple(field.name for field in dataclasses.fields(tp))  # type: ignore[attr-defined]
    return tp


class DataclassMixinSettings:
    """Base class for settings to be associated with `fancy_dataclass` mixins.

    Each [`DataclassMixin`][fancy_dataclass.utils.DataclassMixin] class may store a `__settings_type__` attribute consisting of a subclass of this class. The settings object will be stored as the `__settings__ attribute when the mixin class is subclassed."""


class DataclassMixin:
    """Mixin class that adds some functionality to a dataclass.

    For example, this could provide features for conversion to/from JSON (see [`JSONDataclass`][fancy_dataclass.json.JSONDataclass]), or the ability to construct CLI argument parsers (see [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass]).

    This mixin provides a [`wrap_dataclass`][fancy_dataclass.utils.DataclassMixin.wrap_dataclass] decorator which can be used to wrap an existing dataclass into one that provides the mixin's functionality."""

    __settings_type__: ClassVar[Optional[Type[DataclassMixinSettings]]] = None
    __settings__: ClassVar[Optional[DataclassMixinSettings]] = None

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """When inheriting from this class, you may pass various flags as keyword arguments after the list of base classes.
        If the base class has a `__settings_type__` class attribute, that class will be instantiated with the provided arguments and stored as a `_settings` attribute on the subclass.
        These settings can be used to customize the behavior of the subclass."""
        super().__init_subclass__()
        if cls.__settings_type__ is not None:
            stype = cls.__settings_type__
            assert issubclass(stype, DataclassMixinSettings)
            assert check_dataclass(stype)
            field_names = {field.name for field in dataclasses.fields(stype)}
        else:
            stype = None
            field_names = set()
        d = {}
        if getattr(cls, '__settings__', None) is not None:
            settings = cls.__settings__
            if (stype is not None) and (not isinstance(settings, stype)):
                raise TypeError(f'settings type of {cls.__name__} must be {stype.__name__}')
            for field in dataclasses.fields(cls.__settings__):  # type: ignore[arg-type]
                d[field.name] = getattr(settings, field.name)
        # inheritance kwargs will override existing settings
        for (key, val) in kwargs.items():
            if key in field_names:
                d[key] = val
            else:
                raise TypeError(f'unknown settings field {key!r} for {cls.__name__}')
        if cls.__settings_type__ is not None:
            cls.__settings__ = stype(**d)  # type: ignore[assignment]

    @classmethod
    def wrap_dataclass(cls: Type[Self], tp: Type[T]) -> Type[Self]:
        """Wraps a dataclass type into a new one which inherits from this mixin class and is otherwise the same.

        Args:
            tp: A dataclass type

        Returns:
            New dataclass type inheriting from the mixin

        Raises:
            TypeError: If the given type is not a dataclass"""
        check_dataclass(tp)
        if issubclass(tp, cls):  # the type is already a subclass of this one, so just return it
            return tp
        # otherwise, create a new type that inherits from this class
        return type(tp.__name__, (tp, cls), {})

    def _replace(self: T, **kwargs: Any) -> T:
        """Constructs a new object with the provided fields modified.

        Args:
            **kwargs: Dataclass fields to modify

        Returns:
            New object with selected fields modified

        Raises:
            TypeError: If an invalid dataclass field is provided"""
        assert hasattr(self, '__dataclass_fields__'), f'{obj_class_name(self)} is not a dataclass type'
        d = {field.name : getattr(self, field.name) for field in dataclasses.fields(self)}  # type: ignore[arg-type]
        for (key, val) in kwargs.items():
            if key in d:
                d[key] = val
            else:
                raise TypeError(f'{key!r} is not a valid field for {obj_class_name(self)}')
        return self.__class__(**d)

    @classmethod
    def get_subclass_with_name(cls: Type[T], typename: str) -> Type[T]:
        """Gets the subclass of this class with the given name.

        Args:
            typename: Name of subclass

        Returns:
            Subclass with the given name

        Raises:
            TypeError: If no subclass with the given name exists"""
        return get_subclass_with_name(cls, typename)
