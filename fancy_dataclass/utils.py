"""Various utility functions and classes."""

import collections.abc
from contextlib import suppress
from copy import copy
import dataclasses
from dataclasses import Field, dataclass, is_dataclass, make_dataclass
from functools import lru_cache
import importlib
from pathlib import Path
import re
import types
from typing import IO, TYPE_CHECKING, Any, Callable, Dict, ForwardRef, Generic, Iterable, Iterator, List, Optional, Sequence, Set, Tuple, Type, TypeVar, Union, get_args, get_origin, get_type_hints

from typing_extensions import TypeGuard


if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar('T')
U = TypeVar('U')

Constructor = Callable[[Any], Any]
AnyPath = Union[str, Path]
AnyIO = Union[IO[str], IO[bytes]]
RecordPath = Tuple[str, ...]

# maximum depth when traversing the fields of a dataclass
MAX_DATACLASS_DEPTH = 100


class TypeConversionError(ValueError):
    """Error type for type conversion."""

    def __init__(self, tp: type, val: Any) -> None:
        """Constructor for `TypeConversionError`.

        Args:
            tp: type to convert to
            val: value to convert"""
        self.tp = tp
        self.val = val
        tp_name = re.sub("'>$", '', re.sub(r"^<\w+ '", '', str(tp)))
        super().__init__(f'could not convert {val!r} to type {tp_name!r}')


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

# DICT MANIPULATION

def safe_dict_insert(d: Dict[Any, Any], key: str, val: Any) -> None:
    """Inserts a (key, value) pair into a dict, if the key is not already present.

    Args:
        d: Dict to modify
        key: Key to insert
        val: Value to insert

    Raises:
        ValueError: If the key is already in the dict"""
    if key in d:
        raise ValueError(f'duplicate key {key!r}')
    d[key] = val

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

# TYPE INSPECTION

def type_is_optional(tp: type) -> bool:
    """Determines if a type is an Optional type.

    Args:
        tp: Type to check

    Returns:
        True if the type is Optional"""
    origin_type = get_origin(tp)
    args = get_args(tp)
    union_types: List[Any] = [Union]
    if hasattr(types, 'UnionType'):  # Python >= 3.10
        union_types.append(types.UnionType)  # novermin
    return (origin_type in union_types) and (type(None) in args)

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

def _is_instance(obj: Any, tp: type) -> bool:
    """Checks if the given object is an instance of the given type.

    This attempts to be somewhat more robust than `isinstance` in that it will handle compound types like `List[...]`."""
    # TODO: make this more complete
    if tp is Any:
        return True
    origin = get_origin(tp)
    if origin is Union:
        return any(_is_instance(obj, arg) for arg in get_args(tp))
    if origin in [list, collections.abc.Sequence]:
        base_type = get_args(tp)[0]
        return isinstance(obj, origin) and all(_is_instance(val, base_type) for val in obj)
    if origin is dict:
        (key_type, val_type) = get_args(tp)
        return isinstance(obj, dict) and all(_is_instance(key, key_type) and _is_instance(val, val_type) for (key, val) in obj.items())
    if origin is collections.abc.Callable:
        # TODO: try to check object's annotations
        return isinstance(obj, Callable)  # type: ignore[arg-type]
    return isinstance(obj, tp)

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
        _ = get_object_from_fully_qualified_name(name)
    for subcls in all_subclasses(cls):
        subcls_name = fully_qualified_class_name(subcls) if fully_qualified else subcls.__name__
        if subcls_name == name:
            return subcls
    else:
        raise ValueError(f'{name} is not a known subclass of {cls.__name__}')

# DATACLASS

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
        for (fld, cons, arg) in zip(dataclasses.fields(self), constructors, args):
            setattr(self, fld.name, cons(arg))
    tp = make_dataclass(cls_name, fields, init=False, **kwargs)
    tp.__init__ = __init__  # type: ignore
    # store the field names in a tuple, to match the behavior of namedtuple
    tp._fields = tuple(fld.name for fld in dataclasses.fields(tp))  # type: ignore[attr-defined]
    return tp

