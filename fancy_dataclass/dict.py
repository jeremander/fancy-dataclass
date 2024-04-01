from copy import copy
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import partial
import re
from typing import TYPE_CHECKING, Any, ClassVar, Container, Dict, Literal, Optional, Type, TypeVar, Union, _TypedDictMeta, get_args, get_origin  # type: ignore[attr-defined]

from typing_extensions import Self, _AnnotatedAlias

from fancy_dataclass.mixin import DataclassMixin, DataclassMixinSettings, FieldSettings
from fancy_dataclass.utils import _flatten_dataclass, check_dataclass, fully_qualified_class_name, issubclass_safe, obj_class_name, safe_dict_insert


if TYPE_CHECKING:
    from _typeshed import DataclassInstance

T = TypeVar('T', bound=DataclassMixin)
D = TypeVar('D', bound='DataclassInstance')

JSONDict = Dict[str, Any]


@dataclass
class DictDataclassSettings(DataclassMixinSettings):
    """Settings for the DictDataclass mixin.

    Inheritors of [`DictDataclass`][fancy_dataclass.dict.DictDataclass] may set the following boolean flags:
        - `suppress_defaults`: suppress default values in its dict
        - `store_type`: store the object's type in its dict
        - `qualified_type`: fully qualify the object type's name in its dict
        - `flattened`: if True, [`DictDataclass`][fancy_dataclass.dict.DictDataclass] subfields will be merged together with the main fields (provided there are no name collisions); otherwise, they are nested"""
    suppress_defaults: bool = True
    store_type: bool = False
    qualified_type: bool = False
    flattened: bool = False


@dataclass
class DictDataclassFieldSettings(FieldSettings):
    """Settings for [`DictDataclass`][fancy_dataclass.dict.DictDataclass] fields."""
    # suppress the field in the dict
    suppress: Optional[bool] = None
    # suppress the field in the dict if its value matches the default
    suppress_default: Optional[bool] = None


