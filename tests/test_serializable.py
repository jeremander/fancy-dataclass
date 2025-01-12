from collections import namedtuple
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field, fields, make_dataclass
from datetime import datetime
from enum import Enum, Flag, auto
from io import StringIO
from json import JSONEncoder
import math
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Literal, NamedTuple, Optional, Set, TypedDict, Union

import numpy as np
import pytest
from typing_extensions import Annotated, Doc

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass, JSONSerializable
from fancy_dataclass.toml import TOMLDataclass
from fancy_dataclass.utils import coerce_to_dataclass, dataclass_type_map, issubclass_safe

from .test_dict import DCSuppress, DCSuppress2


NOW = datetime.now()


def to_json_dataclass(cls):
    """Converts a class to a JSONDataclass."""
    flds = [(fld.name, fld.type, fld) for fld in fields(cls)]
    return make_dataclass(cls.__name__, fields=flds, bases=(JSONDataclass,))

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

if sys.version_info[:2] < (3, 10):
    DCBarUnion = DCUnion
else:
    @dataclass
    class DCBarUnion(JSONDataclass):  # novermin
        x: int | str

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
class DCPath(JSONDataclass):
    path: Path

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
DictDCPath = _convert_json_dataclass(DCPath, DictDataclass)

JSONDCSuppress = to_json_dataclass(DCSuppress)
JSONDCSuppress2 = to_json_dataclass(DCSuppress2)


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
    DCBarUnion(1),
    DCBarUnion('a'),
    DCLiteral('a'),
    DCLiteral(1),
    DCDatetime(NOW),
    DCEnum(MyEnum.a),
    DCStrEnum(MyStrEnum.a),
    DCColors(list(Color)),
    DCRange(range(1, 10, 3)),
    DCPath(Path('/example/path')),
    DCAnnotated(3, 4.7),
    DCTypedDict({'x': 3, 'y': 'a'}),
    DCUntypedNamedTuple(UntypedNamedTuple(3, 'a')),
    DCTypedNamedTuple(TypedNamedTuple(3, 'a')),
    DCAny(3),
    DCAny('a'),
    DCAny({}),
    DCAny(None),
    JSONDCSuppress(),
    JSONDCSuppress2(),
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
        if obj.__settings__.should_store_type():
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
        (DictDCPath(Path('test')), {'path': Path('test')}),
        (DCPath(Path('test')), {'path': 'test'}),
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
        with pytest.raises(TypeError, match='must set store_type'):
            @dataclass
            class MyDC1(MyDC):
                pass
        @dataclass
        class MyDC2(MyDC, store_type='qualname'):
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
        with pytest.raises(TypeError, match='must set store_type'):
            @dataclass
            class MyDC4(MyBaseDC, store_type='auto'):
                pass
        with pytest.raises(TypeError, match='must set store_type'):
            @dataclass
            class MyDC5(MyDC, JSONBaseDataclass):
                pass
        @dataclass
        class MyDC6(JSONBaseDataclass, MyDC):
            pass
        @dataclass
        class MyDC7(MyDC, JSONBaseDataclass, store_type='qualname'):
            pass
        @dataclass
        class MyDC8(MyDC, store_type='off'):
            pass
        assert MyDC8().to_dict() == {}
        assert MyDC8.from_dict({}) == MyDC8()

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

    def test_from_dict_kwargs(self):
        """Tests behavior of from_json_string with respect to partitioning kwargs into from_dict and json.loads."""
        @dataclass
        class MyDC(JSONDataclass):
            x: int = 1
        @dataclass
        class MyDCStrict(JSONDataclass, strict=True):
            x: int = 1
        s = '{"x": 1}'
        assert MyDC.from_json_string(s) == MyDC()
        assert MyDCStrict.from_json_string(s) == MyDCStrict()
        with pytest.raises(ValueError, match="'y' is not a valid field for MyDC"):
            _ = MyDCStrict.from_json_string('{"x": 1, "y": 2}', strict=True)
        # kwargs like parse_int get passed to json.load
        parse_int = lambda val: int(val) + 1
        assert MyDC.from_json_string(s, parse_int=parse_int) == MyDC(2)
        assert MyDCStrict.from_json_string(s, parse_int=parse_int) == MyDCStrict(2)
        with pytest.raises(TypeError, match="unexpected keyword argument 'fake_kwarg'"):
            _ = MyDC.from_json_string(s, fake_kwarg=True)

    def test_custom_json_encoder(self):
        """Tests behavior of overriding the `json_encoder` method."""
        class MyEncoder(JSONEncoder):
            def default(self, obj: Any) -> Any:
                if isinstance(obj, set):
                    return sorted(obj)
                return super().default(obj)
        class MyClass(JSONSerializable):
            @classmethod
            def _to_json_value(cls, obj):
                return {1, 2, 3}
            @classmethod
            def _from_text_file(cls, fp, **kwargs):
                return cls()
            @classmethod
            def json_encoder(cls):
                return MyEncoder
        obj = MyClass()
        assert obj.to_json_string() == '[1, 2, 3]'
        @dataclass
        class MyDC1(JSONBaseDataclass, store_type='off', suppress_defaults=False):
            xs: Set[int] = field(default_factory=lambda: {1, 2, 3})
        @dataclass
        class MyDC2(MyDC1):
            @classmethod
            def json_encoder(cls):
                return MyEncoder
        obj1 = MyDC1()
        assert obj1.to_dict() == {'xs': {1, 2, 3}}
        with pytest.raises(TypeError, match='not JSON serializable'):
            _ = obj1.to_json_string()
        obj2 = MyDC2()
        assert obj2.to_dict() == {'xs': {1, 2, 3}}
        assert obj2.to_json_string() == '{"xs": [1, 2, 3]}'
        with StringIO() as sio:
            obj2.to_json(sio)
            assert sio.getvalue() == '{"xs": [1, 2, 3]}'


