from abc import ABC, abstractmethod
from enum import Enum
from io import StringIO, TextIOBase
from typing import Any, BinaryIO, TextIO

from typing_extensions import Self

from fancy_dataclass.dict import AnyDict, DictDataclass
from fancy_dataclass.utils import AnyIO, TypeConversionError


def to_dict_value_basic(val: Any) -> Any:
    """Converts an arbitrary value with a basic data type to an appropriate form for serializing to typical file formats (JSON, TOML).

    Args:
        val: Value with basic data type

    Returns:
        A version of that value suitable for serialization"""
    if isinstance(val, Enum):
        return val.value
    elif isinstance(val, range):  # store the range bounds
        bounds = [val.start, val.stop]
        if val.step != 1:
            bounds.append(val.step)
        return bounds
    elif hasattr(val, 'dtype'):  # assume it's a numpy array of numbers
        return [float(elt) for elt in val]
    return val

def from_dict_value_basic(tp: type, val: Any) -> Any:
    """Converts a deserialized value to the given type.

    Args:
        tp: Target type to convert to
        val: Deserialized value

    Returns:
        Converted value"""
    if issubclass(tp, float):
        return tp(val)
    if issubclass(tp, range):
        return tp(*val)
    if issubclass(tp, Enum):
        try:
            return tp(val)
        except ValueError as e:
            raise TypeConversionError(tp, val) from e
    return val


class FileSerializable(ABC):
    """Mixin class enabling serialization of an object to/from a file.

    Subclasses should override `_to_text_file` and `_from_text_file` to implement them."""

    @abstractmethod
    def _to_text_file(self, fp: TextIO, **kwargs: Any) -> None:
        """Serializes the object to a file in text mode.

        Args:
            fp: A writable text file-like object
            kwargs: Keyword arguments"""

    def _to_binary_file(self, fp: BinaryIO, **kwargs: Any) -> None:
        """Serializes the object to a file in binary mode.

        By default, this writes text encoded as UTF-8.

        Args:
            fp: A writable binary file-like object
            kwargs: Keyword arguments"""
        # by default, convert to a text string, then encode as UTF-8
        fp.write(self._to_string(**kwargs).encode())

    def _to_file(self, fp: AnyIO, **kwargs: Any) -> None:
        """Serializes the object to a file-like object (text or binary).

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        if isinstance(fp, TextIOBase):  # text stream
            self._to_text_file(fp, **kwargs)
        else:  # binary
            self._to_binary_file(fp, **kwargs)  # type: ignore[arg-type]

    def _to_string(self, **kwargs: Any) -> str:
        """Converts the object into a text string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a string"""
        with StringIO() as stream:
            self._to_text_file(stream, **kwargs)
            return stream.getvalue()

    @classmethod
    @abstractmethod
    def _from_text_file(cls, fp: TextIO, **kwargs: Any) -> Self:
        """Deserializes the object from a file in text mode.

        Args:
            fp: A readable text file-like object
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""

    @classmethod
    def _from_binary_file(cls, fp: BinaryIO, **kwargs: Any) -> Self:
        """Deserializes the object from a file in binary mode.

        Args:
            fp: A readable binary file-like object
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""
        # by default, read binary stream, decode to a text string, then deserialize
        return cls._from_string(fp.read().decode(), **kwargs)

    @classmethod
    def _from_file(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Deserializes the object from a file-like object (text or binary).

        If the file is open in binary mode, reads text with UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        if isinstance(fp, TextIOBase):  # text stream
            return cls._from_text_file(fp, **kwargs)
        else:  # binary
            return cls._from_binary_file(fp, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def _from_string(cls, s: str, **kwargs: Any) -> Self:
        """Deserializes the object from a string.

        Args:
            s: String to deserialize
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""
        with StringIO(s) as sio:
            return cls._from_text_file(sio, **kwargs)


class DictFileSerializableDataclass(DictDataclass, FileSerializable):
    """Mixin class for a [`DictDataclass`][fancy_dataclass.dict.DictDataclass] capable of serializing its dict representation to some type of file.

    Examples include JSON and TOML."""

    @classmethod
    @abstractmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: TextIO, **kwargs: Any) -> None:
        """Serializes a dict to a text file.

        Args:
            d: A Python dict
            fp: A writable file-like object
            kwargs: Keyword arguments"""

    def _to_text_file(self, fp: TextIO, **kwargs: Any) -> None:
        # NOTE: by default, we pass all kwargs to `_dict_to_text_file` and none to `to_dict`
        return self._dict_to_text_file(self.to_dict(), fp, **kwargs)

    @classmethod
    @abstractmethod
    def _text_file_to_dict(cls, fp: TextIO, **kwargs: Any) -> AnyDict:
        """Deserializes a text file to a dict.

        Args:
            fp: A readable text file-like object
            kwargs: Keyword arguments

        Returns:
            A dict representation of the file"""

    @classmethod
    def _from_text_file(cls, fp: TextIO, **kwargs: Any) -> Self:
         # pop off known DictDataclass.from_dict kwargs
         default_dict_kwargs = {'strict': False}
         load_kwargs = {key: val for (key, val) in kwargs.items() if (key not in default_dict_kwargs)}
         from_dict_kwargs = {key: kwargs.get(key, default_dict_kwargs[key]) for key in default_dict_kwargs}
         return cls.from_dict(cls._text_file_to_dict(fp, **load_kwargs), **from_dict_kwargs)
