import dataclasses
from typing import Any, Container, Dict, Type, TypeVar, Union

from fancy_dataclass.utils import check_dataclass, obj_class_name

T = TypeVar('T')


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
    def replace(self: T, **kwargs: Any) -> T:
        """Constructs a new object with the provided fields modified."""
        assert hasattr(self, '__dataclass_fields__'), f'{obj_class_name(self)} is not a dataclass type'
        d = {field.name : getattr(self, field.name) for field in dataclasses.fields(self)}
        for (key, val) in kwargs.items():
            if (key in d):
                d[key] = val
            else:
                raise TypeError(f'{key!r} is not a valid field for {obj_class_name(self)}')
        return self.__class__(**d)  # type: ignore

class DataclassFromDict(DataclassMixin):
    """Mixin class that can convert a dict into a bundle of arguments to pass to a dataclass constructor."""
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
        origin_type = getattr(tp, '__origin__', None)
        if (origin_type is None):  # basic class or type
            if (tp == Any):  # assume basic data type
                return x
            elif (type(tp) == TypeVar):
                # can't refer to instantiated type, so we assume a basic data type
                # NB: this limitation means we can only use TypeVar for basic types
                return x
            elif hasattr(tp, 'from_dict'):  # handle nested fields which are themselves convertible from a dict
                return cls._convert_dict_convertible(tp, x)
            elif issubclass(tp, tuple):  # will catch namedtuples too
                return tp(*x)
            elif issubclass(tp, dict):
                return tp(x)
            else:  # basic data type
                return tp(x)  # type: ignore
        else:  # compound data type
            if (origin_type == list):
                subtype = tp.__args[0]
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
                    except:
                        continue
            elif hasattr(origin_type, 'from_dict'):
                return cls._convert_dict_convertible(origin_type, x)
            elif issubclass(origin_type, Container):  # arbitrary container
                subtype = tp.__args__[0]
                return type(x)(cls._convert_value(subtype, y) for y in x)
        raise ValueError(f'could not convert {x!r} to type {tp!r}')
    @classmethod
    def _dataclass_args_from_dict(cls, d: Dict[str, Any]) -> Dict[str, Any]:
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
                else:
                    kwargs[field.name] = field.default_factory()  # type: ignore
        return kwargs
    @classmethod
    def from_dict(cls: Type[T], d: Dict[str, Any]) -> T:
        """Constructor from a dictionary of fields.
        This will perform some basic type/validity checking."""
        return cls(**cls._dataclass_args_from_dict(d))  # type: ignore
