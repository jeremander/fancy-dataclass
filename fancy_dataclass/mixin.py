import dataclasses
from typing import Any, ClassVar, Optional, Type, TypeVar

from typing_extensions import Self

from fancy_dataclass.utils import check_dataclass, get_dataclass_fields, get_subclass_with_name, merge_dataclasses, obj_class_name


T = TypeVar('T')


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
        """When inheriting from this class, you may pass various keyword arguments after the list of base classes.
        If the base class has a `__settings_type__` class attribute, that class will be instantiated with the provided arguments and stored as a `__settings__` attribute on the subclass.
        These settings can be used to customize the behavior of the subclass."""
        super().__init_subclass__()
        # get user-specified settings (need to use __dict__ here rather than direct access, which inherits parent class's value)
        stype = cls.__dict__.get('__settings_type__')
        settings = cls.__dict__.get('__settings__')
        cls.__settings_kwargs__ = {**getattr(cls, '__settings_kwargs__', {}), **kwargs}  # type: ignore[attr-defined]
        if stype is None:  # merge settings types of base classes
            stypes = [stype for base in cls.__bases__ if (stype := getattr(base, '__settings_type__', None))]
            # remove duplicate settings classes
            stypes = list(dict.fromkeys(stypes))
            if stypes:
                stype = stypes[0] if (len(stypes) == 1) else merge_dataclasses(*stypes, cls_name='MiscDataclassSettings')
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
