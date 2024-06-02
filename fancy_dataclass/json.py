from datetime import datetime
from io import IOBase
import json
from json import JSONEncoder
from typing import IO, Any, Type, cast, get_args, get_origin

from typing_extensions import Self

from fancy_dataclass.dict import AnyDict
from fancy_dataclass.serialize import DictFileSerializableDataclass, TextFileSerializable, from_dict_value_basic, to_dict_value_basic
from fancy_dataclass.utils import AnyIO, TypeConversionError, issubclass_safe


class JSONSerializable(TextFileSerializable):
    """Mixin class enabling conversion of an object to/from JSON."""

    @classmethod
    def json_encoder(cls) -> Type[JSONEncoder]:
        """Override this method to create a custom `JSONEncoder` to handle specific data types.
        A skeleton for this looks like:

        ```
        class Encoder(JSONEncoder):
            def default(self, obj):
                return json.JSONEncoder.default(self, obj)
        ```
        """
        class Encoder(JSONEncoder):
            def default(self, obj: Any) -> Any:
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return JSONEncoder.default(self, obj)
        return Encoder

    @classmethod
    def json_key_decoder(cls, key: Any) -> Any:
        """Override this method to decode a JSON key, for use with `from_dict`."""
        return key

    def to_json(self, fp: IOBase, **kwargs: Any) -> None:
        """Writes the object as JSON to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        return JSONDataclass._to_file(self, fp, **kwargs)  # type: ignore[arg-type]

    def to_json_string(self, **kwargs: Any) -> str:
        """Converts the object into a JSON string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a JSON string"""
        return JSONDataclass._to_string(self, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def _from_binary_file(cls, fp: IO[bytes], **kwargs: Any) -> Self:
        # json.load accepts binary file, so we avoid the string conversion
        return cls._from_text_file(cast(IO[str], fp), **kwargs)

    @classmethod
    def from_json(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Constructs an object from a JSON file-like object (text or binary).

        Args:
            fp: A readable file-like object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_file(fp, **kwargs)

    @classmethod
    def from_json_string(cls, s: str, **kwargs: Any) -> Self:
        """Constructs an object from a JSON string.

        Args:
            s: JSON string
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_string(s, **kwargs)


class JSONDataclass(DictFileSerializableDataclass, JSONSerializable):  # type: ignore[misc]
    """Dataclass mixin enabling default serialization of dataclass objects to and from JSON."""

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # if the class already inherits from JSONDataclass, raise an error if qualified_type=False
        # this is because resolving the type from a dict may be ambiguous
        if not getattr(cls.__settings__, 'qualified_type', False):
            for base in cls.mro():
                if (base not in [cls, JSONDataclass]) and issubclass(base, JSONDataclass):
                    raise TypeError('when subclassing a JSONDataclass, you must set qualified_type=True or subclass JSONBaseDataclass instead')

    @classmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        indent = kwargs.get('indent')
        if (indent is not None) and (indent < 0):
            kwargs['indent'] = None
        kwargs['cls'] = cls.json_encoder()
        json.dump(d, fp, **kwargs)

    @classmethod
    def _text_file_to_dict(cls, fp: IO[str], **kwargs: Any) -> AnyDict:
        d = json.load(fp, **kwargs)
        if not isinstance(d, dict):
            raise ValueError('loaded JSON is not a dict')
        return d

    @classmethod
    def _to_dict_value_basic(cls, val: Any) -> Any:
        return to_dict_value_basic(val)

    @classmethod
    def _to_dict_value(cls, val: Any, full: bool) -> Any:
        if isinstance(val, tuple) and hasattr(val, '_fields'):
            # if a namedtuple, render as a dict with named fields rather than a tuple
            return {k: cls._to_dict_value(v, full) for (k, v) in zip(val._fields, val)}
        return super()._to_dict_value(val, full)

    @classmethod
    def _from_dict_value_basic(cls, tp: type, val: Any) -> Any:
        if issubclass(tp, datetime):
            return tp.fromisoformat(val) if isinstance(val, str) else val
        return super()._from_dict_value_basic(tp, from_dict_value_basic(tp, val))

    @classmethod
    def _from_dict_value(cls, tp: type, val: Any, strict: bool = False) -> Any:
        # customize behavior for JSONSerializable
        origin_type = get_origin(tp)
        if (origin_type is None) and issubclass_safe(tp, tuple) and isinstance(val, dict) and hasattr(tp, '_fields'):  # namedtuple
            try:
                vals = []
                for key in tp._fields:
                    # if NamedTuple's types are annotated, check them
                    valtype = getattr(tp, '__annotations__', {}).get(key)
                    vals.append(val[key] if (valtype is None) else cls._from_dict_value(valtype, val[key], strict=strict))
                return tp(*vals)
            except KeyError as e:
                raise TypeConversionError(tp, val) from e
        if origin_type == dict:  # decode keys to be valid JSON
            (keytype, valtype) = get_args(tp)
            return {cls.json_key_decoder(cls._from_dict_value(keytype, k)): cls._from_dict_value(valtype, v, strict=strict) for (k, v) in val.items()}
        return super()._from_dict_value(tp, val)


class JSONBaseDataclass(JSONDataclass, qualified_type=True):
    """This class should be used in place of [`JSONDataclass`][fancy_dataclass.json.JSONDataclass] when you intend to inherit from the class.

    When converting a subclass to a dict with [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict], it will store the subclass's type in the `type` field. It will also resolve this type when calling [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict]."""
