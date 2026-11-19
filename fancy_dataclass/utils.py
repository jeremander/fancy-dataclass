"""Various utility functions and classes."""

import collections.abc
from collections.abc import Sequence
from contextlib import suppress
import dataclasses
from dataclasses import MISSING, Field, is_dataclass
import importlib
import inspect
from pathlib import Path
import re
import types
from typing import (
    IO,
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    ForwardRef,
    Optional,
    TypeAlias,
    TypeGuard,
    TypeVar,
    Union,
    _SpecialForm,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from typeguard import CollectionCheckStrategy, TypeCheckError, check_type
from typing_extensions import Never, _AnnotatedAlias


if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar('T')

AnyPath: TypeAlias = str | Path
AnyIO: TypeAlias = IO[str] | IO[bytes]
AnyVersion: TypeAlias = int | Sequence[int] | str
TypeLike: TypeAlias = type | _SpecialForm | ForwardRef | _AnnotatedAlias
DataclassType: TypeAlias = type['DataclassInstance']


###############
# ERROR TYPES #
###############

class TypeValidationError(TypeError):
    """Error type for runtime type-checking."""

    def __init__(self, expected_type: TypeLike, value: Any) -> None:
        """Constructor for `TypeValidationError`.

        Args:
            expected_type: type to check the value against
            value: value to type-check"""
        self.expected_type = expected_type
        self.value = value
        super().__init__(f'value {value!r} does not match expected type {get_type_name(expected_type)}')


class FieldTypeValidationError(TypeError):
    """Error type for runtime type-checking a value of a dataclass field."""

    def __init__(
        self,
        cls: type,
        field_name: str,
        field_type: TypeLike,
        value: Any,
        *,
        is_default: bool = False,
        msg: Optional[str] = None,
    ) -> None:
        """Constructor for `FieldTypeValidationError`.

        Args:
            cls: type of the dataclass whose field is being checked
            field_name: name of the field being checked
            field_type: type to check the value against
            value: value to type-check
            is_default: flag indicating whether the value is a field default
            msg: additional error message for context"""
        self.cls = cls
        self.field_name = field_name
        self.field_type = field_type
        self.value = value
        self.is_default = is_default
        cls_name = get_type_name(cls)
        if value == MISSING:
            # error message indicates that the field value is missing, rather than the wrong type
            err_msg = f'field {field_name!r} is missing for {cls_name}'
        else:
            default_str = 'default ' if is_default else ''
            err = TypeValidationError(field_type, value)
            err_msg = f'field {field_name!r} of {cls_name}: {default_str}{err}'
        if msg is not None:
            # append message with extra context
            err_msg += f'\n  {msg}'
        super().__init__(err_msg)


class MissingRequiredFieldError(ValueError):
    """Error type for a missing required field."""

    def __init__(self, name: str, alias: Optional[str] = None) -> None:
        """Constructor for `MissingRequiredFieldError`.

        Args:
            name: name of the missing field
            alias: alias of the missing field (e.g. when converting a JSON key)"""
        self.name = name
        self.alias = alias
        msg = f'{self.name!r} field'
        if alias:
            msg += f' (alias {alias!r})'
        msg += ' is required'
        super().__init__(msg)


####################
# HELPER FUNCTIONS #
####################

# STRING MANIPULATION

def snake_case_to_camel_case(name: str) -> str:
    """Converts a string from snake case to camel case.

    Args:
        name: String to convert

    Returns:
        Camel case version of the string"""
    capitalize = lambda s: (s[0].upper() + s[1:]) if s else ''
    return ''.join(map(capitalize, name.split('_')))

def camel_case_to_kebab_case(name: str) -> str:
    """Converts a string from camel case to kebab case.

    Args:
        name: String to convert

    Returns:
        Kebab case version of the string"""
    segs = []
    n = len(name)
    name = name.replace('_', '-')
    for (i, c) in enumerate(name):
        if c.isupper():
            if ((i < n - 1) and name[i + 1].islower()) or ((i > 0) and (name[i - 1].islower())):
                segs.append('-' + c.lower())
            else:
                segs.append(c.lower())
        else:
            segs.append(c)
    return ''.join(segs).lstrip('-')

# VERSION STRINGS

def get_version_string(version: AnyVersion) -> str:
    """Renders a version-like object (string, int, or int sequence) as a dot-separated version string."""
    if (not isinstance(version, str)) and isinstance(version, Sequence):
        return '.'.join(map(str, version))
    return str(version)

# DICT MANIPULATION

def safe_dict_update(d1: dict[str, Any], d2: dict[str, Any]) -> None:
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

# TYPE INSPECTION

def get_type_name(tp: TypeLike) -> str:
    """Renders a type-like object as a human-readable string."""
    return re.sub("'>$", '', re.sub(r"^<\w+ '", '', str(tp)))

_UNION_TYPES = [Union, types.UnionType] if hasattr(types, 'UnionType') else [Union]  # novermin

def type_is_union(tp: TypeLike) -> bool:
    """Determines if a type is a Union type.

    Args:
        tp: Type to check

    Returns:
        True if the type is a Union"""
    origin_type = get_origin(tp)
    return origin_type in _UNION_TYPES

def type_is_optional(tp: TypeLike) -> bool:
    """Determines if a type is an Optional type.

    Args:
        tp: Type to check

    Returns:
        True if the type is Optional"""
    origin_type = get_origin(tp)
    args = get_args(tp)
    return (origin_type in _UNION_TYPES) and (type(None) in args)

def type_is_classvar(tp: TypeLike) -> bool:
    """Determines if a type is a ClassVar.

    Args:
        tp: Type to check

    Returns:
        True if the type is a ClassVar"""
    return get_origin(tp) is ClassVar

def get_annotated_elements(tp: TypeLike) -> Optional[tuple[TypeLike, tuple[Any, ...]]]:
    """If the given type is Annotated, returns the wrapped type and a tuple of additional annotated elements.

    Args:
        tp: Type to examine

    Returns:
        A tuple (wrapped type, extra elements) if `tp` is `Annotated`, otherwise `None`
    Otherwise, returns None."""
    if get_origin(tp) is not Annotated:
        return None
    args = get_args(tp)
    return (args[0], args[1:])

def all_subclasses(cls: type[T]) -> list[type[T]]:
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

def issubclass_safe(type1: TypeLike, type2: type) -> bool:
    """Calls `issubclass(type1, type2)`, returning `False` if an error occurs.

    Args:
        type1: First type
        type2: Second type

    Returns:
        `True` if `type1` is a subclass of `type2`

    Raises:
        TypeError: If `type1` is something like a `GenericAlias`"""
    try:
        return issubclass(type1, type2)  # type: ignore[arg-type]
    except TypeError:
        return False

def _is_subtype(tp1: type, tp2: type) -> bool:
    """Checks if one type is a subtype of the other.

    This attempts to be somewhat more flexible than `issubclass` in that it will handle compound types
    like `list[...]`."""
    # TODO: make this more complete
    if tp2 is Any:
        return True
    origin1 = get_origin(tp1)
    origin2 = get_origin(tp2)
    if origin1 in _UNION_TYPES:
        return all(_is_subtype(arg, tp2) for arg in get_args(tp1))
    if origin2 in _UNION_TYPES:
        return any(_is_subtype(tp1, arg) for arg in get_args(tp2))
    if origin2 in [list, collections.abc.Sequence, ClassVar]:
        return (origin1 == origin2) and _is_subtype(get_args(tp1)[0], get_args(tp2)[0])
    if origin2 is dict:
        if origin1 == origin2:
            (key_type1, val_type1) = get_args(tp1)
            (key_type2, val_type2) = get_args(tp2)
            return _is_subtype(key_type1, key_type2) and _is_subtype(val_type1, val_type2)
        return False
    return issubclass_safe(tp1, tp2)  # fallback

def _check_type(obj: Any, tp: TypeLike) -> None:
    """Checks if the given object conforms to the given type, raising a TypeError if not."""
    # Currently Never is not handled properly by typeguard, so handle it specially.
    # However, it still won't work if the Never type is nested in a compound type.
    #   see: https://github.com/agronholm/typeguard/issues/580
    if tp is Never:
        raise TypeValidationError(tp, obj)
    try:
        _ = check_type(obj, tp, collection_check_strategy=CollectionCheckStrategy.ALL_ITEMS)
    except TypeCheckError as e:
        raise TypeValidationError(tp, obj) from e

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
    return f'{cls.__module__}.{cls.__qualname__}'

def get_object_from_fully_qualified_name(name: str) -> object:
    """Given a fully-qualified name of some object, gets the object, importing the module as needed.

    Args:
        name: Fully qualified object name

    Returns:
        Object with the fully qualified name

    Raises:
        ValueError: If the name does not have a . character"""
    if '.' not in name:
        raise ValueError(f'{name!r} is not a fully qualified name')
    toks = name.split('.')
    mod_name, obj_name = '.'.join(toks[:-1]), toks[-1]
    mod = importlib.import_module(mod_name)
    return getattr(mod, obj_name)

def get_subclass_with_name(cls: type[T], name: str) -> type[T]:
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
        _ = get_object_from_fully_qualified_name(name)
    for subcls in all_subclasses(cls):
        subcls_name = fully_qualified_class_name(subcls) if fully_qualified else subcls.__name__
        if subcls_name == name:
            return subcls
    raise ValueError(f'{name} is not a known subclass of {cls.__name__}')

# DATACLASS

def check_dataclass(cls: type) -> TypeGuard[DataclassType]:
    """Checks whether a given type is a dataclass, raising a `TypeError` otherwise.

    Args:
        cls: A Python type

    Raises:
        TypeError: If the given type is not a dataclass"""
    if not is_dataclass(cls):
        raise TypeError(f'{cls.__name__} is not a dataclass')
    return True

def is_dataclass_type(cls: type) -> TypeGuard[DataclassType]:
    """Returns True if the given type is a dataclass.

    Args:
        cls: A Python type

    Returns:
        True if `cls` is a dataclass"""
    return is_dataclass(cls)

def get_dataclass_fields(obj: type | object, include_all: bool = False) -> tuple[Field, ...]:  # type: ignore[type-arg]
    """Variant of `dataclasses.fields` which can optionally include ClassVars and InitVars.

    Args:
        obj: Python class or object
        include_all: Whether to include `ClassVar` and `InitVar` fields

    Returns:
        Tuple of `dataclasses.Field` objects for the dataclass"""
    if include_all:
        try:
            return tuple(obj.__dataclass_fields__.values())  # type: ignore[union-attr]
        except AttributeError:
            raise TypeError('must be called with a dataclass type or instance') from None
    return dataclasses.fields(obj)  # type: ignore[arg-type]

def get_annotations(cls: type) -> dict[str, Any]:
    """Given a type, gets a dict mapping from field names to types."""
    anns: dict[str, Any] = {}
    for tp in cls.mro()[::-1]:
        anns.update(getattr(tp, '__annotations__', {}))
    return anns

def _get_all_stack_variables() -> dict[str, Any]:
    """Gets a dict of global and local variables for all frames of the current call stack."""
    globs = {}
    stack = inspect.stack()
    for finfo in stack[::-1]:
        globs.update(finfo.frame.f_globals)
        globs.update(finfo.frame.f_locals)
    return globs

def eval_type_str(type_str: str) -> type:
    """Gets the fully-evaluated type from a "stringized" type.

    Args:
        type_str: String representing a type

    Returns:
        Fully evaluated type"""
    # TODO: this may become obsolete once PEP 649 becomes available
    # see: https://peps.python.org/pep-0649
    tp = None
    if '.' in type_str:  # fully qualified: import module and retrieve the type
        with suppress(ModuleNotFoundError):
            tp = get_object_from_fully_qualified_name(type_str)
    # otherwise, a builtin type, locally defined type, or type with complex annotations
    if tp is None:
        # since names from typing/typing_extensions are common, we import all the names
        globs = {}
        for mod_name in ['typing_extensions', 'typing']:
            mod = importlib.import_module(mod_name)
            globs[mod_name] = mod
            globs.update(mod.__dict__)
        globs.update(globals())
        try:
            tp = eval(type_str, globs)
        except NameError:
            # NOTE: globals do not get carried from up the stack.
            # Some names may be missing, so we include them here.
            globs = {**_get_all_stack_variables(), **globs}
            tp = eval(type_str, globs)
    return cast(type, tp)

def dataclass_field_type(cls: DataclassType, name: str) -> type:
    """Given a dataclass type and field name, gets the dataclass field's type annotation.

    If the annotation is a string, resolves it to a type (see PEP 563, 649).

    Args:
        cls: Dataclass type
        name: Name of field

    Returns:
        Fully evaluated type

    Raises:
        AttributeError if there is no dataclass field with the given name"""
    try:
        try:
            return cast(type, get_type_hints(cls)[name])
        except NameError:  # try to resolve string annotation manually
            field_type_str = cls.__annotations__[name]
            assert isinstance(field_type_str, str)
            return eval_type_str(field_type_str)
    except KeyError:
        raise AttributeError(f'type {get_type_name(cls)} has no dataclass field {name!r}') from None

# VALIDATION

def _validate_dataclass_field(cls: type, fld: Field[Any], value: Any, *, is_default: bool = False) -> None:
    """Given a dataclass type, Field object, and field value, checks if the value matches the expected type.
    If not, raises a [`FieldTypeValidationError`][fancy_dataclass.utils.FieldTypeValidationError]."""
    tp = get_args(fld.type)[0] if type_is_classvar(fld.type) else fld.type
    try:
        _check_type(value, tp)
    except TypeValidationError as e:
        kwargs: dict[str, Any] = {'is_default': is_default}
        if e.__cause__:
            kwargs['msg'] = str(e.__cause__)
        raise FieldTypeValidationError(cls, fld.name, tp, value, **kwargs) from e