class DictDataclass(DataclassMixin):
    """Base class for dataclasses that can be converted to and from a JSON-serializable Python dict.

    A subclass may configure settings by storing a [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings] object as its `_settings` attribute.

    Per-field settings can be passed into the `metadata` argument of a `dataclasses.field`:
        - `suppress`: suppress this field in the dict (note: a `ClassVar` assumes this is `True` by default; you can set it to `False` to force the field's inclusion)
        - `suppress_default`: suppress this field in the dict if it matches its default value (overrides class-level `suppress_defaults`)"""

    __settings_type__ = DictDataclassSettings
    __settings__ = DictDataclassSettings()
    __field_settings_type__ = DictDataclassFieldSettings

    @classmethod
    def __post_dataclass_wrap__(cls) -> None:
        super().__post_dataclass_wrap__()
        store_type = cls.__settings__.store_type or cls.__settings__.qualified_type
        if store_type:
            for fld in dataclasses.fields(cls):  # type: ignore[arg-type]
                if fld.name == 'type':
                    raise TypeError(f"'type' is a reserved dict field for {cls.__name__}, cannot be used as dataclass field")

    def _dict_init(self) -> JSONDict:
        """Gets the basic skeleton for a dict generated by this type.
        If `store_type` or `qualified_type` is set to `True`, will include a `type` field to store the type."""
        if self.__settings__.store_type:
            return {'type' : obj_class_name(self)}
        if self.__settings__.qualified_type:
            return {'type' : fully_qualified_class_name(self.__class__)}
        return {}

    def _to_dict(self, full: bool) -> JSONDict:
        if self.__settings__.flattened:
            cls = type(self)
            flat_obj = _flatten_dataclass(cls)[1].forward(self)
            return flat_obj._to_dict(full)  # type: ignore
        def _to_value(x: Any) -> Any:
            if isinstance(x, Enum):
                return x.value
            elif isinstance(x, range):  # store the range bounds
                bounds = [x.start, x.stop]
                if x.step != 1:
                    bounds.append(x.step)
                return bounds
            elif isinstance(x, list):
                return [_to_value(y) for y in x]
            elif isinstance(x, tuple):
                # if a namedtuple, render as a dict with named fields rather than a tuple
                if hasattr(x, '_fields'):
                    return {k: _to_value(v) for (k, v) in zip(x._fields, x)}
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
                return x.to_dict(full=full)
            return x
        d = self._dict_init()
        class_suppress_defaults = self.__settings__.suppress_defaults
        for (name, field) in self.__dataclass_fields__.items():  # type: ignore[attr-defined]
            is_class_var = get_origin(field.type) is ClassVar
            fld_settings = DictDataclassFieldSettings.coerce(self._field_settings(field))
            # suppress field by default if it is a ClassVar or init=False
            if (is_class_var or (not field.init)) if (fld_settings.suppress is None) else fld_settings.suppress:
                continue
            val = getattr(self, name)
            # suppress default (by default) if full=False and class-configured suppress_defaults=True
            if (not full) and (class_suppress_defaults if (fld_settings.suppress_default is None) else fld_settings.suppress_default):
                # suppress values that match the default
                try:
                    if val == field.default:
                        continue
                    if (field.default_factory != dataclasses.MISSING) and (val == field.default_factory()):
                        continue
                except ValueError:  # some types may fail to compare
                    pass
            safe_dict_insert(d, name, _to_value(val))
        return d

    def to_dict(self, **kwargs: Any) -> JSONDict:
        """Converts the object to a JSON-compatible dict which, by default, suppresses values matching their dataclass defaults.

        If `full=True` or the class has set the `suppress_defaults` flag to False, does not suppress the defaults.

        Returns:
            A dict whose keys match the dataclass's fields"""
        full = kwargs.get('full', False)
        return self._to_dict(full)

    @staticmethod
    def _convert_dict_convertible(tp: Type['DictDataclass'], x: Any, strict: bool) -> Any:
        if isinstance(x, tp):  # already converted from a dict
            return x
        # otherwise, convert from a dict
        return tp.from_dict(x, strict=strict)

    @classmethod
    def _convert_value(cls, tp: type, x: Any, strict: bool = False) -> Any:
        """Given a type and a value, attempts to convert the value to the given type."""
        def err() -> ValueError:
            tp_name = re.sub("'>$", '', re.sub(r"^<\w+ '", '', str(tp)))
            return ValueError(f'could not convert {x!r} to type {tp_name!r}')
        convert_val = partial(cls._convert_value, strict=strict)
        if tp is type(None):
            if x is None:
                return None
            raise err()
        if tp in [Any, 'typing.Any']:  # assume basic data type
            return x
        ttp = type(tp)
        if ttp is _AnnotatedAlias:  # Annotated: just ignore the annotation
            return convert_val(get_args(tp)[0], x)
        if issubclass_safe(tp, list):
            # class may inherit from List[T], so get the parent class
            assert hasattr(tp, '__orig_bases__')
            for base in tp.__orig_bases__:
                origin_type = get_origin(base)
                if origin_type and issubclass_safe(origin_type, list):
                    tp = base
                    break
        origin_type = get_origin(tp)
        if origin_type is None:  # basic class or type
            if ttp == TypeVar:  # type: ignore[comparison-overlap]
                # can't refer to instantiated type, so we assume a basic data type
                # this limitation means we can only use TypeVar for basic types
                return x
            elif hasattr(tp, 'from_dict'):  # handle nested fields which are themselves convertible from a dict
                return cls._convert_dict_convertible(tp, x, strict)
            elif issubclass(tp, float):
                return tp(x)
            elif issubclass(tp, tuple):
                if isinstance(x, dict) and hasattr(tp, '_fields'):  # namedtuple
                    try:
                        vals = []
                        for key in tp._fields:
                            # if NamedTuple's types are annotated, check them
                            valtype = tp.__annotations__.get(key)
                            vals.append(x[key] if (valtype is None) else convert_val(valtype, x[key]))
                        return tp(*vals)
                    except KeyError as e:
                        raise err() from e
                return tp(*x)
            elif issubclass(tp, range):
                return tp(*x)
            elif issubclass(tp, dict):
                if ttp is _TypedDictMeta:  # validate TypedDict fields
                    anns = tp.__annotations__
                    if (not isinstance(x, dict)) or (set(anns) != set(x)):
                        raise err()
                    return {key: convert_val(valtype, x[key]) for (key, valtype) in anns.items()}
                return tp(x)
            elif issubclass(tp, datetime):
                return tp.fromisoformat(x)
            elif issubclass(tp, Enum):
                try:
                    return tp(x)
                except ValueError as e:
                    raise err() from e
            else:  # basic data type
                if not isinstance(x, tp):  # validate type
                    raise err()
                return x
                # NOTE: alternatively, we could coerce to the type
                # if x is None:  # do not coerce None
                #     raise err()
                # try:
                #     return tp(x)  # type: ignore[call-arg]
                # except TypeError as e:
                #     raise err() from e
        else:  # compound data type
            args = get_args(tp)
            if origin_type == list:
                subtype = args[0]
                return [convert_val(subtype, y) for y in x]
            elif origin_type == dict:
                (keytype, valtype) = args
                return {convert_val(keytype, k) : convert_val(valtype, v) for (k, v) in x.items()}
            elif origin_type == tuple:
                subtypes = args
                if subtypes[-1] == Ellipsis:  # treat it like a list
                    subtype = subtypes[0]
                    return tuple(convert_val(subtype, y) for y in x)
                return tuple(convert_val(subtype, y) for (subtype, y) in zip(args, x))
            elif origin_type == Union:
                if getattr(tp, '_name', None) == 'Optional':
                    assert len(args) == 2
                    assert args[1] is type(None)
                    args = args[::-1]  # check None first
                for subtype in args:
                    try:
                        # NB: will resolve to the first valid type in the Union
                        return convert_val(subtype, x)
                    except Exception:
                        continue
            elif origin_type == Literal:
                if any((x == arg) for arg in args):
                    # one of the Literal options is matched
                    return x
            elif hasattr(origin_type, 'from_dict'):
                return cls._convert_dict_convertible(origin_type, x, strict)
            elif issubclass_safe(origin_type, Container):  # arbitrary container
                subtype = args[0]
                return type(x)(convert_val(subtype, y) for y in x)
        raise err()

    @classmethod
    def _dataclass_args_from_dict(cls, d: JSONDict, strict: bool = False) -> JSONDict:
        """Given a dict of arguments, performs type conversion and/or validity checking, then returns a new dict that can be passed to the class's constructor."""
        check_dataclass(cls)
        kwargs = {}
        bases = cls.mro()
        fields = dataclasses.fields(cls)  # type: ignore[arg-type]
        if strict:  # check there are no extraneous fields
            field_names = {field.name for field in fields}
            for key in d:
                if (key not in field_names):
                    raise ValueError(f'{key!r} is not a valid field for {cls.__name__}')
        for field in fields:
            if not field.init:  # suppress fields where init=False
                continue
            if field.name in d:
                # field may be defined in the dataclass itself or one of its ancestor dataclasses
                for base in bases:
                    try:
                        field_type = base.__annotations__[field.name]
                        kwargs[field.name] = cls._convert_value(field_type, d[field.name], strict=strict)
                        break
                    except (AttributeError, KeyError):
                        pass
                else:
                    raise ValueError(f'could not locate field {field.name!r}')
            elif field.default == dataclasses.MISSING:
                if field.default_factory == dataclasses.MISSING:
                    raise ValueError(f'{field.name!r} field is required')
                kwargs[field.name] = field.default_factory()
        return kwargs

    @classmethod
    def from_dict(cls, d: JSONDict, **kwargs: Any) -> Self:
        """Constructs an object from a dictionary of fields.

        This may also perform some basic type/validity checking.

        Args:
            d: Dict to convert into an object
            kwargs: Keyword arguments
                - `strict`: if True, raise an error if extraneous dict fields are present

        Returns:
            Converted object of this class"""
        # first establish the type, which may be present in the 'type' field of the dict
        typename = d.get('type')
        if typename is None:  # type field unspecified, so use the calling class
            tp = cls
        else:
            cls_name = fully_qualified_class_name(cls) if ('.' in typename) else cls.__name__
            if cls_name == typename:  # type name already matches this class
                tp = cls
            else:
                # tp must be a subclass of cls
                # the name must be in scope to be found, allowing two alternatives for retrieval:
                # option 1: all subclasses of this DictDataclass are defined in the same module as the base class
                # option 2: the name is fully qualified, so the name can be loaded into scope
                # call from_dict on the subclass in case it has its own custom implementation
                # (remove the type name before passing to the constructor)
                d2 = {key: val for (key, val) in d.items() if (key != 'type')}
                return cls.get_subclass_with_name(typename).from_dict(d2, **kwargs)
        conv = None
        if cls.__settings__.flattened:
            # produce equivalent subfield-flattened type
            settings = copy(tp.__settings__)
            settings.flattened = True
            conv = _flatten_dataclass(tp, cls.__bases__)[1]
            tp = conv.to_type  # type: ignore[assignment]
            tp.__settings__ = settings
        strict = kwargs.get('strict', False)
        result: Self = tp(**tp._dataclass_args_from_dict(d, strict=strict))
        return conv.backward(result) if cls.__settings__.flattened else result  # type: ignore
