from collections import defaultdict
import dataclasses
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Container, Dict, List, Literal, Type, TypeVar, Union

from fancy_dataclass.utils import check_dataclass, DataclassMixin, fully_qualified_class_name, issubclass_safe, obj_class_name


T = TypeVar('T')
JSONDict = Dict[str, Any]


def safe_dict_insert(d: JSONDict, key: str, val: Any) -> None:
    """Inserts a (key, value) pair into a dict, if the key is not already present.

    Args:
        d: Dict to modify
        key: Key to insert
        val: Value to insert

    Raises:
        TypeError: If the key is already in the dict"""
    if (key in d):
        raise TypeError(f'duplicate key {key!r}')
    d[key] = val


class DictDataclass(DataclassMixin):
    """Base class for dataclasses that can be converted to and from a regular Python dict.

    Subclasses may set the following boolean flags as class attributes:
        - `suppress_defaults`: suppress default values in its dict
        - `store_type`: store the object's type in its dict
        - `qualified_type`: fully qualify the object type's name in its dict
        - `strict`: raise a `TypeError` in [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] if extraneous fields are present
        - `nested`: if True, [`DictDataclass`][fancy_dataclass.dict.DictDataclass] subfields will be nested; otherwise, they are merged together with the main fields (provided there are no name collisions)"""

    suppress_defaults: ClassVar[bool] = True
    store_type: ClassVar[bool] = False
    qualified_type: ClassVar[bool] = False
    strict: ClassVar[bool] = False
    nested: ClassVar[bool] = True

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """When inheriting from this class, you may pass various flags as keyword arguments after the list of base classes; these will be stored as class variables."""
        super().__init_subclass__()
        for (key, val) in kwargs.items():
            setattr(cls, key, val)

    def _dict_init(self) -> JSONDict:
        if self.__class__.qualified_type:
            return {'type' : fully_qualified_class_name(self.__class__)}
        elif self.__class__.store_type:
            return {'type' : obj_class_name(self)}
        return {}

    @classmethod
    def get_fields(cls) -> List[dataclasses.Field]:
        """Gets the list of fields in the object's dict representation.

        Returns:
            A list of `dataclasses.Field` objects containing field metadata"""
        flds = []
        for field in dataclasses.fields(cls):
            try:
                is_nested = issubclass(field.type, DictDataclass) and field.type.nested
            except TypeError:
                is_nested = False
            if is_nested:  # expand nested subfields
                flds += field.type.get_fields()
            else:
                flds.append(field)
        return flds

    def _to_dict(self, full: bool) -> JSONDict:
        def _to_value(x: Any) -> Any:
            if isinstance(x, Enum):
                return x.value
            elif isinstance(x, range):  # store the range bounds
                bounds = [x.start, x.stop]
                if (x.step != 1):
                    bounds.append(x.step)
                return bounds
            elif isinstance(x, list):
                return [_to_value(y) for y in x]
            elif isinstance(x, tuple):
                return tuple(_to_value(y) for y in x)
            elif isinstance(x, dict):
                return {k : _to_value(v) for (k, v) in x.items()}
            elif isinstance(x, datetime):
                return x.isoformat()
            elif isinstance(x, (int, float)):  # handles numpy numeric types
                return x
            elif hasattr(x, 'dtype'):  # assume it's a numpy array of numbers
                return [float(y) for y in x]
            elif isinstance(x, DictDataclass):
                return x.to_dict(full = full)
            return x
        d = self._dict_init()
        fields = getattr(self.__class__, '__dataclass_fields__', None)
        if (fields is not None):
            for (name, field) in fields.items():
                if (name == 'type'):
                    raise ValueError(f"'type' is an invalid {obj_class_name(self)} field")
                if (getattr(field.type, '__origin__', None) is ClassVar):  # do not include ClassVars in dict
                    continue
                if (not field.init):  # suppress fields where init = False
                    continue
                val = getattr(self, name)
                if (not full):  # suppress values that match the default
                    try:
                        if (val == field.default):
                            continue
                        if (field.default_factory != dataclasses.MISSING) and (val == field.default_factory()):
                            continue
                    except ValueError:  # some types may fail to compare
                        pass
                field_val = _to_value(val)
                if (not self.__class__.nested) and isinstance(field_val, dict):
                    # merge subfield's dict instead of nesting
                    for (k, v) in field_val.items():
                        safe_dict_insert(d, k, v)
                else:  # nested dict OK
                    safe_dict_insert(d, name, field_val)
        return d

    def to_dict(self, **kwargs: Any) -> JSONDict:
        """Renders a dict which, by default, suppresses values matching their dataclass defaults.

        If `full = True` or the class has set the `suppress_defaults` flag to False, does not suppress the defaults.

        Returns:
            A dict whose keys match the dataclass's fields"""
        full = kwargs.get('full', not self.__class__.suppress_defaults)
        return self._to_dict(full)

    @staticmethod
    def _convert_dict_convertible(tp: type, x: Any) -> Any:
        if isinstance(x, tp):  # already converted from a dict
            return x
        # otherwise, convert from a dict
        return tp.from_dict(x)

    @classmethod
    def _convert_value(cls, tp: type, x: Any) -> Any:
        """Given a type and a value, attempts to convert the value to the given type."""
        if (x is None):
            return None
        if (tp in [Any, 'typing.Any']):  # assume basic data type
            return x
        if issubclass_safe(tp, list):
            # class may inherit from List[T], so get the parent class
            for base in tp.__orig_bases__:
                origin_type = getattr(base, '__origin__', None)
                if origin_type and issubclass_safe(origin_type, list):
                    tp = base
                    break
        origin_type = getattr(tp, '__origin__', None)
        if (origin_type is None):  # basic class or type
            if (type(tp) == TypeVar):
                # can't refer to instantiated type, so we assume a basic data type
                # NB: this limitation means we can only use TypeVar for basic types
                return x
            elif hasattr(tp, 'from_dict'):  # handle nested fields which are themselves convertible from a dict
                return cls._convert_dict_convertible(tp, x)
            elif issubclass(tp, (tuple, range)):  # will catch namedtuples too
                return tp(*x)
            elif issubclass(tp, dict):
                return tp(x)
            elif issubclass(tp, datetime):
                return tp.fromisoformat(x)
            else:  # basic data type
                return tp(x)  # type: ignore
        else:  # compound data type
            if (origin_type == list):
                subtype = tp.__args__[0]
                return [cls._convert_value(subtype, y) for y in x]
            elif (origin_type == dict):
                (keytype, valtype) = tp.__args__
                return {cls._convert_value(keytype, k) : cls._convert_value(valtype, v) for (k, v) in x.items()}
            elif (origin_type == tuple):
                subtypes = tp.__args__
                if (subtypes[-1] == Ellipsis):  # treat it like a list
                    subtype = subtypes[0]
                    return tuple(cls._convert_value(subtype, y) for y in x)
                return tuple(cls._convert_value(subtype, y) for (subtype, y) in zip(tp.__args__, x))
            elif (origin_type == Union):
                for subtype in tp.__args__:
                    try:
                        # NB: will resolve to the first valid type in the Union
                        return cls._convert_value(subtype, x)
                    except Exception:
                        continue
            elif (origin_type == Literal):
                if any((x == arg) for arg in tp.__args__):
                    # one of the Literal options is matched
                    return x
            elif hasattr(origin_type, 'from_dict'):
                return cls._convert_dict_convertible(origin_type, x)
            elif issubclass_safe(origin_type, Container):  # arbitrary container
                subtype = tp.__args__[0]
                return type(x)(cls._convert_value(subtype, y) for y in x)
        raise ValueError(f'could not convert {x!r} to type {tp!r}')

    @classmethod
    def _class_with_merged_fields(cls: Type[T]) -> Type[T]:
        """Converts this type into an isomorphic type where any nested DictDataclass fields have all of their subfields merged into the outer type."""
        fields: List[Any] = []
        field_map: Dict[str, str] = {}
        for field in dataclasses.fields(cls):
            origin = getattr(field.type, '__origin__', None)
            if (origin is Union):  # use the first type of a Union (also handles Optional)
                tp = field.type.__args__[0]
            else:
                tp = field.type
            if issubclass(tp, DictDataclass):
                for fld in dataclasses.fields(tp):
                    safe_dict_insert(field_map, fld.name, field.name)
                    fields.append(fld)
            else:
                fields.append(field)
        cls2 = dataclasses.make_dataclass(cls.__name__, [(field.name, field.type, field) for field in fields], bases = (DictDataclass,))
        # set flags to be identical to the original class (except force nested=True)
        flags = [key for (key, tp) in cls.__annotations__.items() if (getattr(tp, '__origin__', None) is ClassVar)]
        for flag in flags:
            setattr(cls2, flag, getattr(cls, flag))
        cls2.nested = False
        # create method to convert from merged object to nested object
        def _to_nested(self: object) -> object:
            kwargs = {}
            nested_kwargs: Dict[str, Any] = defaultdict(dict)
            types_by_name = {field.name : field.type for field in dataclasses.fields(cls)}
            for field in dataclasses.fields(self):
                key = field.name
                val = getattr(self, key)
                if (key in field_map):  # a merged field
                    nested_kwargs[field_map[key]][key] = val
                else:  # a regular field
                    kwargs[key] = val
            for (key, d) in nested_kwargs.items():
                kwargs[key] = types_by_name[key](**d)
            return cls(**kwargs)
        cls2._to_nested = _to_nested
        return cls2

    @classmethod
    def _dataclass_args_from_dict(cls, d: JSONDict) -> JSONDict:
        """Given a dict of arguments, performs type conversion and/or validity checking, then returns a new dict that can be passed to the class's constructor."""
        check_dataclass(cls)
        kwargs = {}
        bases = cls.mro()
        fields = dataclasses.fields(cls)
        for field in fields:
            if (not field.init):  # suppress fields where init = False
                continue
            if (field.name in d):
                # field may be defined in the dataclass itself or one of its ancestor dataclasses
                for base in bases:
                    try:
                        field_type = base.__annotations__[field.name]
                        kwargs[field.name] = cls._convert_value(field_type, d[field.name])
                        break
                    except (AttributeError, KeyError):
                        pass
                else:
                    raise ValueError(f'could not locate field {field.name!r}')
            elif (field.default == dataclasses.MISSING):
                if (field.default_factory == dataclasses.MISSING):  # type: ignore
                    raise ValueError(f'{field.name!r} field is required')
                kwargs[field.name] = field.default_factory()
        return kwargs

    @classmethod
    def from_dict(cls: Type[T], d: JSONDict) -> T:
        """Constructs an object from a dictionary of fields.

        This may also perform some basic type/validity checking.

        Args:
            d: Dict to convert into an object

        Returns:
            Converted object of this class"""
        # first establish the type, which may be present in the 'type' field of the dict
        typename = d.get('type')
        if (typename is None):  # type field unspecified, so use the calling class
            tp = cls
        else:
            cls_name = fully_qualified_class_name(cls) if ('.' in typename) else cls.__name__
            if (cls_name == typename):  # type name already matches this class
                tp = cls
            else:
                # tp must be a subclass of cls
                # the name must be in scope to be found, allowing two alternatives for retrieval:
                # option 1: all subclasses of this DictDataclass are defined in the same module as the base class
                # option 2: the name is fully qualified, so the name can be loaded into scope
                # call from_dict on the subclass in case it has its own custom implementation
                d2 = dict(d)
                d2.pop('type')  # remove the type name before passing to the constructor
                return cls.get_subclass_with_name(typename).from_dict(d2)
        if (not cls.nested):
            # produce equivalent subfield-merged types, then convert the dict
            cls = cls._class_with_merged_fields()
            tp = tp._class_with_merged_fields()
        result = tp(**tp._dataclass_args_from_dict(d))  # type: ignore
        return result if cls.nested else result._to_nested()
