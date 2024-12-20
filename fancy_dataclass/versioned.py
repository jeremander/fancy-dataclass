from dataclasses import Field, dataclass, field
from typing import Any, Callable, ClassVar, Dict, Optional, Type, TypeVar, cast

from fancy_dataclass.dict import DictDataclass, DictDataclassFieldSettings, DictDataclassSettings
from fancy_dataclass.settings import FieldSettings
from fancy_dataclass.utils import dataclass_kw_only


T = TypeVar('T')
Version = int


###################
# GLOBAL REGISTRY #
###################

@dataclass(frozen=True)
class _VersionedDataclassGroup:
    """Represents a collection of [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] subclasses with the same name but different versions."""
    name: str
    class_by_version: Dict[Version, Type['VersionedDataclass']] = field(default_factory=dict)
    version_by_class: Dict[Type['VersionedDataclass'], Version] = field(default_factory=dict)

    def register_class(self, version: Version, cls: Type['VersionedDataclass']) -> None:
        """Registers a new `VersionedDataclass` subclass with the given version.
        If that version is already registered, or if the same class is already registered, raises a `TypeError`."""
        if not issubclass(cls, VersionedDataclass):
            raise TypeError('class must be a subclass of VersionedDataclass')
        if cls.__name__ != self.name:
            raise TypeError(f'mismatch between group name {self.name!r} and class name {cls.__name__!r}')
        if version in self.class_by_version:
            raise TypeError(f'class already registered with name {self.name!r}, version {version}: {cls.__qualname__}')
        if cls in self.version_by_class:
            ver = self.version_by_class[cls]
            raise TypeError(f'class {cls.__qualname__} is already registered with version {ver}')
        self.class_by_version[version] = cls
        self.version_by_class[cls] = version

    def get_class(self, version: Optional[Version] = None) -> Type['VersionedDataclass']:
        """Gets the [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] subclass with the given version associated with this group.
        If no version is given, uses the latest existing version.
        If no matching version exists, raises a `ValueError."""
        if not self.class_by_version:
            raise ValueError(f'no class registered with name {self.name!r}')
        if version is None:
            version = max(self.class_by_version)
        if version not in self.class_by_version:
            raise ValueError(f'no class registered with name {self.name!r}, version {version}')
        return self.class_by_version[version]


@dataclass(frozen=True)
class _VersionedDataclassRegistry:
    """A registry tracking all subclasses of [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass]."""
    # mapping from class name to the group of all `VersionedDataclass` subclasses with that name
    # NOTE: the names are *not* qualified, which allows classes in different modules to belong to the same group
    groups_by_name: Dict[str, _VersionedDataclassGroup] = field(default_factory=dict)

    def register_class(self, version: Version, cls: Type['VersionedDataclass']) -> None:
        """Registers a new `VersionedDataclass` subclass with the given version.
        If that version is already registered, raises a `TypeError`."""
        if not issubclass(cls, VersionedDataclass):
            raise TypeError('class must be a subclass of VersionedDataclass')
        name = cls.__name__
        group = self.groups_by_name.setdefault(name, _VersionedDataclassGroup(name))
        group.register_class(version, cls)

    def get_class(self, name: str, version: Optional[Version] = None) -> Type['VersionedDataclass']:
        """Gets the [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] subclass with the given name and version.
        If no version is given, uses the latest version in the registry.
        If no matching class exists, raises a `ValueError."""
        if name not in self.groups_by_name:
            raise ValueError(f'no class registered with name {name!r}')
        group = self.groups_by_name[name]
        return group.get_class(version=version)


# global registry
_VERSIONED_DATACLASS_REGISTRY = _VersionedDataclassRegistry()


#######################
# VERSIONED DATACLASS #
#######################

@dataclass_kw_only()
class VersionedDataclassSettings(DictDataclassSettings):
    """Class-level settings for the [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] mixin.

    Subclasses of `VersionedDataclass` should set the `version` field to an integer value indicating the version.

    Additionally they may set the following options as keyword arguments during inheritance:

    - `suppress_version`: suppress version field when converting to a dict"""
    version: Optional[Version] = None
    suppress_version: bool = False


@dataclass
class VersionedDataclass(DictDataclass):
    """Mixin class that ensures a `version` integer is associated with a given `dataclass` type.

    This enables reliable migration between different versions of the "same" class.

    This class also inherits from [`DictDataclass`](fancy_dataclass.dict.DictDataclass], providing support for dict conversion, where by default the `version` field will be included in the dict representation."""
    __settings_type__ = VersionedDataclassSettings
    __settings__ = VersionedDataclassSettings()

    version: ClassVar[Version]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        version = getattr(cls, 'version', cls.__settings__.version)
        if not isinstance(version, int):
            raise TypeError(f'must supply an integer `version` attribute for class {cls.__name__!r}')
        if 'version' not in cls.__dataclass_fields__:
            # if subclass gets generated dynamically, it might not have a 'version' ClassVar field, so create it
            cls.__dataclass_fields__['version'] = VersionedDataclass.__dataclass_fields__['version']
        cls.version = version

    @classmethod
    def _field_settings(cls, fld: Field) -> FieldSettings:  # type: ignore[type-arg]
        """Gets the class-specific FieldSettings extracted from the metadata stored on a Field object."""
        settings = cast(DictDataclassFieldSettings, super()._field_settings(fld))
        if (fld.name == 'version') and (cls.__settings__.suppress_version is False):
            # do not suppress version field if class-level suppress_version=False
            settings.suppress = False
        return settings

    def __setattr__(self, name: str, value: Any) -> None:
        # make 'version' field read-only
        if name == 'version':
            raise AttributeError("cannot assign to field 'version'")
        super().__setattr__(name, value)


def version(version: int, suppress_version: bool = False) -> Callable[[Type[T]], Type[T]]:
    """Decorator turning a regular dataclass into a [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass].

    Args:
        version: Version number associated with the class
        suppress_version: W
        typename: Name of subclass

    Returns:
        Decorator to wrap a `dataclass` into a `VersionedDataclass`"""
    def _wrap_dataclass(tp: Type[T]) -> Type[T]:
        return VersionedDataclass.wrap_dataclass(tp, version=version, suppress_version=suppress_version)  # type: ignore[return-value]
    return _wrap_dataclass
