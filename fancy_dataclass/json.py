from abc import ABC, abstractclassmethod, abstractmethod
import dataclasses
from enum import Enum
from io import StringIO, TextIOBase
import json
from json import JSONEncoder
from typing import Any, ClassVar, Dict, IO, TextIO, Type, TypeVar

from fancy_dataclass.dataclass import DataclassFromDict
from fancy_dataclass.utils import fully_qualified_class_name, get_subclass_with_name, obj_class_name

T = TypeVar('T')
J = TypeVar('J', bound = 'JSONSerializable')

JSONDict = Dict[str, Any]


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
        if isinstance(fp, TextIOBase):  # text stream
            super().to_json(fp)
        else:  # binary
            fp.write(self.to_json_string().encode())
    @abstractclassmethod
    @classmethod
    def from_dict(cls: Type[J], d: JSONDict) -> J:
        """Constructs an object of this type from a JSON dict."""
    @classmethod
    def from_json(cls: Type[J], fp: TextIO, **kwargs: Any) -> J:
        """Reads JSON from a file-like object and converts the context to this type."""
        d = json.load(fp, **kwargs)
        return cls.from_dict(d)
    @classmethod
    def from_json_string(cls: Type[J], s: str) -> J:
        d = json.loads(s)
        return cls.from_dict(d)
    @classmethod
    def from_file(cls: Type[T], fp: IO, **kwargs: Any) -> T:
        if isinstance(fp, TextIOBase):  # text stream
            return cls.from_json(fp, **kwargs)
        else:  # binary
            return cls.from_dict(json.load(fp))

class JSONDataclass(JSONSerializable, DataclassFromDict):
    """Subclass of JSONSerializable enabling default serialization of dataclass objects."""
    # if True, suppresses default values in 'to_dict'
    suppress_defaults: ClassVar[bool] = True
    # flag indicating whether to store the objects type in its dict representation
    store_type: ClassVar[bool] = False
    # flag indicating whether to fully qualify the type name in its dict representation (implies store_type)
    qualified_type: ClassVar[bool] = False
    # flag indicating whether to fully
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__()
        if ('suppress_defaults' in kwargs):  # override suppress_defaults value
            cls.suppress_defaults = kwargs['suppress_defaults']
    def _dict_init(self) -> JSONDict:
        if self.__class__.qualified_type:
            return {'type' : fully_qualified_class_name(self.__class__)}
        elif self.__class__.store_type:
            return {'type' : obj_class_name(self)}
        return {}
    def _to_dict(self, full: bool) -> JSONDict:
        def _to_value(x: Any) -> Any:
            if isinstance(x, Enum):
                return x.value
            elif isinstance(x, range):
                return list(x)
            elif isinstance(x, list):
                return [_to_value(y) for y in x]
            elif isinstance(x, tuple):
                return tuple(_to_value(y) for y in x)
            elif isinstance(x, dict):
                return {k : _to_value(v) for (k, v) in x.items()}
            elif hasattr(x, 'dtype'):  # assume it's a numpy array of numbers
                return [float(y) for y in x]
            elif isinstance(x, JSONSerializable):
                return x.to_dict()
            return x
        d = self._dict_init()
        fields = getattr(self.__class__, '__dataclass_fields__', None)
        if (fields is not None):
            for (name, field) in fields.items():
                if (name == 'type'):
                    raise ValueError("'type' is an invalid JSONDataclass field")
                if (getattr(field.type, '__origin__', None) is ClassVar):  # do not include ClassVars in dict
                    continue
                if (not field.init):  # suppress fields where init = False
                    continue
                val = getattr(self, name)
                if (not full):  # suppress values that match the default
                    try:
                        if (val == field.default):
                            continue
                        if (field.default_factory != dataclasses.MISSING) and (val == field.default_factory()):
                            continue
                    except ValueError:  # some types may fail to compare
                        pass
                d[name] = _to_value(val)
        return d
    def to_dict(self, **kwargs: Any) -> JSONDict:
        """Renders a dict which, by default, suppresses values matching their dataclass defaults.
        If full = True or the class's `suppress_defaults` is False, does not suppress defaults."""
        full = kwargs.get('full', not self.__class__.suppress_defaults)
        return self._to_dict(full)
    @classmethod
    def _convert_value(cls, tp: type, x: Any) -> Any:
        # customize for JSONSerializable
        origin_type = getattr(tp, '__origin__', None)
        if (origin_type == dict):  # decode keys to be valid JSON
            (keytype, valtype) = tp.__args__
            return {cls._json_key_decoder(cls._convert_value(keytype, k)) : cls._convert_value(valtype, v) for (k, v) in x.items()}
        # otherwise, fall back on superclass
        return DataclassFromDict._convert_value(tp, x)
    @classmethod
    def from_dict(cls: Type[T], d: JSONDict) -> T:
        # first establish the type, which may be present in the 'type' field of the JSON blob
        typename = d.get('type')
        if (typename is None):  # type field unspecified, so use the calling class
            tp = cls
        else:
            cls_name = fully_qualified_class_name(cls) if ('.' in typename) else cls.__name__
            if (cls_name == typename):  # type name already matches this class
                tp = cls
            else:
                # tp must be a subclass of cls
                # the name must be in scope to be found, allowing two alternatives for retrieval:
                # option 1: all subclasses of this JSONDataclass are defined in the same module as the base class
                # option 2: the name is fully qualified, so the name can be loaded into scope
                # call from_dict on the subclass in case it has its own custom implementation
                d2 = dict(d)
                d2.pop('type')  # remove the type name before passing to the constructor
                return get_subclass_with_name(cls, typename).from_dict(d2)
        return tp(**cls._dataclass_args_from_dict(d))  # type: ignore

class JSONBaseDataclass(JSONDataclass):
    """This class should be used as a base class for one or more JSONDataclasses.
    It will store the subclass's type in the 'type' field of its `to_dict` representation, and it will resolve this type on `from_dict`."""
    store_type = True
    qualified_type = True

