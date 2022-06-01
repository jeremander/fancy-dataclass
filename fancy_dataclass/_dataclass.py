import dataclasses
from enum import Enum
from typing import Any, ClassVar, Container, Dict, Type, TypeVar, Union

from fancy_dataclass.utils import check_dataclass, fully_qualified_class_name, get_subclass_with_name, obj_class_name

T = TypeVar('T')

JSONDict = Dict[str, Any]


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

class DictDataclass(DataclassMixin):
    """Base class for dataclasses that can be converted to and from a regular Python dict."""
    # if True, suppresses default values in 'to_dict'
    suppress_defaults: ClassVar[bool] = True
    # if True, stores the object's type in its dict representation
    store_type: ClassVar[bool] = False
    # if True, fully qualifies the type name in the dict representation
    qualified_type: ClassVar[bool] = False
    # if this is True, DictDataclass subfields will be nested; otherwise, they are merged
    nested: ClassVar[bool] = True
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
    def _to_dict(self, full: bool) -> JSONDict:
        def _to_value(x: Any) -> Any:
            if isinstance(x, Enum):
                return x.value
            elif isinstance(x, range):
                return list(x)
            elif isinstance(x, list):
                return [_to_value(y) for y in x]
            elif isinstance(x, tuple):
                return tuple(_to_value(y) for y in x)
            elif isinstance(x, dict):
                return {k : _to_value(v) for (k, v) in x.items()}
            elif hasattr(x, 'dtype'):  # assume it's a numpy array of numbers
                return [float(y) for y in x]
            elif hasattr(x, 'to_dict'):
                return x.to_dict()
            return x
        d = self._dict_init()
        fields = getattr(self.__class__, '__dataclass_fields__', None)
        if (fields is not None):
            for (name, field) in fields.items():
                if (name == 'type'):
                    raise ValueError("'type' is an invalid JSONDataclass field")
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
                d[name] = _to_value(val)
        return d
    def to_dict(self, **kwargs: Any) -> JSONDict:
        """Renders a dict which, by default, suppresses values matching their dataclass defaults.
        If full = True or the class's `suppress_defaults` is False, does not suppress defaults."""
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
                else:
                    kwargs[field.name] = field.default_factory()  # type: ignore
        return kwargs
    @classmethod
    def from_dict(cls: Type[T], d: JSONDict) -> T:
        """Constructor from a dictionary of fields.
        This may perform some basic type/validity checking."""
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
                # option 1: all subclasses of this JSONDataclass are defined in the same module as the base class
                # option 2: the name is fully qualified, so the name can be loaded into scope
                # call from_dict on the subclass in case it has its own custom implementation
                d2 = dict(d)
                d2.pop('type')  # remove the type name before passing to the constructor
                return get_subclass_with_name(cls, typename).from_dict(d2)
        return tp(**cls._dataclass_args_from_dict(d))  # type: ignore
