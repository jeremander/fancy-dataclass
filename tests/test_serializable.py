from collections import namedtuple
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, Flag, auto
import math
import re
import sys
from typing import Any, ClassVar, List, Literal, NamedTuple, Optional, TypedDict, Union

import numpy as np
import pytest
from typing_extensions import Annotated, Doc

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass
from fancy_dataclass.toml import TOMLDataclass
from fancy_dataclass.utils import coerce_to_dataclass, dataclass_type_map, issubclass_safe


NOW = datetime.now()


def _convert_json_dataclass(cls, new_cls):
    """Converts JSONDataclass base classes with the given class, recursively within the input class's fields."""
    # TODO: this is very hacky; can we clean it up?
    def _convert(tp):
        if issubclass_safe(tp, JSONDataclass):
            bases = []
            for base in tp.__bases__:
                if base in (JSONDataclass, JSONBaseDataclass):
                    base = new_cls
                elif issubclass_safe(base, JSONDataclass):
                    base = _convert_json_dataclass(base, new_cls)
                bases.append(base)
            return type(tp.__name__, tuple(bases), dict(tp.__dict__))
        return tp
    tp = _convert(dataclass_type_map(cls, _convert))
    tp.__eq__ = cls.__eq__
    tp.__settings__ = cls.__settings__
    return tp


################
# TEST CLASSES #
################

@dataclass
class DCEmpty(JSONDataclass):
    ...

@dataclass
class DC1(JSONBaseDataclass):
    x: int
    y: float
    z: str

@dataclass
class DC2(JSONBaseDataclass):
    x: int
    y: float
    z: str

@dataclass
class DC1Sub(DC1):
    ...

@dataclass
class DC2Sub(DC2):
    ...

@dataclass
class DC3(JSONDataclass):
    list: List[int]

class MyObject:
    """This object is not JSON-serializable."""
    def __eq__(self, other):
        return isinstance(other, MyObject)

@dataclass
class DCNonJSONSerializable(JSONDataclass):
    x: int
    obj: MyObject

@dataclass
class DCOptional(JSONDataclass):
    x: Optional[int]

@dataclass
class DCOptionalDefault(JSONDataclass):
    x: Optional[int] = 1

@dataclass
class DCOptionalInt(JSONDataclass):
    x: int
    y: Optional[int]

@dataclass
class DCOptionalStr(JSONDataclass):
    x: str
    y: Optional[str]

@dataclass
class DCUnion(JSONDataclass):
    x: Union[int, str]

@dataclass
class DCLiteral(JSONDataclass):
    lit: Literal['a', 1]

@dataclass
class DCDatetime(JSONDataclass):
    dt: datetime

class MyEnum(Enum):
    a = auto()
    b = auto()

@dataclass
class DCEnum(JSONDataclass):
    enum: MyEnum

if sys.version_info[:2] < (3, 11):
    class StrEnum(str, Enum):
        pass
else:
    from enum import StrEnum  # novermin

class MyStrEnum(StrEnum):
    a = 'a'
    b = 'b'

@dataclass
class DCStrEnum(JSONDataclass):
    enum: MyStrEnum

class Color(Flag):
    RED = auto()
    GREEN = auto()
    BLUE = auto()

@dataclass
class DCColors(JSONDataclass):
    colors: List[Color]

@dataclass
class DCRange(JSONDataclass):
    range: range

@dataclass
class DCAnnotated(JSONDataclass):
    x: Annotated[int, 'an integer']
    y: Annotated[float, Doc('a float')]

class MyTypedDict(TypedDict):
    x: int
    y: str

@dataclass
class DCTypedDict(JSONDataclass):
    d: MyTypedDict

UntypedNamedTuple = namedtuple('UntypedNamedTuple', ['x', 'y'])

class TypedNamedTuple(NamedTuple):
    x: int
    y: str

@dataclass
class DCUntypedNamedTuple(JSONDataclass):
    t: UntypedNamedTuple

@dataclass
class DCTypedNamedTuple(JSONDataclass):
    t: TypedNamedTuple

@dataclass
class DCAny(JSONDataclass):
    val: Any

@dataclass
class DCFloat(JSONDataclass):
    x: float
    def __eq__(self, other):
        # make nan equal, for comparison testing
        return (math.isnan(self.x) and math.isnan(other.x)) or (self.x == other.x)

