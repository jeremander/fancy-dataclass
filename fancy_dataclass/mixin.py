from collections.abc import Iterable
from contextlib import suppress
import dataclasses
from functools import cache
from typing import Any, ClassVar, Optional, TypeVar
from weakref import WeakKeyDictionary

from typing_extensions import Self

from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import (
    check_dataclass,
    get_dataclass_fields,
    get_subclass_with_name,
    issubclass_safe,
    merge_dataclasses,
    obj_class_name,
)


T = TypeVar('T')

_orig_process_class = dataclasses._process_class  # type: ignore[attr-defined]

def _process_class(cls: type, *args: Any) -> type:
    """Overrides `dataclasses._process_class` to activate a special `__post_dataclass_wrap__` classmethod after the
    `dataclasses.dataclass` decorator wraps a class."""
    cls = _orig_process_class(cls, *args)
    for tp in cls.mro()[::-1]:
        # call __post_dataclass_wrap__ on all base classes to deal with multiple inheritance
        if hasattr(tp, '__post_dataclass_wrap__'):
            tp.__post_dataclass_wrap__(cls)
    return cls

# monkey-patch dataclasses._process_class with this function so that any DataclassMixin will be able to activate its
# post-wrap hook
dataclasses._process_class = _process_class  # type: ignore[attr-defined]


def _reconcile_base_dataclasses(bases: Iterable[type]) -> None:
    """Given a list of base classes for a dataclass type, checks if there are any fields with duplicate names across
    different classes (other than shared by ancestry).

    If there are, raises a TypeError."""
    flds = []
    field_type_map: dict[str, Any] = {}
    base_map: dict[str, type] = {}
    @cache
    def _get_field_names(tp: type) -> set[str]:
        return {fld.name for fld in get_dataclass_fields(tp, include_all=True)}
    def _base_type_with_field(cls: type, name: str) -> type:
        for tp in cls.mro()[::-1]:
            with suppress(TypeError):
                if name in _get_field_names(tp):
                    return tp
        raise TypeError(f'no field named {name!r} for {cls}')
    for cls in bases:
        for fld in get_dataclass_fields(cls, include_all=True):
            base = _base_type_with_field(cls, fld.name)
            if fld.name in field_type_map:
                # allow duplicate field if it came from the same ancestor class
                if base != base_map[fld.name]:
                    raise TypeError(f'duplicate field name {fld.name!r}')
            else:
                field_type_map[fld.name] = fld.type
                base_map[fld.name] = base
                flds.append((fld.name, fld.type, fld))


############
# SETTINGS #
############

def _get_settings_type(cls: type) -> Optional[type[MixinSettings]]:
    """Gets the value of the __settings_type__ field of a class, if it is defined specifically on that class
    (not inherited from a base class)."""
    # TODO: check this is a subclass of MixinSettings?
    return cls.__dict__.get('__settings_type__')

def _configure_mixin_settings(cls: type['DataclassMixin'], **kwargs: Any) -> None:
    """Sets up a `DataclassMixin`'s settings (at definition time), given inheritance kwargs."""
    # get user-specified settings (need to use __dict__ here rather than direct access,
    # which inherits parent class's value)
    pairs: list[tuple[type, type[MixinSettings]]] = []
    if (stype := _get_settings_type(cls)):
        assert check_dataclass(stype)
        if not issubclass(stype, MixinSettings):
            raise TypeError(f'invalid settings type {stype.__name__} for {cls.__name__}')
        pairs.append((cls, stype))
    else:
        cls.__settings_type__ = None
    settings_kwargs = cls.__settings_kwargs__ = {}
    if (settings := cls.__dict__.get('__settings__')) is None:
        cls.__settings__ = None
    else:
        # explicit __settings__ will get overridden by kwargs
        if not dataclasses.is_dataclass(settings):
            raise TypeError(f'invalid __settings__ type {type(settings).__name__} for {cls.__name__}')
        d = dataclasses.asdict(settings)  # type: ignore[arg-type]
        for name in d:
            if name in kwargs:
                raise TypeError(f'redundant specification of field {name!r} for {cls.__name__}')
        settings_kwargs.update(d)
    # inherit kwargs from the parent classes, with nearer ones in the inheritance chain taking priority
    for base in cls.mro()[::-1]:
        if (stype := _get_settings_type(base)) and issubclass_safe(stype, MixinSettings):
            pairs.append((base, stype))
        settings_kwargs.update(getattr(base, '__settings_kwargs__', None) or {})
    settings_map: WeakKeyDictionary[type, MixinSettings] = WeakKeyDictionary()
    if pairs:
        stypes = [stype for (_, stype) in pairs]
        try:
            _reconcile_base_dataclasses(stypes)
        except TypeError as e:
            raise TypeError(f'error reconciling base class settings for {cls.__name__}: {e}') from e
    # this class's kwargs take priority over the parent classes'
    settings_kwargs.update(kwargs)
    settings_map = WeakKeyDictionary()
    field_names = set()
    for (base, stype) in pairs:
        d = {}
        for fld in get_dataclass_fields(stype, include_all=True):
            if (name := fld.name) in settings_kwargs:
                d[name] = settings_kwargs[name]
                field_names.add(name)
        settings_map[base] = stype(**d)
    for name in kwargs:
        if name not in field_names:
            raise TypeError(f'unknown settings field {name!r} for {cls.__name__}')
    cls.__settings_map__ = settings_map

