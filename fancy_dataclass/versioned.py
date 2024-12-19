from dataclasses import Field, dataclass
from typing import Any, Callable, ClassVar, Optional, Type, TypeVar, cast

from fancy_dataclass.dict import DictDataclass, DictDataclassFieldSettings, DictDataclassSettings
from fancy_dataclass.settings import FieldSettings
from fancy_dataclass.utils import dataclass_kw_only


T = TypeVar('T')


@dataclass_kw_only()
class VersionedDataclassSettings(DictDataclassSettings):
    """Class-level settings for the [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] mixin.

    Subclasses of `VersionedDataclass` should set the `version` field to an integer value indicating the version.

    Additionally they may set the following options as keyword arguments during inheritance:

    - `suppress_version`: suppress version field when converting to a dict"""
    version: Optional[int] = None
    suppress_version: bool = False


@dataclass
class VersionedDataclass(DictDataclass):
    """Mixin class that ensures a `version` integer is associated with a given `dataclass` type.

    This enables reliable migration between different versions of the "same" class.

    This class also inherits from [`DictDataclass`](fancy_dataclass.dict.DictDataclass], providing support for dict conversion, where by default the `version` field will be included in the dict representation."""
    __settings_type__ = VersionedDataclassSettings
    __settings__ = VersionedDataclassSettings()

    version: ClassVar[int]

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

# example usage:
# @version(5)
# @dataclass
# class A:
#     x: int = 1