def get_dataclass_fields(obj: Union[type, object], include_classvars: bool = False) -> Tuple[Field, ...]:  # type: ignore[type-arg]
    """Variant of `dataclasses.fields` which can optionally include ClassVars.

    Args:
        obj: Python class or object
        include_classvars: Whether to include `ClassVar` fields

    Returns:
        Tuple of `dataclasses.Field` objects for the dataclass"""
    if include_classvars:
        try:
            return tuple(obj.__dataclass_fields__.values())  # type: ignore[union-attr]
        except AttributeError:
            raise TypeError('must be called with a dataclass type or instance') from None
    return dataclasses.fields(obj)  # type: ignore[arg-type]

def coerce_to_dataclass(cls: Type[T], obj: object) -> T:
    """Coerces the fields from an arbitrary object to an instance of a dataclass type.

    Any missing attributes will be set to the dataclass's default values.

    Args:
        cls: Target dataclass type
        obj: Object to coerce

    Returns:
        A new object of the desired type, coerced from the input object"""
    kwargs = {}
    for fld in dataclasses.fields(cls):  # type: ignore[arg-type]
        if hasattr(obj, fld.name):
            val = getattr(obj, fld.name)
            if is_dataclass(fld.type):
                val = coerce_to_dataclass(fld.type, val)
            else:
                origin_type = get_origin(fld.type)
                if origin_type and issubclass_safe(origin_type, Iterable):
                    if issubclass(origin_type, dict):
                        (_, val_type) = get_args(origin_type)
                        if is_dataclass(val_type):
                            val = type(val)({key: coerce_to_dataclass(val_type, elt) for (key, elt) in val.items()})
                    elif issubclass(origin_type, tuple):
                        val = type(val)(coerce_to_dataclass(tp, elt) if is_dataclass(tp) else elt for (tp, elt) in zip(get_args(fld.type), val))
                    else:
                        (elt_type,) = get_args(fld.type)
                        if is_dataclass(elt_type):
                            val = type(val)(coerce_to_dataclass(elt_type, elt) for elt in val)
            kwargs[fld.name] = val
    return cls(**kwargs)

def dataclass_type_map(cls: Type['DataclassInstance'], func: Callable[[type], type]) -> Type['DataclassInstance']:
    """Applies a type function to all dataclass field types, recursively through container types.

    Args:
        cls: Target dataclass type to manipulate
        func: Function to map onto basic (non-container) field types

    Returns:
        A new dataclass type whose field types have been mapped by the function"""
    def _map_func(tp: type) -> type:
        return func(dataclass_type_map(tp, func)) if is_dataclass(tp) else func(tp)
    # for Py3.8 compatibility, can only subscript typing classes
    container_type_map: Dict[type, type] = {dict: Dict, tuple: Tuple, list: List}  # type: ignore[dict-item]
    field_data = []
    for fld in get_dataclass_fields(cls, include_classvars=True):
        new_fld = copy(fld)
        origin_type = get_origin(fld.type)
        if origin_type and issubclass_safe(origin_type, Iterable):
            otype = container_type_map.get(origin_type, origin_type)
            if issubclass(origin_type, dict):
                (key_type, val_type) = get_args(origin_type)
                tp = otype[key_type, _map_func(val_type)]
            elif issubclass(origin_type, tuple):
                tp = otype[tuple([_map_func(elt_type) for elt_type in get_args(fld.type)])]
            else:
                (elt_type,) = get_args(fld.type)
                tp = otype[_map_func(elt_type)]
        else:
            tp = _map_func(fld.type)
        field_data.append((fld.name, tp, new_fld))
    return make_dataclass(cls.__name__, field_data, bases=cls.__bases__)


##############
# FLATTENING #
##############

