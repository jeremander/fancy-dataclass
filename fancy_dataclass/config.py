from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import is_dataclass, make_dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterator, Optional, Type

from typing_extensions import Self

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.serialize import FileSerializable
from fancy_dataclass.utils import AnyPath, coerce_to_dataclass, dataclass_type_map, get_dataclass_fields


class Config:
    """Base class for storing a collection of configurations.

    Subclasses may store a class attribute, `_config`, with the current global configurations, which can be retrieved or updated by the user."""

    _config: ClassVar[Optional[Self]] = None

    @classmethod
    def get_config(cls) -> Optional[Self]:
        """Gets the current global configuration.

        Returns:
            Global configuration object (`None` if not set)"""
        # return deepcopy(cls._config)  # type: ignore[return-value]
        return cls._config  # type: ignore[return-value]

    @classmethod
    def _set_config(cls, config: Optional[Self]) -> None:
        """Sets the global configuration to a given value."""
        # NOTE: this is private to avoid confusion with update_config
        cls._config = config

    @classmethod
    def clear_config(cls) -> None:
        """Clears the global configuration by setting it to `None`."""
        cls._set_config(None)

    def update_config(self) -> None:
        """Updates the global configuration, setting it equal to this object."""
        type(self)._set_config(self)

    @contextmanager
    def as_config(self) -> Iterator[None]:
        """Context manager which temporarily updates the global configuration with this object."""
        try:
            orig_config = type(self).get_config()
            self.update_config()
            yield
        finally:
            type(self)._set_config(orig_config)


class FileConfig(Config, ABC):
    """A collection of configurations that can be loaded from a file."""

    @classmethod
    @abstractmethod
    def load_config(cls, path: AnyPath) -> Self:
        """Loads configurations from a file and sets them to be the global configurations for this class.

        Args:
            path: File from which to load configurations

        Returns:
            The newly loaded global configurations"""


def _get_dataclass_type_for_path(path: AnyPath) -> Type[FileSerializable]:
    p = Path(path)
    if not p.suffix:
        raise ValueError(f'filename {p} has no extension')
    ext_lower = p.suffix.lower()
    if ext_lower == '.json':
        from fancy_dataclass.json import JSONDataclass
        return JSONDataclass
    if ext_lower == '.toml':
        from fancy_dataclass.toml import TOMLDataclass
        return TOMLDataclass
    raise ValueError(f'unknown config file extension {p.suffix!r}')


class ConfigDataclass(DictDataclass, FileConfig, suppress_defaults=False):
    """A dataclass representing a collection of configurations.

    The configurations can be loaded from a file, the type of which will be inferred from its extension.
    Supported file types are:

    - JSON
    - TOML
    """

    @staticmethod
    def _wrap_config_dataclass(mixin_cls: Type[DataclassMixin], cls: Type['ConfigDataclass']) -> Type[DataclassMixin]:
        """Recursively wraps a DataclassMixin class around a ConfigDataclass so that nested dataclass fields inherit from the same mixin."""
        def _wrap(tp: type) -> type:
            if is_dataclass(tp):
                wrapped_cls = mixin_cls.wrap_dataclass(tp)
                field_data = [(fld.name, fld.type, fld) for fld in get_dataclass_fields(tp, include_classvars=True)]
                return make_dataclass(tp.__name__, field_data, bases=wrapped_cls.__bases__)
            return tp
        return _wrap(dataclass_type_map(cls, _wrap))  # type: ignore[arg-type]

    @classmethod
    def load_config(cls, path: AnyPath) -> Self:  # noqa: D102
        tp = _get_dataclass_type_for_path(path)
        new_cls: Type[FileSerializable] = ConfigDataclass._wrap_config_dataclass(tp, cls)  # type: ignore
        with open(path) as fp:
            cfg: Self = coerce_to_dataclass(cls, new_cls._from_file(fp))
        cfg.update_config()
        return cfg


class DictConfig(FileConfig, Dict[Any, Any]):
    """A collection of configurations, stored as a Python dict.

    To impose a type schema on the configurations, use [`ConfigDataclass`][fancy_dataclass.config.ConfigDataclass] instead.

    The configurations can be loaded from a file, the type of which will be inferred from its extension.
    Supported file types are:

    - JSON
    - TOML
    """

    @classmethod
    def load_config(cls, path: AnyPath) -> Self:  # noqa: D102
        tp = _get_dataclass_type_for_path(path)
        with open(path) as fp:
            cfg = cls(tp._text_file_to_dict(fp))  # type: ignore[attr-defined]
        cfg.update_config()
        return cfg
