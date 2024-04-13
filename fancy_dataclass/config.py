from contextlib import contextmanager
from copy import copy
from dataclasses import make_dataclass
from pathlib import Path
from typing import ClassVar, Iterator, Optional, Type

from typing_extensions import Self

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.utils import AnyPath, coerce_to_dataclass, get_dataclass_fields


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
        """Updates the global configuration, setting it equal to this object."""
        type(self)._set_config(self)

    @contextmanager
    def configure(self) -> Iterator[None]:
        """Context manager which temporarily updates the global configuration with this object."""
        try:
            orig_config = type(self).get_config()
            self.update_config()
            yield
        finally:
            type(self)._set_config(orig_config)


class ConfigDataclass(Config, DictDataclass, suppress_defaults=False):
    """A dataclass representing a collection of configurations.

    The configurations can be loaded from a file, the type of which will be inferred from its extension.
    Supported file types are:
        - JSON
    """

    @staticmethod
    def _wrap_config_dataclass(mixin_cls: Type[DataclassMixin], cls: Type['ConfigDataclass']) -> Type[DataclassMixin]:
        """Recursively wraps a DataclassMixin class around a ConfigDataclass so that nested ConfigDataclass fields inherit from the same mixin."""
        wrapped_cls = mixin_cls.wrap_dataclass(cls)
        field_data = []
        for fld in get_dataclass_fields(cls, include_classvars=True):
            if issubclass(fld.type, ConfigDataclass):
                tp = ConfigDataclass._wrap_config_dataclass(mixin_cls, fld.type)
                new_fld = copy(fld)
                new_fld.type = tp
            else:
                tp = fld.type
                new_fld = fld
            field_data.append((fld.name, tp, new_fld))
        return make_dataclass(cls.__name__, field_data, bases=wrapped_cls.__bases__)

    @classmethod
    def load_config(cls, path: AnyPath) -> Self:
        """Loads configurations from a file and sets them to be the global configurations for this class.

        Returns:
            The newly loaded global configuration"""
        p = Path(path)
        ext = p.suffix.lower()
        if not ext:
            raise ValueError(f'filename {p} has no extension')
        if ext == '.json':
            from fancy_dataclass.json import JSONDataclass
            new_cls: Type[JSONDataclass] = ConfigDataclass._wrap_config_dataclass(JSONDataclass, cls)  # type: ignore[assignment]
            with open(path) as f:
                cfg: Self = coerce_to_dataclass(cls, new_cls.from_json(f))
        else:
            raise ValueError(f'unknown config file extension {ext!r}')
        cfg.update_config()
        return cfg
