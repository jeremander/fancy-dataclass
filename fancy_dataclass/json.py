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
        """Converts an object to a dict that can be readily converted into JSON."""

    def _json_encoder(self) -> Type[JSONEncoder]:
        """Override this method to create a custom JSON encoder to handle specific data types.
        A skeleton for this looks like:

        class Encoder(JSONEncoder):
            def default(self, obj):
                return json.JSONEncoder.default(self, obj)
        """
        return JSONEncoder

    @classmethod
    def _json_key_decoder(cls, key: Any) -> Any:
        """Override this method to decode a JSON key, for use with `from_dict`."""
        return key

    def to_json(self, fp: TextIO, **kwargs: Any) -> None:
        """Writes the object as JSON to fp, where fp is a writable file-like object."""
        indent = kwargs.get('indent')
        if (indent is not None) and (indent < 0):
            kwargs['indent'] = None
        kwargs['cls'] = self._json_encoder()
        d = self.to_dict()
        json.dump(d, fp, **kwargs)

    def to_json_string(self, **kwargs: Any) -> str:
        """Converts the object into a JSON string."""
        with StringIO() as stream:
            self.to_json(stream, **kwargs)
            return stream.getvalue()

    def to_file(self, fp: IO) -> None:
        """Writes this object as JSON to fp, where fp is a writable file-like object (text or binary)."""
        if isinstance(fp, TextIOBase):  # text stream
            super().to_json(fp)
        else:  # binary
            fp.write(self.to_json_string().encode())

    @abstractclassmethod
    def from_dict(cls: Type[T], d: JSONDict) -> T:  # type: ignore
        """Constructs an object of this type from a JSON dict."""

    @classmethod
    def from_json(cls: Type[T], fp: TextIO, **kwargs: Any) -> T:
        """Reads JSON from a file-like object and converts it to an object of this type."""
        d = json.load(fp, **kwargs)
        return cls.from_dict(d)

    @classmethod
    def from_json_string(cls: Type[T], s: str) -> T:
        """Converts a JSON string to an object of this type."""
        d = json.loads(s)
        return cls.from_dict(d)

    @classmethod
    def from_file(cls: Type[T], fp: IO, **kwargs: Any) -> T:
        """Reads JSON from a file-like object (text or binary) and converts it to an object of this type."""
        if isinstance(fp, TextIOBase):  # text stream
            return cls.from_json(fp, **kwargs)
        else:  # binary
            return cls.from_dict(json.load(fp))


class JSONDataclass(DictDataclass, JSONSerializable):  # type: ignore
    """Subclass of JSONSerializable enabling default serialization of dataclass objects."""

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
    """This class should be used in place of `JSONDataclass` when you intend to inherit from the class.
    When converting a subclass to a dict with `to_dict`, it will store the subclass's type in the 'type' field. It will also resolve this type on `from_dict`."""