def _configure_field_settings_type(cls: type['DataclassMixin']) -> None:
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

def _check_field_settings(cls: type['DataclassMixin']) -> None:
    """Performs type checking of a `DataclassMixin`'s fields to catch any errors at dataclass-wrap time."""
    if (stype := cls.__field_settings_type__) is not None:
        for fld in dataclasses.fields(cls):  # type: ignore[arg-type]
            _ = stype.from_field(fld)


###################
# DATACLASS MIXIN #
###################

class DataclassMixin:
    """Mixin class for adding some kind functionality to a dataclass.

    For example, this could provide features for conversion to/from JSON
    ([`JSONDataclass`][fancy_dataclass.json.JSONDataclass]), the ability to construct CLI argument parsers
    ([`CLIDataclass`][fancy_dataclass.cli.CLIDataclass]), etc.

    This mixin also provides a [`wrap_dataclass`][fancy_dataclass.mixin.DataclassMixin.wrap_dataclass] decorator which
    can be used to wrap an existing dataclass type into one that provides the mixin's functionality."""

    __settings_type__: ClassVar[Optional[type[MixinSettings]]] = None
    __settings__: ClassVar[Optional[MixinSettings]] = None
    __settings_kwargs__: ClassVar[Optional[dict[str, Any]]] = None
    __settings_map__: ClassVar[WeakKeyDictionary[type, MixinSettings]]
    __field_settings_type__: ClassVar[Optional[type[FieldSettings]]] = None

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """When inheriting from this class, you may pass various keyword arguments after the list of base classes.

        If the base class has a `__settings_type__` class attribute (subclass of
        [`MixinSettings`][fancy_dataclass.settings.MixinSettings]), that class will be instantiated with the provided
        arguments and stored as a `__settings__` attribute on the subclass.
        These settings can be used to customize the behavior of the subclass.

        Additionally, the mixin may set the `__field_settings_type__` class attribute to indicate the type
        (subclass of [`FieldSettings`][fancy_dataclass.settings.FieldSettings]) that should be used for field settings,
        which are extracted from each field's `metadata` dict."""
        super().__init_subclass__()
        _configure_mixin_settings(cls, **kwargs)
        _configure_field_settings_type(cls)

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: type[Self]) -> None:
        """A hook that is called after the
        [`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass) decorator
        is applied to the mixin subclass.

        This can be used, for instance, to validate the dataclass fields at definition time.

        NOTE: this function should be _idempotent_, meaning it can be called multiple times with the same effect.
        This is because it will be called for every base class of the `dataclass`-wrapped class, which may result in
        duplicate calls.

        Args:
            wrapped_cls: Class wrapped by the `dataclass` decorator"""
        _check_field_settings(wrapped_cls)

    @classmethod
    def _class_settings(cls, *, base: Optional[type['DataclassMixin']] = None) -> MixinSettings:
        base = cls if (base is None) else base
        if base not in cls.__settings_map__:
            raise TypeError(f'could not get class settings for {cls.__name__}, base {base.__name__}')
        return cls.__settings_map__[base]

    @classmethod
    def _field_settings(cls, fld: dataclasses.Field[Any]) -> FieldSettings:
        """Gets the class-specific FieldSettings extracted from the metadata stored on a Field object."""
        stype = cls.__field_settings_type__ or FieldSettings
        return stype.from_field(fld)

    @classmethod
    def wrap_dataclass(cls: type[Self], tp: type[T], **kwargs: Any) -> type[Self]:
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
            # preserve the original
            d = {'__module__': tp.__module__, '__qualname__': tp.__qualname__}
            return type(tp.__name__, (tp, cls), d, **kwargs)
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
    def get_subclass_with_name(cls, typename: str) -> type[Self]:
        """Gets the subclass of this class with the given name.

        Args:
            typename: Name of subclass

        Returns:
            Subclass with the given name

        Raises:
            TypeError: If no subclass with the given name exists"""
        return get_subclass_with_name(cls, typename)