def traverse_dataclass(cls: type) -> Iterator[Tuple[RecordPath, Field]]:  # type: ignore[type-arg]
    """Iterates through the fields of a dataclass, yielding (name, field) pairs.

    If the dataclass contains nested dataclasses, recursively iterates through their fields, in depth-first order.

    Nesting is indicated in the field names via "record path" syntax, e.g. `outer.middle.inner`.

    Args:
        cls: Dataclass type

    Returns:
        Generator of (name, field) pairs, where each field is a `dataclasses.Field` object

    Raises:
        TypeError: if the type cannot be traversed"""
    def _make_optional(fld: Field) -> Field:  # type: ignore[type-arg]
        new_fld = copy(fld)
        new_fld.type = Optional[fld.type]  # type: ignore
        new_fld.default = None
        return new_fld
    def _traverse(prefix: RecordPath, tp: type) -> Iterator[Tuple[RecordPath, Field]]:  # type: ignore[type-arg]
        if len(prefix) > MAX_DATACLASS_DEPTH:
            raise TypeError(f'type recursion exceeds depth {MAX_DATACLASS_DEPTH}')
        for fld in get_dataclass_fields(tp, include_classvars=True):
            fld_type = get_type_hints(tp)[fld.name] if isinstance(fld.type, str) else fld.type
            if fld_type is tp:  # prevent infinite recursion
                raise TypeError('type cannot contain a member field of its own type')
            path = prefix + (fld.name,)
            origin = get_origin(fld_type)
            is_union = origin is Union
            if is_union:
                args = get_args(fld_type)
                # if optional, use the wrapped type, otherwise error
                base_types = []
                for arg in args:
                    if isinstance(arg, ForwardRef):
                        raise TypeError('type cannot contain a ForwardRef')
                    base_types.append(arg)
            else:
                base_types = [fld_type]
            if any(not is_dataclass(base_type) for base_type in base_types):
                if is_union:
                    fld = _make_optional(fld)
                yield (path, fld)
            for base_type in base_types:
                if is_dataclass(base_type):
                    subfields = _traverse(path, base_type)
                    if is_union:
                        # wrap each field type in an Optional
                        for (name, subfld) in subfields:
                            subfld = _make_optional(subfld)
                            yield (name, subfld)
                    else:
                        yield from subfields
    yield from _traverse((), cls)


@dataclass
class DataclassConverter(Generic[T, U]):
    """Class for converting values from one dataclass type to another."""
    from_type: Type[T]
    to_type: Type[U]
    forward: Callable[[T], U]
    backward: Optional[Callable[[U], T]] = None


