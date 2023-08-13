from abc import ABC, abstractclassmethod, abstractmethod
from io import StringIO, TextIOBase
import json
from json import JSONEncoder
from typing import Any, IO, TextIO, Type, TypeVar

from fancy_dataclass.dict import DictDataclass, JSONDict


T = TypeVar('T')


class JSONSerializable(ABC):
    """Mixin class enabling conversion of an object to/from JSON."""

    @abstractmethod
    def to_dict(self, **kwargs: Any) -> JSONDict:
        """Converts an object to a dict that can be readily converted into JSON.

        Returns:
            A JSON-convertible dict"""

    def _json_encoder(self) -> Type[JSONEncoder]:
        """Override this method to create a custom `JSONEncoder` to handle specific data types.
        A skeleton for this looks like:

        ```
        class Encoder(JSONEncoder):
            def default(self, obj):
                return json.JSONEncoder.default(self, obj)
        ```
        """
        return JSONEncoder

    @classmethod
    def _json_key_decoder(cls, key: Any) -> Any:
        """Override this method to decode a JSON key, for use with `from_dict`."""
        return key

    def _to_json(self, fp: TextIO, **kwargs: Any) -> None:
        indent = kwargs.get('indent')
        if (indent is not None) and (indent < 0):
            kwargs['indent'] = None
        kwargs['cls'] = self._json_encoder()
        d = self.to_dict()
        json.dump(d, fp, **kwargs)

    def to_json(self, fp: IO, **kwargs: Any) -> None:
        """Writes the object as JSON to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments passed to `json.dump`"""
        if isinstance(fp, TextIOBase):  # text stream
            self._to_json(fp, **kwargs)
        else:  # binary
            fp.write(self.to_json_string(**kwargs).encode())

    def to_json_string(self, **kwargs: Any) -> str:
        """Converts the object into a JSON string.

        Args:
            kwargs: Keyword arguments passed to `json.dump`

        Returns:
            Object rendered as a JSON string"""
        with StringIO() as stream:
            self._to_json(stream, **kwargs)
            return stream.getvalue()

    @abstractclassmethod
    def from_dict(cls: Type[T], d: JSONDict) -> T:  # type: ignore
        """Constructs an object from a dictionary of fields.

        Args:
            d: Dict to convert into an object

        Returns:
            Converted object of this class"""

    @classmethod
    def from_json(cls: Type[T], fp: IO, **kwargs: Any) -> T:
        """Constructs an object from a JSON file-like object (text or binary).

        Args:
            fp: A readable file-like object
            kwargs: Keyword arguments passed to `json.load`

        Returns:
            Converted object of this class"""
        return cls.from_dict(json.load(fp, **kwargs))

    @classmethod
    def from_json_string(cls: Type[T], s: str, **kwargs: Any) -> T:
        """Constructs an object from a JSON string.

        Args:
            s: JSON string
            kwargs: Keyword arguments passed to `json.loads`

        Returns:
            Converted object of this class"""
        return cls.from_dict(json.loads(s, **kwargs))


class JSONDataclass(DictDataclass, JSONSerializable):  # type: ignore
    """Subclass of [`JSONSerializable`][fancy_dataclass.json.JSONSerializable] enabling default serialization of dataclass objects to and from JSON."""

    @classmethod
    def _convert_value(cls, tp: type, x: Any) -> Any:
        # customize for JSONSerializable
        origin_type = getattr(tp, '__origin__', None)
        if (origin_type == dict):  # decode keys to be valid JSON
            (keytype, valtype) = tp.__args__
            return {cls._json_key_decoder(cls._convert_value(keytype, k)) : cls._convert_value(valtype, v) for (k, v) in x.items()}
        # otherwise, fall back on superclass
        return DictDataclass._convert_value(tp, x)


class JSONBaseDataclass(JSONDataclass, qualified_type = True):
    """This class should be used in place of [`JSONDataclass`][fancy_dataclass.json.JSONDataclass] when you intend to inherit from the class.
    When converting a subclass to a dict with [`to_dict`][fancy_dataclass.json.JSONSerializable.to_dict], it will store the subclass's type in the `type` field. It will also resolve this type on [`from_dict`][fancy_dataclass.json.JSONSerializable.from_dict]."""