@dataclass
class DCSuppress(JSONDataclass, suppress_defaults=False):
    cv1: ClassVar[int] = field(default=0)
    x: int = field(default=1)
    y: int = field(default=2, metadata={'suppress': True})
    z: int = field(default=3, metadata={'suppress': False})

@dataclass
class DCSuppress2(JSONDataclass, suppress_defaults=True):
    cv1: ClassVar[int] = field(default=0)
    x: int = field(default=1)
    y: int = field(default=2, metadata={'suppress': True})
    z: int = field(default=3, metadata={'suppress': False})

@dataclass
class DCList(JSONDataclass):
    vals: List[DCAny]

@dataclass
class DCListOptional(JSONDataclass):
    vals: List[Optional[int]]


@dataclass
class DCNumpy(JSONDataclass, suppress_defaults=False):
    num_int: np.int64 = np.int64(1)
    num_float: np.float64 = np.float64(1)
    arr_int: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.int64))
    arr_float: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float64))

    def __eq__(self, other):
        for name in self.__dataclass_fields__:
            val1, val2 = getattr(self, name), getattr(other, name)
            if isinstance(val1, np.ndarray):
                if not np.array_equal(val1, val2):
                    return False
            elif val1 != val2:
                return False
        return True


# DictDataclass versions
DictDCDatetime = _convert_json_dataclass(DCDatetime, DictDataclass)
DictDCEnum = _convert_json_dataclass(DCEnum, DictDataclass)
DictDCRange = _convert_json_dataclass(DCRange, DictDataclass)


TEST_JSON = [
    DCEmpty(),
    DC1(3, 4.7, 'abc'),
    DC2(3, 4.7, 'abc'),
    DC1Sub(3, 4.7, 'abc'),
    DC2Sub(3, 4.7, 'abc'),
    DC3([1, 2, 3]),
    DCOptionalInt(1, 2),
    DCOptionalInt(1, None),
    DCOptionalStr('a', 'b'),
    DCOptionalStr('a', 'None'),
    DCUnion(1),
    DCUnion('a'),
    DCUnion('1'),
    DCLiteral('a'),
    DCLiteral(1),
    DCDatetime(NOW),
    DCEnum(MyEnum.a),
    DCStrEnum(MyStrEnum.a),
    DCColors(list(Color)),
    DCRange(range(1, 10, 3)),
    DCAnnotated(3, 4.7),
    DCTypedDict({'x': 3, 'y': 'a'}),
    DCUntypedNamedTuple(UntypedNamedTuple(3, 'a')),
    DCTypedNamedTuple(TypedNamedTuple(3, 'a')),
    DCAny(3),
    DCAny('a'),
    DCAny({}),
    DCAny(None),
    DCSuppress(),
    DCSuppress2(),
    DCList([DCAny(None), DCAny(1), DCAny([1]), DCAny(None), DCAny({})]),
    DCNumpy(),
]

