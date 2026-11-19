from collections.abc import Iterable, Mapping
from contextlib import suppress
import dataclasses
from functools import cache
from typing import Any, ClassVar, Optional, TypeVar, cast
from weakref import WeakKeyDictionary

from typing_extensions import Self

from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import (
    check_dataclass,
    get_dataclass_fields,
    get_subclass_with_name,
    issubclass_safe,
    obj_class_name,
)


T = TypeVar('T')

_orig_process_class = dataclasses._process_class  # type: ignore[attr-defined]

def _process_class(cls: type, *args: Any) -> type:
    """Overrides `dataclasses._process_class` to activate a special `__post_dataclass_wrap__` classmethod after the
    `dataclasses.dataclass` decorator wraps a class."""
    cls = _orig_process_class(cls, *args)
    if issubclass(cls, DataclassMixin):
        cls.__post_dataclass_wrap__()
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
    if (tp := cls.__dict__.get('__settings_type__')) and (not issubclass_safe(tp, MixinSettings)):
        raise TypeError(f'{cls.__name__}.__settings_type__ should be a subclass of MixinSettings')
    return tp

def _update_settings_kwargs(
    cls: type['DataclassMixin'],
    settings_kwargs: dict[str, Any],
    settings_type: Optional[type[MixinSettings]],
    settings: MixinSettings,
) -> None:
    if settings_type is None:
        raise TypeError(f'{cls.__name__}.__settings__ requires __settings_type__ to also be defined')
    if not isinstance(settings, settings_type):
        raise TypeError(f'{cls.__name__}.__settings__ should be an instance of {settings_type.__name__}')
    if not dataclasses.is_dataclass(settings):
        raise TypeError(f'{cls.__name__}.__settings__ should be a dataclass')
    d = dataclasses.asdict(settings)  # pyrefly: ignore[bad-argument-type]
    for name in d:
        if name in settings_kwargs:
            raise TypeError(f'redundant specification of field {name!r} for {cls.__name__}')
    settings_kwargs.update(d)

def _make_settings_map(
    pairs: Iterable[tuple[type, type[MixinSettings]]],
    settings_kwargs: dict[str, Any],
) -> tuple[WeakKeyDictionary[type, MixinSettings], set[str]]:
    settings_map: WeakKeyDictionary[type, MixinSettings] = WeakKeyDictionary()
    field_names = set()
    for (base, stype) in pairs:
        d = {}
        for fld in get_dataclass_fields(stype, include_all=True):
            if (name := fld.name) in settings_kwargs:
                d[name] = settings_kwargs[name]
                field_names.add(name)
        settings_map[base] = stype(**d)
    return (settings_map, field_names)

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
        _update_settings_kwargs(cls, kwargs, stype, settings)
    # inherit kwargs from the parent classes, with nearer ones in the inheritance chain taking priority
    for base in cls.mro()[::-1]:
        if (stype := _get_settings_type(base)) and issubclass_safe(stype, MixinSettings):
            pairs.append((base, stype))
        settings_kwargs.update(getattr(base, '__settings_kwargs__', None) or {})
    # this class's kwargs take priority over the parent classes'
    settings_kwargs.update(kwargs)
    if pairs:
        stypes = [stype for (_, stype) in pairs]
        try:
            _reconcile_base_dataclasses(stypes)
        except TypeError as e:
            raise TypeError(f'error reconciling base class settings for {cls.__name__}: {e}') from e
    (settings_map, field_names) = _make_settings_map(pairs, settings_kwargs)
    for name in kwargs:
        if name not in field_names:
            raise TypeError(f'unknown settings field {name!r} for {cls.__name__}')
    cls.__settings_map__ = settings_map

def _get_field_settings_type(cls: type) -> Optional[type[FieldSettings]]:
    """Gets the value of the __field_settings_type__ field of a class, if it is defined specifically on that class
    (not inherited from a base class)."""
    if (tp := cls.__dict__.get('__field_settings_type__')) and (not issubclass_safe(tp, FieldSettings)):
        raise TypeError(f'{cls.__name__}.__field_settings_type__ should be a subclass of FieldSettings')
    return tp

def _configure_field_settings(cls: type['DataclassMixin']) -> None:
    """Sets up a `DataclassMixin`'s field settings (called at dataclass wrap time)."""
    settings_map: WeakKeyDictionary[type, dict[str, FieldSettings]] = WeakKeyDictionary()
    assert check_dataclass(cls)
    fields = list(get_dataclass_fields(cls, include_all=True))
    for base in [cls] + cls.mro()[::-1]:
        if (stype := _get_field_settings_type(base)) is None:
            continue
        d = {}
        for fld in fields:
            d[fld.name] = stype.from_field(fld)
        settings_map[base] = d
    cls.__field_settings_map__ = settings_map  # type: ignore[attr-defined]


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
    __field_settings_map__: ClassVar[WeakKeyDictionary[type, dict[str, FieldSettings]]]

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
        # erase parent class's __field_settings_type__ attribute
        if _get_field_settings_type(cls) is None:
            cls.__field_settings_type__ = None

    @classmethod
    def __post_dataclass_wrap__(cls) -> None:
        """A hook that is called after the
        [`dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass) decorator
        is applied to the mixin subclass.

        This can be used, for instance, to validate the dataclass fields at definition time, as in
        [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass]."""
        _configure_field_settings(cls)

    @classmethod
    def _class_settings(cls, *, base: Optional[type['DataclassMixin']] = None) -> MixinSettings:
        """Gets the class-specific MixinSettings for the given base class."""
        base = cls if (base is None) else base
        if base not in cls.__settings_map__:
            raise TypeError(f'could not get class settings for {cls.__name__}, base {base.__name__}')
        return cls.__settings_map__[base]

    @classmethod
    def _field_settings(cls, name: str, *, base: Optional[type['DataclassMixin']] = None) -> FieldSettings:
        """Gets the class-specific FieldSettings extracted from the metadata associated with the dataclass field
        of the given name and base class."""
        base = cls if (base is None) else base
        field_settings_map = cast(Mapping[type, dict[str, FieldSettings]], getattr(cls, '__field_settings_map__', {}))
        if (d := field_settings_map.get(base)) is None:
            raise TypeError(f'could not get field settings for {cls.__name__}, base {base.__name__}')
        if name not in d:
            raise ValueError(f'field {name!r} does not exist for {cls.__name__}')
        return d[name]

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
            return dataclasses.dataclass(type(tp.__name__, (tp, cls), d, **kwargs))
        except TypeError as e:
            if 'Cannot create a consistent' in str(e):
                # try the opposite order of inheritance
                return dataclasses.dataclass(type(tp.__name__, (cls, tp), {}, **kwargs))
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
