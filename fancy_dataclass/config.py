from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, Iterator, Optional

from typing_extensions import Self

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.utils import AnyPath


class Config:
    """Base class for a collection of configurations.

    This uses the Singleton pattern by storing a class attribute with the current configurations, which can be retrieved or updated by the user."""

    _config: ClassVar[Optional[Self]] = None

    @classmethod
    def get_config(cls) -> Optional[Self]:
        """Gets the current global configuration."""
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
        """Updates the global configuration, setting it equal to this value."""
        type(self)._set_config(self)

    @contextmanager
    def configure(self) -> Iterator[None]:
        """Context manager which temporarily updates the global configuration with this value."""
        try:
            orig_config = type(self).get_config()
            self.update_config()
            yield
        finally:
            type(self)._set_config(orig_config)


class ConfigDataclass(Config, DictDataclass):
    """A dataclass representing a collection of configurations.

    The configurations can be loaded from a file, the type of which will be inferred from its extension. Supported file types are:
        - JSON
    """

    @classmethod
    def load_config(cls, path: AnyPath) -> Self:
        """Loads configuration from a file and sets them to be the global configuration for this class.

        Returns:
            The newly loaded global configuration"""
        p = Path(path)
        ext = p.suffix
        if not ext:
            raise ValueError(f'filename {p} has no extension')
        if ext == '.json':
            from fancy_dataclass.json import JSONDataclass
            new_cls = JSONDataclass.wrap_dataclass(cls)
            with open(path) as f:
                cfg: Self = cls.from_dict(new_cls.from_json(f).to_dict())
        else:
            raise ValueError(f'unknown config file extension {ext!r}')
        cfg.update_config()
        return cfg
