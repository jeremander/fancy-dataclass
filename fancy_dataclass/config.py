from abc import ABC, abstractmethod
from contextlib import contextmanager
import json
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterator, Optional

from typing_extensions import Self

from fancy_dataclass.dict import AnyDict, DictDataclass
from fancy_dataclass.utils import AnyPath


class Config:
    """Base class for storing a collection of configurations.

    Subclasses may store a class attribute, `_config`, with the current global configurations, which can be retrieved or updated by the user."""

    _config: ClassVar[Optional[Self]] = None

    @classmethod
    def get_config(cls) -> Optional[Self]:
        """Gets the current global configuration.

        Returns:
            Global configuration object (`None` if not set)"""
        return cls._config

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


def _load_dict(path: AnyPath) -> AnyDict:
    p = Path(path)
    if not p.suffix:
        raise ValueError(f'filename {p} has no extension')
    ext_lower = p.suffix.lower()
    if ext_lower not in ['.json', '.toml']:
        raise ValueError(f'unknown config file extension {p.suffix!r}')
    with open(p) as f:
        if ext_lower == '.json':
            d = json.load(f)
        elif ext_lower == '.toml':
            import tomlkit as tk
            d = tk.load(f)
    if not isinstance(d, dict):
        raise ValueError('loaded JSON is not a dict')
    return d


class ConfigDataclass(DictDataclass, FileConfig, suppress_defaults=False, store_type='off'):
    """A dataclass representing a collection of configurations.

    The configurations can be loaded from a file, the type of which will be inferred from its extension.
    Supported file types are:

    - JSON
    - TOML
    """

    @classmethod
    def load_config(cls, path: AnyPath) -> Self:  # noqa: D102
        cfg = cls.from_dict(_load_dict(path))
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
        cfg = cls(_load_dict(path))
        cfg.update_config()
        return cfg

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        dict_repr = dict.__repr__(self)
        return f'{cls_name}({dict_repr})'
