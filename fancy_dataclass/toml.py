from typing import Any, TextIO

import tomlkit
from typing_extensions import Self

from fancy_dataclass.dict import AnyDict
from fancy_dataclass.serialize import DictFileSerializableDataclass, FileSerializable
from fancy_dataclass.utils import AnyIO


class TOMLSerializable(FileSerializable):
    """Mixin class enabling conversion of an object to/from TOML."""

    def to_toml(self, fp: AnyIO, **kwargs: Any) -> None:
        """Writes the object as TOML to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        return self._to_file(fp, **kwargs)

    def to_toml_string(self, **kwargs: Any) -> str:
        """Converts the object into a TOML string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a TOML string"""
        return self._to_string(**kwargs)

    @classmethod
    def from_toml(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Constructs an object from a TOML file-like object (text or binary).

        Args:
            fp: A readable file-like object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_file(fp, **kwargs)

    @classmethod
    def from_toml_string(cls, s: str, **kwargs: Any) -> Self:
        """Constructs an object from a TOML string.

        Args:
            s: TOML string
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_string(s, **kwargs)


class TOMLDataclass(DictFileSerializableDataclass, TOMLSerializable):
    """Dataclass mixin enabling default serialization of dataclass objects to and from TOML."""

    # TODO: require subclass to set qualified_type=True, like JSONDataclass?

    @classmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: TextIO, **kwargs: Any) -> None:
        tomlkit.dump(d, fp, **kwargs)

    @classmethod
    def _text_file_to_dict(cls, fp: TextIO, **kwargs: Any) -> AnyDict:
        return tomlkit.load(fp)
