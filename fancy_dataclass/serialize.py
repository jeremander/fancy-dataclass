from abc import ABC, abstractmethod
from enum import Enum
from io import BytesIO, StringIO, TextIOBase
from numbers import Integral
from pathlib import Path
from typing import IO, Any, BinaryIO, Union, cast

from typing_extensions import Self

from fancy_dataclass.dict import AnyDict, DictDataclass
from fancy_dataclass.utils import AnyIO, AnyPath, TypeConversionError


def to_dict_value_basic(val: Any) -> Any:
    """Converts an arbitrary value with a basic data type to an appropriate form for serializing to typical file formats (JSON, TOML).

    Args:
        val: Value with basic data type

    Returns:
        A version of that value suitable for serialization"""
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, range):  # store the range bounds
        bounds = [val.start, val.stop]
        if val.step != 1:
            bounds.append(val.step)
        return bounds
    if hasattr(val, 'dtype'):
        if hasattr(val, '__len__'):  # assume it's a numpy array of numbers
            return [float(elt) for elt in val]
        # numpy scalars have trouble serializing
        if isinstance(val, Integral):
            return int(val)
        if isinstance(val, float):
            return float(val)
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
    if issubclass(tp, Integral) and isinstance(val, Integral):
        # also handles numpy integer types
        return tp(val)  # type: ignore[call-arg]
    if issubclass(tp, range):
        return tp(*val)
    if issubclass(tp, Enum):
        try:
            return tp(val)
        except ValueError as e:
            raise TypeConversionError(tp, val) from e
    if getattr(tp, '__name__', None) == 'ndarray':  # numpy array
        import numpy as np
        return np.array(val)
    return val