class TestDict:
    """Unit tests for DictDataclass."""

    base_cls = DictDataclass
    ext: str = None

    def _convert_dataclass(self, tp):
        """Converts a dataclass type to have the desired base class."""
        return _convert_json_dataclass(tp, self.base_cls)

    def _coerce_object(self, obj):
        """Creates a new version of the object with the desired base class.
        Returns the class and the coerced object."""
        tp = self._convert_dataclass(type(obj))
        assert issubclass(tp, self.base_cls)
        obj = coerce_to_dataclass(tp, obj)
        assert isinstance(obj, self.base_cls)
        return (tp, obj)

    def _test_dict_round_trip(self, obj):
        """Tests round-trip conversion to/from a dict."""
        (tp, obj) = self._coerce_object(obj)
        if obj.__settings__.qualified_type:
            assert 'type' in obj.to_dict()
        else:
            assert 'type' not in obj.to_dict()
        assert tp.from_dict(obj.to_dict()) == obj

    def _get_conversion_contexts(self, err):
        if err is None:
            return (True, nullcontext(), nullcontext())
        (fwd_ok, errtype, match) = err
        err_ctx = pytest.raises(errtype, match=match)
        if fwd_ok:  # error occurs when converting back
            return (True, nullcontext(), err_ctx)
        return (False, err_ctx, nullcontext())

    def _test_dict_convert(self, obj, d, err):
        """Tests that an object gets converted to the expected dict and back."""
        (fwd_ok, fwd_ctx, bwd_ctx) = self._get_conversion_contexts(err)
        with fwd_ctx:
            assert obj.to_dict() == d
        if fwd_ok:
            with bwd_ctx:
                assert type(obj).from_dict(d) == obj

    def _test_serialize_round_trip(self, obj, tmp_path):
        """Tests round-trip conversion to/from the serialized format."""
        (tp, obj) = self._coerce_object(obj)
        ext = self.ext
        # write to text file
        path = tmp_path / f'test.{ext}'
        with open(path, 'w') as f:
            getattr(obj, f'to_{ext}')(f)
        with open(path) as f:
            obj1 = getattr(tp, f'from_{ext}')(f)
        assert obj1 == obj
        # write to binary file
        with open(path, 'wb') as f:
            getattr(obj, f'to_{ext}')(f)
        with open(path, 'rb') as f:
            obj2 = getattr(tp, f'from_{ext}')(f)
        assert obj2 == obj
        # call save/load
        obj.save(path)
        with open(path) as f:
            assert tp.load(f) == obj
        assert tp.load(path) == obj
        # convert to string
        s = getattr(obj, f'to_{ext}_string')()
        obj3 = getattr(tp, f'from_{ext}_string')(s)
        assert obj3 == obj

    def _test_serialize_convert(self, obj, s, err):
        """Tests that an object gets serialized to the expected string and back."""
        (tp, obj) = self._coerce_object(obj)
        ext = self.ext
        (fwd_ok, fwd_ctx, bwd_ctx) = self._get_conversion_contexts(err)
        with fwd_ctx:
            assert getattr(obj, f'to_{ext}_string')() == s
        if fwd_ok:
            with bwd_ctx:
                assert getattr(type(obj), f'from_{ext}_string')(s) == obj

    @pytest.mark.parametrize('obj', TEST_JSON)
    def test_dict_round_trip(self, obj):
        """Tests round-trip to dict and back."""
        self._test_dict_round_trip(obj)