def _flatten_dataclass(cls: Type[T], bases: Optional[Tuple[type, ...]] = None) -> Tuple[Dict[str, RecordPath], DataclassConverter[T, type]]:
    """Given a nested dataclass type, returns data for converting between it and a flattened version of that type.

    Args:
        cls: Nested dataclass type
        bases: Base classes for the flattened type to inherit from

    Returns:
        A tuple, `(field_map, flattened_type, to_flattened, to_nested)`:
            - `field_map` maps from leaf field names to fully qualified names
            - `flattened_type` is the flattened type equivalent to the nested type
            - `to_flattened` is a function converting an object from the nested type to the flattened type
            - `to_nested` is a function converting an object from the flattened type to the nested type

    Raises:
        TypeError: if duplicate field names occur"""
    fields: List[Any] = []
    field_map: Dict[str, RecordPath] = {}
    for (path, fld) in traverse_dataclass(cls):
        try:
            safe_dict_insert(field_map, fld.name, path)  # will error on name collision
        except ValueError as e:
            raise TypeError(str(e)) from None
        fields.append(fld)
    field_data = [(fld.name, fld.type, fld) for fld in fields]
    bases = cls.__bases__ if (bases is None) else bases
    flattened_type = make_dataclass(cls.__name__, field_data, bases=bases)
    def to_flattened(obj: T) -> object:
        def _to_dict(prefix: RecordPath, subobj: 'DataclassInstance') -> Dict[str, Any]:
            kwargs = {}
            for fld in get_dataclass_fields(subobj):
                val = getattr(subobj, fld.name)
                if is_dataclass(val):  # recurse into subfield
                    kwargs.update(_to_dict(prefix + (fld.name,), val))
                else:
                    kwargs[fld.name] = val
            return kwargs
        return flattened_type(**_to_dict((), obj))  # type: ignore[arg-type]
    def to_nested(obj: 'DataclassInstance') -> T:
        def _to_nested(prefix: RecordPath, subcls: Type['DataclassInstance']) -> 'DataclassInstance':
            kwargs = {}
            for fld in get_dataclass_fields(subcls):
                name = fld.name
                path = prefix + (name,)
                origin = get_origin(fld.type)
                def _get_val(tp: type) -> Any:
                    val = _to_nested(path, tp) if is_dataclass(tp) else getattr(obj, name)  # noqa: B023
                    if val is None:
                        raise TypeError(f'invalid {tp.__name__} value: {val}')
                    return val
                if origin is Union:
                    args = get_args(fld.type)
                    for tp in args:
                        try:
                            val = _get_val(tp)
                        except TypeError:
                            continue
                        if val is not None:
                            kwargs[name] = val
                            break
                    else:
                        if type(None) in args:
                            kwargs[name] = None
                        else:
                            raise TypeError(f'could not extract field of type {fld.type}')
                else:
                    kwargs[name] = _get_val(fld.type)
            return subcls(**kwargs)
        return _to_nested((), cls)  # type: ignore
    converter: DataclassConverter[T, Any] = DataclassConverter(cls, flattened_type, to_flattened, to_nested)
    return (field_map, converter)


###########
# MERGING #
###########

def merge_dataclasses(*classes: type, cls_name: str = '_', bases: Optional[Tuple[type, ...]] = None, allow_duplicates: bool = False) -> type:
    """Merges multiple dataclasses together into a single dataclass whose fields have been combined.
    This preserves `ClassVar`s but does not recursively merge subfields.

    Args:
        classes: Multiple dataclass types
        cls_name: Name of the output dataclass
        bases: Base classes for the new type
        allow_duplicates: Whether to allow duplicate field names

    Returns:
        The merged dataclass type

    Raises:
        TypeError: If there are any duplicate field names"""
    flds = []
    field_type_map: Dict[str, type] = {}
    base_map: Dict[str, type] = {}
    @lru_cache
    def _get_field_names(tp: type) -> Set[str]:
        return {fld.name for fld in get_dataclass_fields(tp, include_classvars=True)}
    def _base_type_with_field(cls: type, name: str) -> type:
        for tp in cls.mro()[::-1]:
            with suppress(TypeError):
                if name in _get_field_names(tp):
                    return tp
        raise TypeError(f'no field named {name!r} for {cls}')
    for cls in classes:
        for fld in get_dataclass_fields(cls, include_classvars=True):
            base = _base_type_with_field(cls, fld.name)
            if fld.name in field_type_map:
                if allow_duplicates:
                    if (field_type_map[fld.name] == fld.type):
                        continue
                    raise TypeError(f'duplicate field name {fld.name!r} with mismatched types')
                # allow duplicate field if it came from the same ancestor class
                if base != base_map[fld.name]:
                    raise TypeError(f'duplicate field name {fld.name!r}')
            else:
                field_type_map[fld.name] = fld.type
                base_map[fld.name] = base
                flds.append((fld.name, fld.type, fld))
    # if bases are unspecified, use the original classes
    bases = classes if (bases is None) else bases
    cls = make_dataclass(cls_name, flds, bases=bases)
    # field ordering may get rearranged by make_dataclass (processes fields in reverse MRO order),
    # so we revert them back to their canonical ordering
    cls.__dataclass_fields__ = {name: cls.__dataclass_fields__[name] for (name, _, _) in flds}  # type: ignore[attr-defined]
    return cls