class FileSerializable:
    """Mixin class enabling serialization of an object to/from a file (either text or binary)."""

    @classmethod
    @abstractmethod
    def _to_file(cls, obj: Self, fp: AnyIO, **kwargs: Any) -> None:
        """Serializes the object to a file-like object (text or binary).

        Args:
            obj: Object to serialize
            fp: A writable file-like object
            kwargs: Keyword arguments"""

    @classmethod
    @abstractmethod
    def _from_file(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Deserializes the object from a file-like object (text or binary).

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""

    @classmethod
    @abstractmethod
    def _file_mode_is_binary(cls) -> bool:
        """Returns True if the class's default mode for opening files is binary."""

    def save(self, file: Union[AnyPath, AnyIO], **kwargs: Any) -> None:
        """Serializes the object to a path or file-like object (text or binary).

        Args:
            file: Path or file-like object to save to
            kwargs: Keyword arguments for serialization"""
        if isinstance(file, (str, Path)):
            mode = 'wb' if self._file_mode_is_binary() else 'w'
            with open(file, mode) as fp:
                self._to_file(self, fp, **kwargs)
        else:
            self._to_file(self, file, **kwargs)

    @classmethod
    def load(cls, file: Union[AnyPath, AnyIO], **kwargs: Any) -> Self:
        """Deserializes the object from a file, given a path or file-like object.

        Args:
            file: Path or file-like object to load from
            kwargs: Keyword arguments for deserialization"""
        if isinstance(file, (str, Path)):
            mode = 'rb' if cls._file_mode_is_binary() else 'r'
            with open(file, mode) as fp:
                return cls._from_file(fp, **kwargs)
        return cls._from_file(file, **kwargs)


class BinarySerializable(ABC):
    """Mixin class enabling serialization of an object to/from a binary string.

    Subclasses should override `_to_bytes` and `_from_bytes` to implement them."""

    @classmethod
    @abstractmethod
    def _to_bytes(cls, obj: Self, **kwargs: Any) -> bytes:
        """Converts the object into raw bytes.

        Args:
            obj: Object to serialize
            kwargs: Keyword arguments

        Returns:
            Object rendered as raw bytes"""

    @classmethod
    @abstractmethod
    def _from_bytes(cls, b: bytes, **kwargs: Any) -> Self:
        """Deserializes the object from raw bytes.

        Args:
            b: Bytes to deserialize
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""


class BinaryFileSerializable(BinarySerializable, FileSerializable):
    """Mixin class enabling serialization of an object to/from a binary file.

    Subclasses should override `_to_binary_file` and `_from_binary_file` to implement them."""

    @classmethod
    def _file_mode_is_binary(cls) -> bool:
        return True

    @classmethod
    @abstractmethod
    def _to_binary_file(cls, obj: Self, fp: IO[bytes], **kwargs: Any) -> None:
        """Serializes the object to a file in binary mode.

        Args:
            obj: Object to serialize
            fp: A writable binary file-like object
            kwargs: Keyword arguments"""

    @classmethod
    @abstractmethod
    def _from_binary_file(cls, fp: IO[bytes], **kwargs: Any) -> Self:
        """Deserializes the object from a file in binary mode.

        Args:
            fp: A readable binary file-like object
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""

    @classmethod
    def _to_bytes(cls, obj: Self, **kwargs: Any) -> bytes:
        with BytesIO() as stream:
            cls._to_binary_file(obj, stream, **kwargs)
            return stream.getvalue()

    @classmethod
    def _from_bytes(cls, b: bytes, **kwargs: Any) -> Self:
        with BytesIO(b) as bio:
            return cls._from_binary_file(bio, **kwargs)

    @classmethod
    def _to_file(cls, obj: Self, fp: AnyIO, **kwargs: Any) -> None:
        cls._to_binary_file(obj, cast(IO[bytes], fp), **kwargs)

    @classmethod
    def _from_file(cls, fp: AnyIO, **kwargs: Any) -> Self:
        return cls._from_binary_file(cast(IO[bytes], fp), **kwargs)


class TextSerializable(BinarySerializable, ABC):
    """Mixin class enabling serialization of an object to/from a text string.

    Subclasses should override `_to_string` and `_from_string` to implement them."""

    @classmethod
    @abstractmethod
    def _to_string(cls, obj: Self, **kwargs: Any) -> str:
        """Converts the object into a text string.

        Args:
            obj: Object to serialize
            kwargs: Keyword arguments

        Returns:
            Object rendered as a string"""

    @classmethod
    @abstractmethod
    def _from_string(cls, s: str, **kwargs: Any) -> Self:
        """Deserializes the object from a string.

        Args:
            s: String to deserialize
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""

    @classmethod
    def _to_bytes(cls, obj: Self, **kwargs: Any) -> bytes:
        # by default, encode string as UTF-8
        return cls._to_string(obj, **kwargs).encode()

    @classmethod
    def _from_bytes(cls, b: bytes, **kwargs: Any) -> Self:
        # by default, decode bytes as UTF-8
        return cls._from_string(b.decode(), **kwargs)


class TextFileSerializable(TextSerializable, BinaryFileSerializable, FileSerializable):  # type: ignore[misc]
    """Mixin class enabling serialization of an object to/from a text file.

    Subclasses should override `_to_text_file` and `_from_text_file` to implement them."""

    @classmethod
    def _file_mode_is_binary(cls) -> bool:
        return False

    @classmethod
    @abstractmethod
    def _to_text_file(cls, obj: Self, fp: IO[str], **kwargs: Any) -> None:
        """Serializes the object to a file in text mode.

        Args:
            obj: Object to serialize
            fp: A writable text file-like object
            kwargs: Keyword arguments"""

    @classmethod
    @abstractmethod
    def _from_text_file(cls, fp: IO[str], **kwargs: Any) -> Self:
        """Deserializes the object from a file in text mode.

        Args:
            fp: A readable text file-like object
            kwargs: Keyword arguments

        Returns:
            The deserialized object"""

    @classmethod
    def _to_string(cls, obj: Self, **kwargs: Any) -> str:
        with StringIO() as stream:
            cls._to_text_file(obj, stream, **kwargs)
            return stream.getvalue()

    @classmethod
    def _from_string(cls, s: str, **kwargs: Any) -> Self:
        with StringIO(s) as sio:
            return cls._from_text_file(sio, **kwargs)

    @classmethod
    def _to_binary_file(cls, obj: Self, fp: IO[bytes], **kwargs: Any) -> None:
        fp.write(cls._to_bytes(obj, **kwargs))

    @classmethod
    def _from_binary_file(cls, fp: IO[bytes], **kwargs: Any) -> Self:
        return cls._from_bytes(fp.read(), **kwargs)

    @classmethod
    def _to_file(cls, obj: Self, fp: AnyIO, **kwargs: Any) -> None:
        if isinstance(fp, TextIOBase):
            cls._to_text_file(obj, fp, **kwargs)
        else:
            cls._to_binary_file(obj, cast(BinaryIO, fp), **kwargs)

    @classmethod
    def _from_file(cls, fp: AnyIO, **kwargs: Any) -> Self:
        if isinstance(fp, TextIOBase):
            return cls._from_text_file(fp, **kwargs)
        return cls._from_binary_file(cast(BinaryIO, fp), **kwargs)


class DictFileSerializableDataclass(DictDataclass, TextFileSerializable):  # type: ignore[misc]
    """Mixin class for a [`DictDataclass`][fancy_dataclass.dict.DictDataclass] capable of serializing its dict representation to some type of file.

    Examples include JSON and TOML."""

    @classmethod
    @abstractmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        """Serializes a dict to a text file.

        Args:
            d: A Python dict
            fp: A writable file-like object
            kwargs: Keyword arguments"""

    @classmethod
    def _to_text_file(cls, obj: Self, fp: IO[str], **kwargs: Any) -> None:
        # NOTE: by default, we pass all kwargs to `_dict_to_text_file` and none to `to_dict`
        return cls._dict_to_text_file(cls.to_dict(obj), fp, **kwargs)

    @classmethod
    @abstractmethod
    def _text_file_to_dict(cls, fp: IO[str], **kwargs: Any) -> AnyDict:
        """Deserializes a text file to a dict.

        Args:
            fp: A readable text file-like object
            kwargs: Keyword arguments

        Returns:
            A dict representation of the file"""

    @classmethod
    def _from_text_file(cls, fp: IO[str], **kwargs: Any) -> Self:
        # pop off known DictDataclass.from_dict kwargs
        default_dict_kwargs = {'strict': False}
        load_kwargs = {key: val for (key, val) in kwargs.items() if (key not in default_dict_kwargs)}
        from_dict_kwargs = {key: kwargs.get(key, default_dict_kwargs[key]) for key in default_dict_kwargs}
        return cls.from_dict(cls._text_file_to_dict(fp, **load_kwargs), **from_dict_kwargs)