class TestJSON(TestDict):
    """Unit tests for JSONDataclass."""

    base_cls = JSONDataclass
    ext = 'json'

    @pytest.mark.parametrize('obj', TEST_JSON)
    def test_dict_round_trip(self, obj):
        """Tests round-trip to dict and back."""
        self._test_dict_round_trip(obj)

    @pytest.mark.parametrize('obj', TEST_JSON)
    def test_json_round_trip(self, obj, tmp_path):
        """Tests round-trip to JSON and back."""
        self._test_serialize_round_trip(obj, tmp_path)

    @pytest.mark.parametrize(['obj', 'd'], [
        (DCEmpty(), {}),
        (DCFloat(1), {'x': 1}),
        (DCFloat(math.inf), {'x': math.inf}),
        (DCFloat(math.nan), {'x': math.nan}),
        (DCColors([Color.RED, Color.BLUE]), {'colors': [1, 4]}),
        (DCStrEnum(MyStrEnum.a), {'enum': 'a'}),
        (DCNonJSONSerializable(1, MyObject()), {'x': 1, 'obj': MyObject()}),
        (DCList([]), {'vals': []}),
        (DCList([DCAny(None)]), {'vals': [{'val': None}]}),
        (DCList([DCAny(1)]), {'vals': [{'val': 1}]}),
        (DCList([DCAny([])]), {'vals': [{'val': []}]}),
        (DCList([DCAny({})]), {'vals': [{'val': {}}]}),

    ])
    def test_dict_convert(self, obj, d):
        """Tests round-trip fidelity to/from dict."""
        self._test_dict_convert(obj, d, None)

    @pytest.mark.parametrize(['obj', 'd'], [
        (DictDCDatetime(NOW), {'dt': NOW}),
        (DCDatetime(NOW), {'dt': NOW}),
        (DictDCEnum(MyEnum.a), {'enum': MyEnum.a}),
        (DCEnum(MyEnum.a), {'enum': 1}),
        (DictDCRange(range(1, 10, 3)), {'range': range(1, 10, 3)}),
        (DCRange(range(1, 10, 3)), {'range': [1, 10, 3]}),
        (DictDCRange(range(1, 10)), {'range': range(1, 10)}),
        (DCRange(range(1, 10)), {'range': [1, 10]}),
    ])
    def test_special_types(self, obj, d):
        """Tests that DictDataclass does not do special type conversion for certain types, while JSONDataclass does."""
        self._test_dict_convert(obj, d, None)

    @pytest.mark.parametrize(['obj', 'd', 'err'], [
        (DCOptionalInt(1, 2), {'x': 1, 'y': 2}, None),
        (DCOptionalInt(1, None), {'x': 1, 'y': None}, None),
        # validation does not occur when converting to dict, only from dict
        (DCOptionalInt(None, 1), {'x': None, 'y': 1}, (True, ValueError, "could not convert None to type 'int'")),
        (DCOptionalStr('a', 'b'), {'x': 'a', 'y': 'b'}, None),
        (DCOptionalStr('a', None), {'x': 'a', 'y': None}, None),
        (DCOptionalStr(None, 'b'), {'x': None, 'y': 'b'}, (True, ValueError, "could not convert None to type 'str'")),
    ])
    def test_optional(self, obj, d, err):
        self._test_dict_convert(obj, d, err)

    @pytest.mark.parametrize(['obj', 'd', 'err'], [
        (DCLiteral(1), {'lit': 1}, None),
        (DCLiteral('b'), {'lit': 'b'}, (True, ValueError, re.escape("could not convert 'b' to type \"typing.Literal['a', 1]\""))),
    ])
    def test_literal(self, obj, d, err):
        self._test_dict_convert(obj, d, err)

    def test_datetime(self):
        obj = DCDatetime(NOW)
        d = obj.to_dict()
        s = NOW.isoformat()
        assert d == {'dt': NOW}
        # compare with dataclasses.asdict
        assert asdict(obj) == {'dt': NOW}
        assert DCDatetime.from_dict(d) == obj
        # some prefixes of full isoformat are valid
        assert DCDatetime.from_dict({'dt': NOW.strftime('%Y-%m-%dT%H:%M:%S')}).dt.isoformat() == s[:19]
        assert DCDatetime.from_dict({'dt': NOW.strftime('%Y-%m-%d')}).dt.isoformat()[:10] == s[:10]
        # other datetime formats are invalid
        with pytest.raises(ValueError, match='Invalid isoformat string'):
            DCDatetime.from_dict({'dt': NOW.strftime('%m/%d/%Y %H:%M:%S')})
        with pytest.raises(ValueError, match='Invalid isoformat string'):
            DCDatetime.from_dict({'dt': NOW.strftime('%d/%m/%Y')})

    def test_enum(self):
        obj1 = DCEnum(MyEnum.a)
        assert obj1.to_dict() == {'enum': 1}
        assert asdict(obj1) == {'enum': MyEnum.a}
        obj2 = DCStrEnum(MyStrEnum.a)
        assert obj2.to_dict() == {'enum': 'a'}
        assert asdict(obj2) == {'enum': MyStrEnum.a}
        obj3 = DCColors(list(Color))
        assert obj3.to_dict() == {'colors': [1, 2, 4]}
        assert asdict(obj3) == {'colors': list(Color)}

    def test_annotated(self):
        obj = DCAnnotated(3, 4.7)
        assert obj.to_dict() == {'x': 3, 'y': 4.7}

    def test_typed_dict(self):
        td: MyTypedDict = {'x': 3, 'y': 'a'}
        obj = DCTypedDict(td)
        assert obj.to_dict() == {'d': td}
        # invalid TypedDicts
        for d in [{'x': 3}, {'x': 3, 'y': 'a', 'z': 1}, {'x': 3, 'y': 4}, {'x': 3, 'y': None}]:
            with pytest.raises(ValueError, match="could not convert .* to type .*"):
                _ = DCTypedDict.from_dict({'d': d})

    @pytest.mark.parametrize(['obj', 'd', 'err'], [
        (DCUntypedNamedTuple(UntypedNamedTuple(3, 'a')), {'t': {'x': 3, 'y': 'a'}}, None),
        (DCTypedNamedTuple(TypedNamedTuple(3, 'a')), {'t': {'x': 3, 'y': 'a'}}, None),
        # invalid NamedTuple field (validation occurs on from_dict)
        (DCTypedNamedTuple(TypedNamedTuple(3, 4)), {'t': {'x': 3, 'y': 4}}, (True, ValueError, "could not convert 4 to type 'str'")),
    ])
    def test_namedtuple(self, obj, d, err):
        self._test_dict_convert(obj, d, err)

    def test_any(self):
        # two non-identical objects get mapped to the same dict, resulting in round-trip failure
        obj1 = DCList([DCAny(DCAny(1))])
        obj2 = DCList([DCAny({'val': 1})])
        d = {'vals': [{'val': {'val': 1}}]}
        assert obj1.to_dict() == d
        assert obj2.to_dict() == d
        assert type(obj1).from_dict(d) == obj2
        assert obj1 != obj2

    def test_subclass_json_dataclass(self):
        def _remove_type(d):
            return {key: val for (key, val) in d.items() if (key != 'type')}
        obj = DC1Sub(3, 4.7, 'abc')
        obj1 = DC1Sub.from_dict(obj.to_dict())
        assert obj1 == obj
        assert isinstance(obj1, DC1Sub)
        d = obj.to_dict()
        assert d['type'] == 'tests.test_serializable.DC1Sub'
        obj2 = DC1.from_dict(d)
        # fully qualified type is resolved to the subclass
        assert obj2 == obj
        assert isinstance(obj2, DC1Sub)
        obj3 = DC1.from_dict(_remove_type(d))
        assert isinstance(obj3, DC1)
        assert not isinstance(obj3, DC1Sub)
        d3 = obj3.to_dict()
        # objects have the same dict other than the type
        assert _remove_type(d3) == _remove_type(d)
        assert d3['type'] == 'tests.test_serializable.DC1'
        # test behavior of inheriting from JSONDataclass
        @dataclass
        class MyDC(JSONDataclass):
            pass
        assert MyDC().to_dict() == {}
        with pytest.raises(TypeError, match='you must set qualified_type=True'):
            @dataclass
            class MyDC1(MyDC):
                pass
        @dataclass
        class MyDC2(MyDC, qualified_type=True):
            pass
        # TODO: forbid local types?
        assert MyDC2().to_dict() == {'type': 'tests.test_serializable.TestJSON.test_subclass_json_dataclass.<locals>.MyDC2'}
        @dataclass
        class MyBaseDC(JSONBaseDataclass):
            pass
        @dataclass
        class MyDC3(MyBaseDC):
            pass
        assert MyDC3().to_dict() == {'type': 'tests.test_serializable.TestJSON.test_subclass_json_dataclass.<locals>.MyDC3'}
        with pytest.raises(TypeError, match='you must set qualified_type=True'):
            @dataclass
            class MyDC4(MyBaseDC, qualified_type=False):
                pass
        with pytest.raises(TypeError, match='you must set qualified_type=True'):
            @dataclass
            class MyDC5(MyDC, JSONBaseDataclass):
                pass
        @dataclass
        class MyDC6(JSONBaseDataclass, MyDC):
            pass
        @dataclass
        class MyDC7(MyDC, JSONBaseDataclass, qualified_type=True):
            pass

    def test_subclass_json_base_dataclass(self):
        """Tests JSONBaseDataclass."""
        obj = DC2Sub(3, 4.7, 'abc')
        d = obj.to_dict()
        assert d['type'] == 'tests.test_serializable.DC2Sub'
        obj1 = DC2Sub.from_dict(d)
        assert obj1 == obj
        obj2 = DC2.from_dict(d)
        assert isinstance(obj2, DC2Sub)
        assert obj2 == obj

    def test_invalid_json_obj(self):
        """Attempts to convert an object to JSON that is not JSONSerializable."""
        obj = MyObject()
        njs = DCNonJSONSerializable(3, obj)
        d = {'x': 3, 'obj': obj}
        assert njs.to_dict() == d
        # conversion from dict works OK
        assert DCNonJSONSerializable.from_dict(d) == njs
        with pytest.raises(TypeError, match='Object of type MyObject is not JSON serializable'):
            _ = njs.to_json_string()

    def test_suppress_field(self):
        """Tests behavior of setting the 'suppress' option on a field."""
        obj = DCSuppress()
        d = {'x': 1, 'z': 3}
        assert obj.to_dict() == d
        assert obj.to_dict(full=True) == d
        assert DCSuppress.from_dict(d) == obj
        obj = DCSuppress(y=100)
        assert obj.to_dict() == d
        assert obj.to_dict(full=True) == d
        assert DCSuppress.from_dict(d).y == 2
        d2 = {'z': 3}
        obj2 = DCSuppress2()
        assert obj2.to_dict() == d2
        assert obj2.to_dict(full=True) == d
        assert DCSuppress2.from_dict(d2) == obj2
        assert DCSuppress2.from_dict(d) == obj2
        obj2 = DCSuppress2(y=100)
        assert obj2.to_dict() == {'z': 3}
        assert obj2.to_dict(full=True) == d
        assert DCSuppress2.from_dict(d).y == 2

    def test_suppress_required_field(self):
        """Tests that a required field with suppress=True cannot create a valid dict."""
        @dataclass
        class DCSuppressRequired(JSONDataclass):
            x: int = field(metadata={'suppress': True})
        with pytest.raises(TypeError, match='missing 1 required positional argument'):
            _ = DCSuppressRequired()
        obj = DCSuppressRequired(1)
        assert obj.to_dict() == {}
        with pytest.raises(ValueError, match="'x' field is required"):
            _ = DCSuppressRequired.from_dict({})
        _ = DCSuppressRequired.from_dict({'x': 1})

    def test_suppress_defaults(self):
        """Tests behavior of the suppress_defaults option, both at the class level and the field level."""
        @dataclass
        class MyDC(JSONDataclass):
            x: int = 1
        assert MyDC.__settings__.suppress_defaults is True
        obj = MyDC()
        assert obj.to_dict() == {}
        assert obj.to_dict(full=True) == {'x': 1}
        obj = MyDC(2)
        assert obj.to_dict() == {'x': 2}
        assert obj.to_dict(full=True) == {'x': 2}
        @dataclass
        class MyDC(JSONDataclass, suppress_defaults=False):
            x: int = 1
        obj = MyDC()
        assert obj.to_dict() == {'x': 1}
        assert obj.to_dict(full=True) == {'x': 1}
        @dataclass
        class MyDC(JSONDataclass):
            x: int = field(default=1, metadata={'suppress_default': False})
        obj = MyDC()
        assert obj.to_dict() == {'x': 1}
        assert obj.to_dict(full=True) == {'x': 1}
        @dataclass
        class MyDC(JSONDataclass, suppress_defaults=False):
            x: int = field(default=1, metadata={'suppress_default': True})
        obj = MyDC()
        assert obj.to_dict() == {}
        assert obj.to_dict(full=True) == {'x': 1}

    def test_class_var(self):
        """Tests the behavior of ClassVars."""
        @dataclass
        class MyDC1(JSONDataclass):
            x: ClassVar[int]
        obj = MyDC1()
        assert obj.to_dict() == {}
        assert obj.to_dict(full=True) == {}
        assert MyDC1.from_dict({}) == obj
        with pytest.raises(AttributeError, match='object has no attribute'):
            _ = obj.x
        @dataclass
        class MyDC2(JSONDataclass):
            x: ClassVar[int] = field(metadata={'suppress': False})
        obj = MyDC2()
        with pytest.raises(AttributeError, match='object has no attribute'):
            _ = obj.to_dict()
        assert MyDC2.from_dict({}) == obj
        @dataclass
        class MyDC3(JSONDataclass):
            x: ClassVar[int] = 1
        obj = MyDC3()
        assert obj.to_dict() == {}
        assert obj.to_dict(full=True) == {}
        obj0 = MyDC3.from_dict({})
        assert obj0 == obj
        assert obj0.x == 1
        # ClassVar gets ignored when loading from dict
        obj1 = MyDC3.from_dict({'x': 1})
        assert obj1 == obj
        assert obj1.x == 1
        obj2 = MyDC3.from_dict({'x': 2})
        assert obj2 == obj
        assert obj2.x == 1
        MyDC3.x = 2
        obj = MyDC3()
        assert obj.to_dict() == {}
        # ClassVar field has to override with suppress=False to include it
        assert obj.to_dict(full=True) == {}
        @dataclass
        class MyDC4(JSONDataclass):
            x: ClassVar[int] = field(default=1, metadata={'suppress': False})
        obj = MyDC4()
        assert obj.to_dict() == {'x': 1}  # equals default, but suppress=False overrides it
        assert obj.to_dict(full=True) == {'x': 1}
        obj0 = MyDC4.from_dict({})
        assert obj0 == obj
        obj2 = MyDC4.from_dict({'x': 2})
        assert obj2 == obj
        assert obj2.x == 1
        MyDC4.x = 2
        obj = MyDC4()
        assert obj.to_dict() == {'x': 2}  # no longer equals default
        assert obj.to_dict(full=True) == {'x': 2}

    def test_from_dict_kwargs(self):
        """Tests behavior of from_json_string with respect to partitioning kwargs into from_dict and json.loads."""
        @dataclass
        class MyDC(JSONDataclass):
            x: int = 1
        s = '{"x": 1}'
        assert MyDC.from_json_string(s) == MyDC()
        assert MyDC.from_json_string(s, strict=True) == MyDC()
        with pytest.raises(ValueError, match="'y' is not a valid field for MyDC"):
            _ = MyDC.from_json_string('{"x": 1, "y": 2}', strict=True)
        parse_int = lambda val: int(val) + 1
        assert MyDC.from_json_string(s, parse_int=parse_int) == MyDC(2)
        assert MyDC.from_json_string(s, strict=True, parse_int=parse_int) == MyDC(2)
        with pytest.raises(TypeError, match="unexpected keyword argument 'fake_kwarg'"):
            _ = MyDC.from_json_string(s, fake_kwarg=True)