class TestTOML(TestDict):
    """Unit tests for TOMLDataclass."""

    base_cls = TOMLDataclass
    ext = 'toml'

    def _convert_dataclass(self, tp):
        tp = _convert_json_dataclass(tp, self.base_cls)
        tp.__settings__.suppress_defaults = False
        tp.__settings__.store_type = tp.__settings__._store_type = 'off'
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

    @pytest.mark.parametrize(['obj', 's'], [
        (DCAny(None), '# val = \n'),
        (DCAny(1), 'val = 1\n'),
        (DCAny([]), 'val = []\n'),
        (DCAny({}), '[val]\n'),
        (DCAny({'x': 5}), '[val]\nx = 5\n'),
    ])
    def test_any(self, obj, s):
        """Tests Any type."""
        self._test_serialize_convert(obj, s, None)

    @pytest.mark.parametrize(['obj', 's', 'err'], [
        (DCOptional(1), 'x = 1\n', None),
        (DCOptional(None), '# x = \n', None),
        (DCOptionalDefault(1), 'x = 1\n', None),
        (DCOptionalDefault(2), 'x = 2\n', None),
        # NOTE: round-trip is violated because null value is omitted and default is non-null
        (DCOptionalDefault(None), '# x = \n', (True, AssertionError, '==')),
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
        (DCList([]), 'vals = []\n', None),
        (DCList([DCAny(1)]), '[[vals]]\nval = 1\n', None),
        (DCList([DCAny('')]), '[[vals]]\nval = ""\n', None),
        (DCList([DCAny([])]), '[[vals]]\nval = []\n', None),
        (DCList([DCAny({})]), '[[vals]]\n[vals.val]\n', None),
        (DCListOptional([]), 'vals = []\n', None),
        (DCListOptional([1, 2, 3]), 'vals = [1, 2, 3]\n', None),
        (DCListOptional([1, None, 3]), 'vals = [1, None, 3]\n', (False, ValueError, "<class 'NoneType'>")),
    ])
    def test_list(self, obj, s, err):
        """Tests behavior of list types."""
        self._test_serialize_convert(obj, s, err)

    def test_nested_dict(self, tmp_path):
        """Tests serialization of a dict whose values are TOMLDataclass."""
        @dataclass
        class DCInner0(TOMLDataclass):
            ...
        @dataclass
        class DCOuter0(TOMLDataclass):
            inner: Dict[str, DCInner0]
        obj = DCOuter0({'key': DCInner0()})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '[inner.key]\n'
        obj = DCOuter0({'key1': DCInner0(), 'key2': DCInner0()})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '\n[inner.key1]\n\n[inner.key2]\n'
        @dataclass
        class DCOuter01(TOMLDataclass):
            inner: Annotated[Dict[str, DCInner0], Doc('An inner field')]
        obj = DCOuter01({'key': DCInner0()})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '\n# An inner field\n[inner.key]\n'
        obj = DCOuter01({'key1': DCInner0(), 'key2': DCInner0()})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '\n# An inner field\n\n[inner.key1]\n\n[inner.key2]\n'
        @dataclass
        class DCInner1(TOMLDataclass):
            x: int = 5
        @dataclass
        class DCOuter1(TOMLDataclass):
            inner: Dict[str, DCInner1]
        obj = DCOuter1({'key': DCInner1()})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '[inner.key]\nx = 5\n'
        obj = DCOuter1({'key1': DCInner1(1), 'key2': DCInner1(2)})
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '\n[inner.key1]\nx = 1\n\n[inner.key2]\nx = 2\n'

    def test_field_doc(self, tmp_path):
        """Tests field-level documentation in TOML serialization."""
        @dataclass
        class DCDoc(TOMLDataclass):
            a: int = 1
            b: int = field(default=2, metadata={'doc': 'b value'})
            c: Annotated[int, Doc('c value')] = 3
            d: Annotated[int, Doc('fake')] = field(default=4, metadata={'doc': 'd value'})
        obj = DCDoc()
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == 'a = 1\n# b value\nb = 2\n# c value\nc = 3\n# d value\nd = 4\n'
        @dataclass
        class DCDocOuter(TOMLDataclass):
            string: Annotated[str, Doc('a string')] = 'abc'
            nested: Annotated[DCDoc, Doc('nested object')] = field(default_factory=DCDoc)
            flag: Annotated[bool, Doc('a flag')] = False
        obj = DCDocOuter()
        self._test_serialize_round_trip(obj, tmp_path)
        # NOTE: nested gets moved to the end, to prevent parsing ambiguity
        assert obj.to_toml_string() == '# a string\nstring = "abc"\n# a flag\nflag = false\n\n# nested object\n[nested]\na = 1\n# b value\nb = 2\n# c value\nc = 3\n# d value\nd = 4\n'
        @dataclass
        class DCList(TOMLDataclass):
            vals: Annotated[List[int], Doc('a list')]
        obj = DCList([1, 2, 3])
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# a list\nvals = [1, 2, 3]\n'
        @dataclass
        class DCOptional(TOMLDataclass):
            val: Annotated[Optional[int], Doc('nullable')] = None
        obj = DCOptional()
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# nullable\n# val = \n'
        obj = DCOptional(1)
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# nullable\nval = 1\n'

    def test_top_level_doc(self, tmp_path):
        """Tests top-level comments in TOML serialization."""
        @dataclass
        class DC1(TOMLDataclass, comment='DC1'):
            x: int = 5
        obj = DC1()
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# DC1\n\nx = 5\n'
        @dataclass
        class DC2(TOMLDataclass, doc_as_comment=True):
            """DC2

Subtitle"""
            x: int = 5
        obj = DC2()
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# DC2\n\n# Subtitle\n\nx = 5\n'
        # comment with no fields
        @dataclass
        class DC3(TOMLDataclass, comment='DC3\nSubtitle'):
            ...
        obj = DC3()
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# DC3\n# Subtitle\n\n'
        # error if comment is set and doc_as_comment=True
        with pytest.raises(ValueError, match='but not both'):
            class DC4(TOMLDataclass, comment='DC4', doc_as_comment=True):
                """DC4"""
        # nested top-level comment
        @dataclass
        class DC5(TOMLDataclass, comment='DC5'):
            x: int
            nested: DC1
            y: int
        obj = DC5(4, DC1(5), 6)
        self._test_serialize_round_trip(obj, tmp_path)
        assert obj.to_toml_string() == '# DC5\n\nx = 4\ny = 6\n\n[nested]\n# DC1\n\nx = 5\n'
