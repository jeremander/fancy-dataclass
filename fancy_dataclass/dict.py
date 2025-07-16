from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import suppress
import dataclasses
from dataclasses import Field, InitVar
import types
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Iterable, List, Literal, Optional, Set, Type, TypeVar, Union, _TypedDictMeta, get_args, get_origin  # type: ignore[attr-defined]
import warnings

from typing_extensions import Self, _AnnotatedAlias

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import DocFieldSettings, MixinSettings
from fancy_dataclass.utils import MissingRequiredFieldError, TypeConversionError, check_dataclass, dataclass_field_type, dataclass_kw_only, fully_qualified_class_name, get_dataclass_fields, issubclass_safe, obj_class_name


if TYPE_CHECKING:
    from _typeshed import DataclassInstance

T = TypeVar('T', bound=DataclassMixin)
D = TypeVar('D', bound='DataclassInstance')

_UNION_TYPES = [Union, types.UnionType] if hasattr(types, 'UnionType') else [Union]  # novermin

AnyDict = Dict[str, Any]
# mode for storing data type in dict
StoreTypeMode = Literal['auto', 'off', 'name', 'qualname']


class DictConvertible(ABC):
    """Mixin class enabling conversion of an object to/from a Python dict.

    Subclasses should override `to_dict` and `from_dict` to implement the conversion."""

    @abstractmethod
    def to_dict(self, **kwargs: Any) -> AnyDict:
        """Converts an object to a dict.

        Args:
            kwargs: Keyword arguments

        Returns:
            A Python dict"""

    @classmethod
    @abstractmethod
    def from_dict(cls, d: AnyDict, **kwargs: Any) -> Self:
        """Constructs an object from a dictionary of (attribute, value) pairs.

        Args:
            d: Dict to convert into an object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""


@dataclass_kw_only()
class DictDataclassSettings(MixinSettings):
    """Class-level settings for the [`DictDataclass`][fancy_dataclass.dict.DictDataclass] mixin.

    Subclasses of `DictDataclass` may set the following options as keyword arguments during inheritance:

    - `suppress_defaults`: suppress default values in the dict, by default
    - `suppress_none`: suppress `None` values in the dict, by default
    - `store_type`: whether and how to store the object's type name in its dict, options are:
        - `auto`: base class determines how to store the type
        - `off`: do not store the type
        - `name`: store the type name
        - `qualname`: store the fully qualified type name (easiest way to resolve the type from the dict)
    - `flatten`: if `True`, [`DictDataclass`][fancy_dataclass.dict.DictDataclass] subfields will be merged together with the main fields (provided there are no name collisions); otherwise, they are nested
    - `allow_extra_fields`: if `False`, raise an error when converting from a dict if unknown fields are present
    - `validate`: if `True`, attempt to validate data when converting from a dict"""
    suppress_defaults: bool = True
    suppress_none: bool = False
    store_type: StoreTypeMode = 'auto'
    flattened: Optional[bool] = None  # DEPRECATED
    flatten: bool = False
    strict: Optional[bool] = None  # DEPRECATED
    allow_extra_fields: bool = True
    validate: bool = True

    def __post_init__(self) -> None:
        # validate store_type
        if self.store_type not in get_args(StoreTypeMode):
            raise ValueError(f'invalid value {self.store_type!r} for store_type mode')
        self._store_type = self.store_type  # stores the value where 'auto' has been resolved from base class
        if self.flattened is not None:
            warnings.warn(f"'flattened' is a deprecated field for {self.__class__.__name__}, use 'flatten' instead", DeprecationWarning, stacklevel=2)
            self.flatten = self.flattened
        if self.strict is not None:
            warnings.warn(f"'strict' is a deprecated field for {self.__class__.__name__}, use 'allow_extra_fields' instead", DeprecationWarning, stacklevel=2)
            self.allow_extra_fields = not self.strict

    def should_store_type(self) -> bool:
        """Returns `True` if the type should be stored (qualified or unqualified) in the output dict."""
        return self._store_type in ['name', 'qualname']


@dataclass_kw_only()
class DictDataclassFieldSettings(DocFieldSettings):
    """Settings for [`DictDataclass`][fancy_dataclass.dict.DictDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `suppress`: flag to suppress this field in the dict representation, unconditionally
        - Note: if the field is a class variable, it is excluded by default; you can set `suppress=False` to force the field's inclusion.
        - Note: if set, this will override both `suppress_default` and `suppress_none` (see below)
    - `suppress_default`: flag to suppress this field in the dict if it matches its default value (overrides class-level `suppress_defaults`)
    - `suppress_none`: flag to suppress this field in the dict if its value is `None` (overrides class-level `suppress_none`)
    - `alias`: alternate name to use for the field, both when converting to and from a dict key
    - `flatten`: if set to `True` or `False` and the field is a `DictDataclass`, determines whether to merge subfields into the outer dataclass (this overrides the class-level `flatten` setting)
    - `doc`: a text description of the field, which may be used when generating schemas or serializing the data"""
    suppress: Optional[bool] = None
    suppress_default: Optional[bool] = None
    suppress_none: Optional[bool] = None
    alias: Optional[str] = None
    flatten: Optional[bool] = None


class DictDataclass(DataclassMixin):
    """Mixin class for dataclasses that can be converted to and from a Python dict.

    A subclass may configure settings by using [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings] fields as keyword arguments when inheriting from `DictDataclass`.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`. See [`DictDataclassFieldSettings`][fancy_dataclass.dict.DictDataclassFieldSettings] for the full list of settings."""

    __settings_type__ = DictDataclassSettings
    __settings__ = DictDataclassSettings()
    __field_settings_type__ = DictDataclassFieldSettings

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # if store_type mode is 'auto', use base class to resolve it
        if getattr(cls.__settings__, 'store_type', None) == 'auto':
            for base in cls.mro():
                if issubclass(base, DictDataclass) and (base.__settings__.store_type != 'auto'):
                    cls.__settings__._store_type = base.__settings__.store_type
                    break
            else:  # by default, do not store
                cls.__settings__._store_type = 'off'

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: Type[Self]) -> None:
        # disallow 'type' field when the type needs to be stored in the output dict
        if wrapped_cls.__settings__.should_store_type():
            for fld in dataclasses.fields(wrapped_cls):  # type: ignore[arg-type]
                if fld.name == 'type':
                    raise TypeError(f"'type' is a reserved dict field for {cls.__name__}, cannot be used as dataclass field")
        # prevent field name collisions when using 'alias' setting
        field_names = set()
        for fld in dataclasses.fields(wrapped_cls):  # type: ignore[arg-type]
            settings = cls._field_settings(fld).adapt_to(DictDataclassFieldSettings)
            name = fld.name if (settings.alias is None) else settings.alias
            if name in field_names:
                raise TypeError(f'duplicate field name or alias {name!r}')
            field_names.add(name)

    @classmethod
    def _get_flattened_field_names(cls) -> Set[str]:
        """Gets the set of flattened field names."""
        class_flatten = cls.__settings__.flatten
        fields = dataclasses.fields(cls)  # type: ignore[arg-type]
        flattened_field_names = set()
        for fld in fields:
            settings = cls._field_settings(fld).adapt_to(DictDataclassFieldSettings)
            if issubclass_safe(fld.type, DictDataclass):  # type: ignore[arg-type]
                if class_flatten:
                    flatten_field = settings.flatten is not False
                else:
                    flatten_field = bool(settings.flatten)
                if flatten_field:
                    flattened_field_names.add(fld.name)
            # otherwise, field cannot be flattened, so ignore any flags
        return flattened_field_names

    def _dict_init(self) -> AnyDict:
        """Gets the basic skeleton for a dict generated by this type.
        If `store_type` is `'name'` or `'qualname'`, will include a `type` field to store the type."""
        if self.__settings__._store_type == 'name':
            return {'type': obj_class_name(self)}
        if self.__settings__._store_type == 'qualname':
            return {'type': fully_qualified_class_name(self.__class__)}
        return {}

    @classmethod
    def _to_dict_value_basic(cls, val: Any) -> Any:
        """Converts a value with a basic type to a form appropriate for dict values.

        By default this will return the original value. Subclasses may override the behavior, e.g. to perform custom type coercion."""
        return val

    @classmethod
    def _to_dict_value(cls, val: Any, full: bool) -> Any:
        """Converts an arbitrary value to a form appropriate for dict values.

        This will recursively process values within containers (lists, dicts, etc.)."""
        if isinstance(val, DictDataclass):
            return val.to_dict(full=full)
        if isinstance(val, list):
            return [cls._to_dict_value(elt, full) for elt in val]
        if isinstance(val, tuple):
            return tuple(cls._to_dict_value(elt, full) for elt in val)
        if isinstance(val, dict):
            return {k: cls._to_dict_value(v, full) for (k, v) in val.items()}
        return cls._to_dict_value_basic(val)

    def _to_dict(self, full: bool) -> AnyDict:
        d = self._dict_init()
        class_suppress_none = self.__settings__.suppress_none
        class_suppress_defaults = self.__settings__.suppress_defaults
        flattened_field_names = self._get_flattened_field_names()
        for fld in get_dataclass_fields(self, include_all=True):
            name = fld.name
            is_class_var = get_origin(fld.type) is ClassVar
            settings = self._field_settings(fld).adapt_to(DictDataclassFieldSettings)
            if (should_suppress := settings.suppress) is None:
                # suppress field by default if it is a ClassVar or InitVar or init=False
                should_suppress = is_class_var or isinstance(fld.type, InitVar) or (not fld.init)
            if should_suppress:
                continue
            val = getattr(self, name)
            if (not full) and (settings.suppress is None):
                # suppress None if field specifies it (falling back on class setting)
                if (val is None) and (class_suppress_none if (settings.suppress_none is None) else settings.suppress_none):
                    continue
                # suppress default if field specifies it (falling back on class setting)
                if (class_suppress_defaults if (settings.suppress_default is None) else settings.suppress_default):
                    # suppress values that match the default
                    with suppress(ValueError):  # some types may fail to compare
                        if val == fld.default:
                            continue
                        if (fld.default_factory != dataclasses.MISSING) and (val == fld.default_factory()):
                            continue
            if name in flattened_field_names:
                d2 = val._to_dict(full)
                if 'type' in d2:
                    raise ValueError(f"flattened field {name!r} may not store a 'type' field in dict")
            else:
                key = name if (settings.alias is None) else settings.alias
                d2 = {key: self._to_dict_value(val, full)}
            for (inner_key, inner_val) in d2.items():
                if inner_key in d:
                    raise ValueError(f'duplicate field name or alias {inner_key!r}')
                d[inner_key] = inner_val
        return d

    def to_dict(self, **kwargs: Any) -> AnyDict:
        """Converts the object to a Python dict which, by default, suppresses values matching their dataclass defaults.

        Args:
            kwargs: Keyword arguments <ul><li>`full`: if `True`, does not suppress `None` or default values</li></ul>

        Returns:
            A dict whose keys match the dataclass's fields"""
        full = kwargs.get('full', False)
        return self._to_dict(full)

    @staticmethod
    def _from_dict_value_convertible(tp: Type['DictDataclass'], val: Any) -> Any:
        if isinstance(val, tp):  # already converted from a dict
            return val
        # otherwise, convert from a dict
        return tp.from_dict(val)

    @classmethod
    def _from_dict_value_basic(cls, tp: type, val: Any) -> Any:
        """Given a basic type and a value, attempts to convert the value to the given type.

        By default this will return the original value. Subclasses may override the behavior, e.g. to perform custom validation or type coercion."""
        if cls.__settings__.validate and (not isinstance(val, tp)):  # validate type
            raise TypeConversionError(tp, val)
        # NOTE: alternatively, we could coerce to the type
        # if val is None:  # do not coerce None
        #     raise TypeConversionError(tp, val)
        # try:
        #     return tp(val)  # type: ignore[call-arg]
        # except TypeError as e:
        #     raise TypeConversionError(tp, val) from e
        return val

    @classmethod
    def _from_dict_value(cls, tp: type, val: Any) -> Any:
        """Given a type and a value, attempts to convert the value to the given type."""
        def err() -> TypeConversionError:
            return TypeConversionError(tp, val)
        convert_val = cls._from_dict_value
        if tp is type(None):
            if val is None:
                return None
            raise err()
        if tp in [Any, 'typing.Any']:  # assume basic data type
            return val
        if isinstance(tp, InitVar):
            tp = tp.type
        ttp = type(tp)
        if ttp is _AnnotatedAlias:  # Annotated: just ignore the annotation
            return convert_val(get_args(tp)[0], val)
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
                return val
            if hasattr(tp, 'from_dict'):  # handle nested fields which are themselves convertible from a dict
                return cls._from_dict_value_convertible(tp, val)
            if issubclass(tp, tuple):
                return tp(*val)
            if issubclass(tp, dict):
                if ttp is _TypedDictMeta:  # validate TypedDict fields
                    anns = tp.__annotations__
                    if cls.__settings__.validate and ((not isinstance(val, dict)) or (set(anns) != set(val))):
                        raise err()
                    return {key: convert_val(valtype, val[key]) for (key, valtype) in anns.items()}
                return tp(val)
            # basic data type
            return cls._from_dict_value_basic(tp, val)
        # compound data type
        args = get_args(tp)
        if origin_type is list:
            subtype = args[0]
            return [convert_val(subtype, elt) for elt in val]
        if origin_type is dict:
            (keytype, valtype) = args
            return {convert_val(keytype, k): convert_val(valtype, v) for (k, v) in val.items()}
        if origin_type is tuple:
            subtypes = args
            if subtypes[-1] == Ellipsis:  # treat it like a list
                subtype = subtypes[0]
                return tuple(convert_val(subtype, elt) for elt in val)
            return tuple(convert_val(subtype, elt) for (subtype, elt) in zip(args, val))
        if origin_type in _UNION_TYPES:
            for subtype in args:
                try:
                    # NB: will resolve to the first valid type in the Union
                    return convert_val(subtype, val)
                except Exception:
                    continue
        elif origin_type == Literal:
            if any((val == arg) for arg in args):
                # one of the Literal options is matched
                return val
        elif hasattr(origin_type, 'from_dict'):
            return cls._from_dict_value_convertible(origin_type, val)
        elif issubclass_safe(origin_type, Iterable):  # arbitrary iterable
            subtype = args[0]
            return type(val)(convert_val(subtype, elt) for elt in val)
        raise err()

    @classmethod
    def _get_missing_value(cls, fld: Field) -> Any:  # type: ignore[type-arg]
        settings = cls._field_settings(fld).adapt_to(DictDataclassFieldSettings)
        if settings.alias is None:
            raise MissingRequiredFieldError(fld.name)
        raise MissingRequiredFieldError(fld.name, alias=settings.alias)

    @classmethod
    def _get_field_key_map(cls) -> Dict[str, List[str]]:
        """Gets a dict mapping from field names to the list of corresponding keys to be consumed when converting from a dict."""
        flattened_field_names = cls._get_flattened_field_names()
        field_key_map: Dict[str, List[str]] = defaultdict(list)
        for fld in get_dataclass_fields(cls, include_all=True):
            settings = cls._field_settings(fld).adapt_to(DictDataclassFieldSettings)
            if fld.name in flattened_field_names:
                tp = dataclass_field_type(cls, fld.name)  # type: ignore[arg-type]
                assert issubclass(tp, DictDataclass)
                inner_map = tp._get_field_key_map()
                inner_names = [name for names in inner_map.values() for name in names]
                field_key_map[fld.name].extend(inner_names)
            else:
                key = fld.name if (settings.alias is None) else settings.alias
                field_key_map[fld.name].append(key)
        return field_key_map

    @classmethod
    def dataclass_args_from_dict(cls, d: AnyDict) -> AnyDict:
        """Given a dict of arguments, performs type conversion and/or validity checking, then returns a new dict that can be passed to the class's constructor."""
        check_dataclass(cls)
        kwargs = {}
        bases = cls.mro()
        fields = get_dataclass_fields(cls, include_all=True)
        flattened_field_names = cls._get_flattened_field_names()
        field_key_map = cls._get_field_key_map()
        consumed_keys: Set[str] = set()
        for fld in fields:
            if not fld.init:  # ignore fields where init=False
                continue
            if get_origin(fld.type) is ClassVar:  # ignore ClassVars
                continue
            tp = dataclass_field_type(cls, fld.name)  # type: ignore[arg-type]
            if fld.name in flattened_field_names:
                assert issubclass(tp, DictDataclass)
                d2 = {key: d[key] for key in field_key_map.get(fld.name, []) if (key in d)}
                kwargs[fld.name] = tp.from_dict(d2)
                consumed_keys.update(d2)
            else:
                key = field_key_map[fld.name][0]
                if key in d:
                    # field may be defined in the dataclass itself or one of its ancestor dataclasses
                    for base in bases:
                        with suppress(AttributeError, KeyError):
                            field_type = dataclass_field_type(base, fld.name)
                            kwargs[fld.name] = cls._from_dict_value(field_type, d[key])
                            consumed_keys.add(key)
                            break
                    else:
                        raise ValueError(f'could not locate field {fld.name!r}')
                elif fld.default == dataclasses.MISSING:
                    if fld.default_factory == dataclasses.MISSING:
                        val = cls._get_missing_value(fld)
                    else:
                        val = fld.default_factory()
                        # raise ValueError(f'{fld.name!r} field is required')
                    kwargs[fld.name] = val
        if (not cls.__settings__.allow_extra_fields) and (len(consumed_keys) < len(d)):
            # error if there are unknown fields when they are not allowed
            unknown_fields = [key for key in d if (key not in consumed_keys)]
            raise ValueError(f'unknown dict fields for {cls.__name__}: {unknown_fields!r}')
        return kwargs

    @classmethod
    def _get_type_from_dict(cls, d: AnyDict) -> Type[Self]:
        typename = d.get('type')
        if (typename is None) or ('type' in cls.__dataclass_fields__):  # type: ignore[attr-defined]
            # type field is unspecified *or* 'type' is an expected dataclass field: use the calling class
            return cls
        cls_name = fully_qualified_class_name(cls) if ('.' in typename) else cls.__name__
        if cls_name == typename:  # type name already matches this class
            return cls
        # tp must be a subclass of cls
        # the name must be in scope to be found, allowing two alternatives for retrieval:
        # option 1: all subclasses of this DictDataclass are defined in the same module as the base class
        # option 2: the name is fully qualified, so the name can be loaded into scope
        return cls.get_subclass_with_name(typename)

    @classmethod
    def from_dict(cls, d: AnyDict, **kwargs: Any) -> Self:
        """Constructs an object from a dictionary of fields.

        This may also perform some basic type/validity checking.

        Args:
            d: Dict to convert into an object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        # first establish the type, which may be present in the 'type' field of the dict
        tp = cls._get_type_from_dict(d)
        if tp is not cls:
            # call from_dict on the subclass in case it has its own custom implementation
            # (remove the type name before passing to the constructor)
            d2 = {key: val for (key, val) in d.items() if (key != 'type')}
            return tp.from_dict(d2, **kwargs)
        return tp(**tp.dataclass_args_from_dict(d))
