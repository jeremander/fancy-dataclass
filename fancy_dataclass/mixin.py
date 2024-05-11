import dataclasses
from typing import Any, ClassVar, Optional, Type, TypeVar

from typing_extensions import Self

from fancy_dataclass.utils import _is_instance, check_dataclass, coerce_to_dataclass, get_dataclass_fields, get_subclass_with_name, merge_dataclasses, obj_class_name


T = TypeVar('T')
DA = TypeVar('DA', bound='DataclassAdaptable')

_orig_process_class = dataclasses._process_class  # type: ignore[attr-defined]

def _process_class(cls: type, *args: Any) -> type:
    """Overrides `dataclasses._process_class` to activate a special `__post_dataclass_wrap__` classmethod after the `dataclasses.dataclass` decorator wraps a class."""
    cls = _orig_process_class(cls, *args)
    for tp in cls.mro()[::-1]:
        # call __post_dataclass_wrap__ on all base classes to deal with multiple inheritance
        if hasattr(tp, '__post_dataclass_wrap__'):
            tp.__post_dataclass_wrap__(cls)
    return cls

# monkey-patch dataclasses._process_class with this function so that any DataclassMixin will be able to activate its post-wrap hook
dataclasses._process_class = _process_class  # type: ignore[attr-defined]


############
# SETTINGS #
############

class DataclassAdaptable:
    """Mixin class providing the ability to convert (adapt) one dataclass type to another."""

    @classmethod
    def coerce(cls, obj: object) -> Self:
        """Constructs a `DataclassAdaptable` object from the attributes of an arbitrary object.

        Any missing attributes will be set to their default values."""
        return coerce_to_dataclass(cls, obj)

    def adapt_to(self, dest_type: Type[DA]) -> DA:
        """Converts a `DataclassAdaptable` object to another type, `dest_type`.

        By default this will attempt to coerce the fields from the original type to the new type, but subclasses may override the behavior, e.g. to allow field renaming."""
        return dest_type.coerce(self)


class DataclassMixinSettings(DataclassAdaptable):
    """Base class for settings to be associated with `fancy_dataclass` mixins.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__settings_type__` attribute consisting of a subclass of this class. The settings object will be instantiated as a `__settings__` attribute on a mixin subclass when it is defined."""


class FieldSettings(DataclassAdaptable):
    """Class storing a bundle of parameters that will be extracted from dataclass field metadata.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__field_settings_type__` attribute which is a `FieldSettings` subclass. This specifies which keys in the `field.metadata` dictionary are recognized by the mixin class. Other keys will be ignored (unless they are used by other mixin classes)."""

    def type_check(self) -> None:
        """Checks that every field on the `FieldSettings` object is the proper type.

        Raises:
            TypeError: If a field is the wrong type"""
        for fld in dataclasses.fields(self):  # type: ignore[arg-type]
            val = getattr(self, fld.name)
            # semi-robust type checking (could still be improved)
            if not _is_instance(val, fld.type):
                raise TypeError(f'expected type {fld.type} for field {fld.name!r}, got {type(val)}')

    @classmethod
    def from_field(cls, field: dataclasses.Field) -> Self:  # type: ignore[type-arg]
        """Constructs a `FieldSettings` object from a [`dataclasses.Field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.Field)'s metadata.

        Raises:
            TypeError: If any field has the wrong type"""
        assert check_dataclass(cls)
        obj: Self = cls(**{key: val for (key, val) in field.metadata.items() if key in cls.__dataclass_fields__})  # type: ignore[assignment]
        obj.type_check()
        return obj


def _configure_mixin_settings(cls: Type['DataclassMixin'], **kwargs: Any) -> None:
    """Sets up a `DataclassMixin`'s settings (at definition time), given inheritance kwargs."""
    # get user-specified settings (need to use __dict__ here rather than direct access, which inherits parent class's value)
    stype = cls.__dict__.get('__settings_type__')
    settings = cls.__dict__.get('__settings__')
    cls.__settings_kwargs__ = {**getattr(cls, '__settings_kwargs__', {}), **kwargs}  # type: ignore[attr-defined]
    if stype is None:  # merge settings types of base classes
        stypes = [stype for base in cls.__bases__ if (stype := getattr(base, '__settings_type__', None))]
        # remove duplicate settings classes
        stypes = list(dict.fromkeys(stypes))
        if stypes:
            try:
                stype = stypes[0] if (len(stypes) == 1) else merge_dataclasses(*stypes, cls_name='MiscDataclassSettings')
            except TypeError as e:
                raise TypeError(f'error merging base class settings for {cls.__name__}: {e}') from e
            cls.__settings_type__ = stype
    else:
        if not issubclass(stype, DataclassMixinSettings):
            raise TypeError(f'invalid settings type {stype.__name__} for {cls.__name__}')
        assert check_dataclass(stype)
    field_names = set() if (stype is None) else {fld.name for fld in dataclasses.fields(stype)}
    d = {}
    for (key, val) in cls.__settings_kwargs__.items():  # type: ignore[attr-defined]
        if key in field_names:
            d[key] = val
        else:
            raise TypeError(f'unknown settings field {key!r} for {cls.__name__}')
    # explicit settings will override inheritance kwargs
    if settings is not None:
        # make sure user-configured settings type has all required fields
        for fld in get_dataclass_fields(stype):
            name = fld.name
            if stype and (not hasattr(settings, name)):
                raise TypeError(f'settings for {cls.__name__} missing expected field {name!r}')
            if name in kwargs:  # disallow kwarg specification alongside __settings__ specification
                raise TypeError(f'redundant specification of field {name!r} for {cls.__name__}')
            d[name] = getattr(settings, name)
    if stype is not None:
        cls.__settings__ = stype(**d)

