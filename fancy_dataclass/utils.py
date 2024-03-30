"""Various utility functions and classes."""

from copy import copy
import dataclasses
from dataclasses import Field, dataclass, is_dataclass, make_dataclass
import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, ForwardRef, Generic, Iterator, List, Optional, Sequence, Tuple, Type, TypeVar, Union, get_args, get_origin, get_type_hints

from typing_extensions import Self, TypeGuard


if TYPE_CHECKING:
    from _typeshed import DataclassInstance


T = TypeVar('T')
U = TypeVar('U')

Constructor = Callable[[Any], Any]
AnyPath = str | Path
RecordPath = Tuple[str, ...]

# maximum depth when traversing the fields of a dataclass
MAX_DATACLASS_DEPTH = 100


def safe_dict_insert(d: Dict[Any, Any], key: str, val: Any) -> None:
    """Inserts a (key, value) pair into a dict, if the key is not already present.

    Args:
        d: Dict to modify
        key: Key to insert
        val: Value to insert

    Raises:
        TypeError: If the key is already in the dict"""
    if key in d:
        raise TypeError(f'duplicate key {key!r}')
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
        for (fld, cons, arg) in zip(dataclasses.fields(self), constructors, args):
            setattr(self, fld.name, cons(arg))
    tp = make_dataclass(cls_name, fields, init = False, **kwargs)
    tp.__init__ = __init__  # type: ignore
    # store the field names in a tuple, to match the behavior of namedtuple
    tp._fields = tuple(fld.name for fld in dataclasses.fields(tp))  # type: ignore[attr-defined]
    return tp

def get_dataclass_fields(obj: Union[type, object], include_classvars: bool = False) -> Tuple[Field, ...]:  # type: ignore[type-arg]
    """Variant of dataclasses.fields which can optionally include ClassVars."""
    if include_classvars:
        try:
            return tuple(obj.__dataclass_fields__.values())  # type: ignore[union-attr]
        except AttributeError:
            raise TypeError('must be called with a dataclass type or instance') from None
    return dataclasses.fields(obj)  # type: ignore[arg-type]


##############
# FLATTENING #
##############

def traverse_dataclass(cls: type) -> Iterator[Tuple[RecordPath, Field]]:  # type: ignore[type-arg]
    """Iterates through the fields of a dataclass, yielding (name, field) pairs.
    If the dataclass contains nested dataclasses, recursively iterates through their fields, in depth-first order.
    Nesting is indicated in the field names via "record path" syntax, e.g. `outer.middle.inner`."""
    def _make_optional(fld: Field) -> Field:  # type: ignore[type-arg]
        new_fld = Field
        new_fld = copy(fld)  # type: ignore[assignment]
        new_fld.type = Optional[fld.type]  # type: ignore
        new_fld.default = None  # type: ignore
        return new_fld  # type: ignore[return-value]
    def _traverse(prefix: RecordPath, tp: type) -> Iterator[Tuple[RecordPath, Field]]:  # type: ignore[type-arg]
        if len(prefix) > MAX_DATACLASS_DEPTH:
            raise TypeError(f'Type recursion exceeds depth {MAX_DATACLASS_DEPTH}')
        for fld in get_dataclass_fields(tp, include_classvars=True):
            fld_type = get_type_hints(tp)[fld.name] if isinstance(fld.type, str) else fld.type
            if fld_type is tp:  # prevent infinite recursion
                raise TypeError('Type cannot contain a member field of its own type')
            path = prefix + (fld.name,)
            origin = get_origin(fld_type)
            is_union = origin is Union
            if is_union:
                args = get_args(fld_type)
                # if optional, use the wrapped type, otherwise error
                base_types = []
                for arg in args:
                    if isinstance(arg, ForwardRef):
                        raise TypeError('Type cannot contain a ForwardRef')
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


def _flatten_dataclass(cls: Type[T], bases: Tuple[type, ...] = ()) -> Tuple[Dict[str, RecordPath], DataclassConverter[T, type]]:
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
        safe_dict_insert(field_map, fld.name, path)  # will error on name collision
        fields.append(fld)
    field_data = [(fld.name, fld.type, fld) for fld in fields]
    flattened_type = dataclasses.make_dataclass(cls.__name__, field_data, bases=bases)
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

def merge_dataclasses(*classes: type, cls_name: str = '_') -> type:
    """Merges multiple dataclasses together into a single dataclass whose fields have been combined.
    This preserves `ClassVar`s but does not recursively merge subfields.

    Args:
        classes: Multiple dataclass types
        cls_name: Name of the output dataclass

    Returns:
        The merged dataclass type

    Raises:
        TypeError: if there are any duplicate field names"""
    flds = []
    field_names = set()
    for cls in classes:
        for fld in get_dataclass_fields(cls, include_classvars=True):
            if fld.name in field_names:
                raise TypeError(f'duplicate field name {fld.name!r}')
            field_names.add(fld.name)
            flds.append((fld.name, fld.type, fld))
    return make_dataclass(cls_name, flds)


###################
# DATACLASS MIXIN #
###################

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
        If the base class has a `__settings_type__` class attribute, that class will be instantiated with the provided arguments and stored as a `__settings__` attribute on the subclass.
        These settings can be used to customize the behavior of the subclass."""
        super().__init_subclass__()
        if cls.__settings_type__ is not None:
            stype = cls.__settings_type__
            assert issubclass(stype, DataclassMixinSettings)
            assert check_dataclass(stype)
            field_names = {fld.name for fld in dataclasses.fields(stype)}
        else:
            # TODO: merge __bases__ settings
            stype = None
            field_names = set()
        d = {}
        if getattr(cls, '__settings__', None) is not None:
            settings = cls.__settings__
            if (stype is not None) and (not isinstance(settings, stype)):
                raise TypeError(f'settings type of {cls.__name__} must be {stype.__name__}')
            for fld in dataclasses.fields(cls.__settings__):  # type: ignore[arg-type]
                d[fld.name] = getattr(settings, fld.name)
        # inheritance kwargs will override existing settings
        for (key, val) in kwargs.items():
            if key in field_names:
                d[key] = val
            else:
                raise TypeError(f'unknown settings field {key!r} for {cls.__name__}')
        if cls.__settings_type__ is not None:
            cls.__settings__ = stype(**d)

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
        d = {fld.name : getattr(self, fld.name) for fld in dataclasses.fields(self)}  # type: ignore[arg-type]
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