class TestTOML(TestDict):
    """Unit tests for TOMLDataclass."""

    base_cls = TOMLDataclass
    ext = 'toml'

    def _convert_dataclass(self, tp):
        tp = _convert_json_dataclass(tp, self.base_cls)
        tp.__settings__.suppress_defaults = False
        return tp

    @pytest.mark.parametrize('obj', TEST_JSON)
    def test_dict_round_trip(self, obj):
        """Tests round-trip to dict and back."""
        self._test_dict_round_trip(obj)

    @pytest.mark.parametrize('obj', TEST_JSON)
    def test_toml_round_trip(self, obj, tmp_path):
        """Tests round-trip to TOML and back."""
        self._test_serialize_round_trip(obj, tmp_path)

    @pytest.mark.parametrize(['obj', 's'], [
        (DCFloat(1), 'x = 1\n'),
        (DCFloat(1.0), 'x = 1.0\n'),
        (DCFloat(1e-12), 'x = 1e-12\n'),
        (DCFloat(math.inf), 'x = inf\n'),
        (DCFloat(math.nan), 'x = nan\n'),
    ])
    def test_float(self, obj, s):
        """Tests floating-point support."""
        self._test_serialize_convert(obj, s, None)

    @pytest.mark.parametrize(['obj', 's', 'err'], [
        (DCOptional(1), 'x = 1\n', None),
        (DCOptional(None), '', None),
        (DCOptionalDefault(1), 'x = 1\n', None),
        (DCOptionalDefault(2), 'x = 2\n', None),
        # round-trip is violated because null value is omitted and default is non-null
        (DCOptionalDefault(None), '', (True, AssertionError, '==')),
    ])
    def test_optional(self, obj, s, err):
        """Tests behavior of Optional types with TOML conversion."""
        self._test_serialize_convert(obj, s, err)

    @pytest.mark.parametrize(['obj', 's'], [
        (DCDatetime(datetime.strptime('2024-01-01', '%Y-%m-%d')), 'dt = 2024-01-01T00:00:00\n'),
    ])
    def test_datetime(self, obj, s):
        """Tests support for the datetime type."""
        self._test_serialize_convert(obj, s, None)

    @pytest.mark.parametrize(['obj', 's', 'err'], [
        (DCListOptional([]), 'vals = []\n', None),
        (DCListOptional([1, 2, 3]), 'vals = [1, 2, 3]\n', None),
        (DCListOptional([1, None, 3]), 'vals = [1, None, 3]\n', (False, ValueError, "Invalid type <class 'NoneType'>")),
    ])
    def test_list(self, obj, s, err):
        """Tests behavior of list types."""
        self._test_serialize_convert(obj, s, err)