def _configure_field_settings_type(cls: Type['DataclassMixin']) -> None:
    """Sets up the __field_settings_type__ attribute on a `DataclassMixin` subclass at definition time.
    This reconciles any such attributes inherited from multiple parent classes."""
    stype = cls.__dict__.get('__field_settings_type__')
    if stype is None:
        stypes = [stype for base in cls.__bases__ if (stype := getattr(base, '__field_settings_type__', None))]
        # remove duplicate settings classes
        stypes = list(dict.fromkeys(stypes))
        if stypes:
            stype = stypes[0] if (len(stypes) == 1) else merge_dataclasses(*stypes, cls_name='MiscFieldSettings')
            cls.__field_settings_type__ = stype
    else:
        if not issubclass(stype, FieldSettings):
            raise TypeError(f'invalid field settings type {stype.__name__} for {cls.__name__}')
        assert check_dataclass(stype)

def _check_field_settings(cls: Type['DataclassMixin']) -> None:
    """Performs type checking of a `DataclassMixin`'s fields to catch any errors at dataclass-wrap time."""
    if (stype := cls.__field_settings_type__) is not None:
        for fld in dataclasses.fields(cls):  # type: ignore[arg-type]
            _ = stype.from_field(fld)


###################
# DATACLASS MIXIN #
###################

class DataclassMixin:
    """Mixin class for adding some kind functionality to a dataclass.

    For example, this could provide features for conversion to/from JSON ([`JSONDataclass`][fancy_dataclass.json.JSONDataclass]), the ability to construct CLI argument parsers ([`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass]), etc.

    This mixin also provides a [`wrap_dataclass`][fancy_dataclass.mixin.DataclassMixin.wrap_dataclass] decorator which can be used to wrap an existing dataclass type into one that provides the mixin's functionality."""

    __settings_type__: ClassVar[Optional[Type[DataclassMixinSettings]]] = None
    __settings__: ClassVar[Optional[DataclassMixinSettings]] = None
    __field_settings_type__: ClassVar[Optional[Type[FieldSettings]]] = None

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """When inheriting from this class, you may pass various keyword arguments after the list of base classes.

        If the base class has a `__settings_type__` class attribute (subclass of [`DataclassMixinSettings`][fancy_dataclass.mixin.DataclassMixinSettings]), that class will be instantiated with the provided arguments and stored as a `__settings__` attribute on the subclass. These settings can be used to customize the behavior of the subclass.

        Additionally, the mixin may set the `__field_settings_type__` class attribute to indicate the type (subclass of [`FieldSettings`][fancy_dataclass.mixin.FieldSettings]) that should be used for field settings, which are extracted from each field's `metadata` dict."""
        super().__init_subclass__()
        _configure_mixin_settings(cls, **kwargs)
        _configure_field_settings_type(cls)

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: Type[Self]) -> None:
        """A hook that is called after the [`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass) decorator is applied to the mixin subclass.

        This can be used, for instance, to validate the dataclass fields at definition time.

        NOTE: this function should be _idempotent_, meaning it can be called multiple times with the same effect. This is because it will be called for every base class of the `dataclass`-wrapped class, which may result in duplicate calls.

        Args:
            wrapped_cls: Class wrapped by the `dataclass` decorator"""
        _check_field_settings(wrapped_cls)

    @classmethod
    def _field_settings(cls, field: dataclasses.Field) -> FieldSettings:  # type: ignore[type-arg]
        """Gets the class-specific FieldSettings extracted from the metadata stored on a Field object."""
        stype = cls.__field_settings_type__ or FieldSettings
        return stype.from_field(field)

    @classmethod
    def wrap_dataclass(cls: Type[Self], tp: Type[T], **kwargs: Any) -> Type[Self]:
        """Wraps a dataclass type into a new one which inherits from this mixin class and is otherwise the same.

        Args:
            tp: A dataclass type
            kwargs: Keyword arguments to type constructor

        Returns:
            New dataclass type inheriting from the mixin

        Raises:
            TypeError: If the given type is not a dataclass"""
        check_dataclass(tp)
        if issubclass(tp, cls):  # the type is already a subclass of this one, so just return it
            return tp
        # otherwise, create a new type that inherits from this class
        try:
            return type(tp.__name__, (tp, cls), {}, **kwargs)
        except TypeError as e:
            if 'Cannot create a consistent' in str(e):
                # try the opposite order of inheritance
                return type(tp.__name__, (cls, tp), {}, **kwargs)
            raise

    def _replace(self, **kwargs: Any) -> Self:
        """Constructs a new object with the provided fields modified.

        Args:
            **kwargs: Dataclass fields to modify

        Returns:
            New object with selected fields modified

        Raises:
            TypeError: If an invalid dataclass field is provided"""
        assert hasattr(self, '__dataclass_fields__'), f'{obj_class_name(self)} is not a dataclass type'
        d = {fld.name: getattr(self, fld.name) for fld in dataclasses.fields(self)}  # type: ignore[arg-type]
        for (key, val) in kwargs.items():
            if key in d:
                d[key] = val
            else:
                raise TypeError(f'{key!r} is not a valid field for {obj_class_name(self)}')
        return self.__class__(**d)

    @classmethod
    def get_subclass_with_name(cls, typename: str) -> Type[Self]:
        """Gets the subclass of this class with the given name.

        Args:
            typename: Name of subclass

        Returns:
            Subclass with the given name

        Raises:
            TypeError: If no subclass with the given name exists"""
        return get_subclass_with_name(cls, typename)
