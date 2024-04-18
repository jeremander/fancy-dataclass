from dataclasses import Field
from io import IOBase
from typing import IO, Any

import tomlkit
from typing_extensions import Self

from fancy_dataclass.dict import AnyDict
from fancy_dataclass.serialize import DictFileSerializableDataclass, TextFileSerializable, from_dict_value_basic, to_dict_value_basic
from fancy_dataclass.utils import AnyIO


def _remove_null_dict_values(val: Any) -> Any:
    """Removes all null (None) values from a dict.

    Does this recursively to any nested dicts or lists."""
    if isinstance(val, (list, tuple)):
        return type(val)(_remove_null_dict_values(elt) for elt in val)
    if isinstance(val, dict):
        return type(val)({key: _remove_null_dict_values(elt) for (key, elt) in val.items() if (elt is not None)})
    return val


class TOMLSerializable(TextFileSerializable):
    """Mixin class enabling conversion of an object to/from TOML."""

    def to_toml(self, fp: IOBase, **kwargs: Any) -> None:
        """Writes the object as TOML to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        return TOMLDataclass._to_file(self, fp, **kwargs)  # type: ignore[arg-type]

    def to_toml_string(self, **kwargs: Any) -> str:
        """Converts the object into a TOML string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a TOML string"""
        return TOMLDataclass._to_string(self, **kwargs)  # type: ignore[arg-type]

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


class TOMLDataclass(DictFileSerializableDataclass, TOMLSerializable, suppress_defaults=False):  # type: ignore[misc]
    """Dataclass mixin enabling default serialization of dataclass objects to and from TOML."""

    # TODO: require subclass to set qualified_type=True, like JSONDataclass?
    @classmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        d = _remove_null_dict_values(d)
        tomlkit.dump(d, fp, **kwargs)

    @classmethod
    def _text_file_to_dict(cls, fp: IO[str], **kwargs: Any) -> AnyDict:
        return tomlkit.load(fp)

    @classmethod
    def _to_dict_value_basic(cls, val: Any) -> Any:
        return to_dict_value_basic(val)

    @classmethod
    def _from_dict_value_basic(cls, tp: type, val: Any) -> Any:
        return super()._from_dict_value_basic(tp, from_dict_value_basic(tp, val))

    @classmethod
    def _get_missing_value(cls, fld: Field) -> Any:  # type: ignore[type-arg]
        # replace any missing required fields with a default of None
        return None
