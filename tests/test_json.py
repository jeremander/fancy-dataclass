from dataclasses import asdict, dataclass, field
from io import StringIO
from json import JSONEncoder
import math
from pathlib import Path
import re
from typing import IO, Any, Literal

import pytest
from typing_extensions import Self

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass, JSONSerializable
from fancy_dataclass.utils import fully_qualified_class_name
import tests.test_dict as td
import tests.test_serializable as ts

from . import raises_field_type_err
from .test_serializable import (
    NOW,
    Color,
    MyEnum,
    MyStrEnum,
    MyTypedDict,
    PlainObject,
    TypedNamedTuple,
    UntypedNamedTuple,
    _TestDictFileSerializableDataclass,
)


################
# TEST CLASSES #
################

@dataclass
class DCEmpty(JSONDataclass, ts.DCEmpty): ...

@dataclass
class DC1(JSONBaseDataclass, ts.DC1): ...

@dataclass
class DC2(JSONBaseDataclass, ts.DC2): ...

@dataclass
class DC1Sub(DC1): ...

@dataclass
class DC2Sub(DC2): ...

@dataclass
class DC3(JSONDataclass, ts.DC3): ...

@dataclass
class DCNestedPlainObj(JSONDataclass, ts.DCNestedPlainObj): ...

@dataclass
class DCOptionalInt(JSONDataclass, ts.DCOptionalInt): ...

@dataclass
class DCOptionalStr(JSONDataclass, ts.DCOptionalStr): ...

@dataclass
class DCUnion(JSONDataclass, ts.DCUnion): ...

@dataclass
class DCBarUnion(JSONDataclass, ts.DCBarUnion): ...

@dataclass
class DCLiteral(JSONDataclass, ts.DCLiteral): ...

@dataclass
class DCDatetime(JSONDataclass, ts.DCDatetime): ...

@dataclass
class DCEnum(JSONDataclass, ts.DCEnum): ...

@dataclass
class DCStrEnum(JSONDataclass, ts.DCStrEnum): ...

@dataclass
class DCColors(JSONDataclass, ts.DCColors): ...

@dataclass
class DCRange(JSONDataclass, ts.DCRange): ...

@dataclass
class DCPath(JSONDataclass, ts.DCPath): ...

@dataclass
class DCAnnotated(JSONDataclass, ts.DCAnnotated): ...

@dataclass
class DCTypedDict(JSONDataclass, ts.DCTypedDict): ...

@dataclass
class DCTypedNamedTuple(JSONDataclass, ts.DCTypedNamedTuple): ...

@dataclass
class DCUntypedNamedTuple(JSONDataclass, ts.DCUntypedNamedTuple): ...

@dataclass
class DCAny(JSONDataclass, ts.DCAny): ...

@dataclass(eq=False)
class DCFloat(JSONDataclass, ts.DCFloat): ...

@dataclass
class DCSuppress(JSONDataclass, td.DCSuppress): ...

@dataclass
class DCSuppress2(JSONDataclass, td.DCSuppress2): ...

@dataclass
class DCList(JSONDataclass):
    vals: list[DCAny]

@dataclass(eq=False)
class DCNumpy(JSONDataclass, ts.DCNumpy): ...


#########
# TESTS #
#########

TEST_JSON_DATACLASS = [
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
    DCFloat(1),
    DCFloat(1.0),
    DCFloat(1e-12),
    DCFloat(math.inf),
    DCFloat(math.nan),
    DCSuppress(),
    DCSuppress2(),
    DCList([DCAny(None), DCAny(1), DCAny([1]), DCAny(None), DCAny({})]),
    DCNumpy(),
]


class TestJSONDataclass(_TestDictFileSerializableDataclass):
    """Unit tests for JSONDataclass."""

    base_cls = JSONDataclass
    ext = 'json'

    @pytest.mark.parametrize('obj', TEST_JSON_DATACLASS)
    def test_dict_round_trip(self, obj: DictDataclass) -> None:
        """Tests round-trip to dict and back."""
        assert isinstance(obj, JSONDataclass)
        self._test_dict_round_trip(obj)

    @pytest.mark.parametrize('obj', TEST_JSON_DATACLASS)
    def test_json_round_trip(self, tmp_path: Path, obj: JSONDataclass) -> None:
        """Tests round-trip to JSON and back."""
        assert isinstance(obj, JSONDataclass)
        self._test_serialize_round_trip(tmp_path, obj)

    @pytest.mark.parametrize(['obj', 'd'], [
        (DCEmpty(), {}),
        (DCFloat(1), {'x': 1}),
        (DCFloat(math.inf), {'x': math.inf}),
        (DCFloat(math.nan), {'x': math.nan}),
        (DCColors([Color.RED, Color.BLUE]), {'colors': [1, 4]}),
        (DCStrEnum(MyStrEnum.a), {'enum': 'a'}),
        (DCNestedPlainObj(1, PlainObject()), {'x': 1, 'obj': PlainObject()}),
        (DCList([]), {'vals': []}),
        (DCList([DCAny(None)]), {'vals': [{'val': None}]}),
        (DCList([DCAny(1)]), {'vals': [{'val': 1}]}),
        (DCList([DCAny([])]), {'vals': [{'val': []}]}),
        (DCList([DCAny({})]), {'vals': [{'val': {}}]}),

    ])
    def test_dict_convert(self, obj: DictDataclass, d: dict[str, Any]) -> None:
        """Tests round-trip fidelity to/from dict."""
        self._test_dict_convert(obj, d, None)

    @pytest.mark.parametrize(['obj', 'd'], [
        (ts.DCDatetime(NOW), {'dt': NOW}),
        (DCDatetime(NOW), {'dt': NOW}),
        (ts.DCEnum(MyEnum.a), {'enum': MyEnum.a}),
        (DCEnum(MyEnum.a), {'enum': 1}),
        (ts.DCRange(range(1, 10, 3)), {'range': range(1, 10, 3)}),
        (DCRange(range(1, 10, 3)), {'range': [1, 10, 3]}),
        (ts.DCRange(range(1, 10)), {'range': range(1, 10)}),
        (DCRange(range(1, 10)), {'range': [1, 10]}),
        (ts.DCPath(Path('test')), {'path': Path('test')}),
        (DCPath(Path('test')), {'path': 'test'}),
    ])
    def test_special_types(self, obj: DictDataclass, d: dict[str, Any]) -> None:
        """Tests that DictDataclass does not do special type conversion for certain types, while JSONDataclass does."""
        self._test_dict_convert(obj, d, None)

    @pytest.mark.parametrize(['obj', 'd'], [
        (DCOptionalInt(1, 2), {'x': 1, 'y': 2}),
        (DCOptionalInt(1, None), {'x': 1, 'y': None}),
        (DCOptionalStr('a', 'b'), {'x': 'a', 'y': 'b'}),
        (DCOptionalStr('a', None), {'x': 'a', 'y': None}),
    ])
    def test_optional_valid(self, obj: DictDataclass, d: dict[str, Any]) -> None:
        """Tests an optional field, for valid examples."""
        self._test_dict_convert(obj, d, None)

    def test_optional_invalid(self) -> None:
        """Tests an optional field, for invalid examples."""
        with raises_field_type_err(DCOptionalStr, 'x', str, None):
            _ = DCOptionalStr(None, 'b')  # type: ignore[arg-type]
        obj = DCOptionalStr('a', 'b')
        object.__setattr__(obj, 'x', None)
        d = obj.to_dict()
        assert d == {'x': None, 'y': 'b'}
        with raises_field_type_err(DCOptionalStr, 'x', str, None):
            _ = DCOptionalStr.from_dict(d)

    def test_literal(self) -> None:
        self._test_dict_convert(DCLiteral(1), {'lit': 1}, None)
        with raises_field_type_err(DCLiteral, 'lit', Literal['a', 1], 'b'):
            _ = DCLiteral('b')  # type: ignore[arg-type]
        obj = DCLiteral(1)
        object.__setattr__(obj, 'lit', 'b')
        d = obj.to_dict()
        assert d == {'lit': 'b'}
        with raises_field_type_err(DCLiteral, 'lit', Literal['a', 1], 'b'):
            _ = DCLiteral.from_dict(d)

    def test_datetime(self) -> None:
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

    def test_enum(self) -> None:
        obj1 = DCEnum(MyEnum.a)
        assert obj1.to_dict() == {'enum': 1}
        assert asdict(obj1) == {'enum': MyEnum.a}
        obj2 = DCStrEnum(MyStrEnum.a)
        assert obj2.to_dict() == {'enum': 'a'}
        assert asdict(obj2) == {'enum': MyStrEnum.a}
        obj3 = DCColors(list(Color))
        assert obj3.to_dict() == {'colors': [1, 2, 4]}
        assert asdict(obj3) == {'colors': list(Color)}

    def test_annotated(self) -> None:
        obj = DCAnnotated(3, 4.7)
        assert obj.to_dict() == {'x': 3, 'y': 4.7}

    def test_typed_dict(self) -> None:
        td: MyTypedDict = {'x': 3, 'y': 'a'}
        obj = DCTypedDict(td)
        assert obj.to_dict() == {'d': td}
        # invalid TypedDicts
        for d in [{'x': 3}, {'x': 3, 'y': 'a', 'z': 1}, {'x': 3, 'y': 4}, {'x': 3, 'y': None}]:
            with raises_field_type_err(DCTypedDict, 'd', MyTypedDict, d):
                _ = DCTypedDict.from_dict({'d': d})

    @pytest.mark.parametrize(['obj', 'd'], [
        (
            DCUntypedNamedTuple(UntypedNamedTuple(3, 'a')),
            {'t': {'x': 3, 'y': 'a'}},
        ),
        (
            DCTypedNamedTuple(TypedNamedTuple(3, 'a')),
            {'t': {'x': 3, 'y': 'a'}},
        ),
    ])
    def test_namedtuple(self, obj: DictDataclass, d: dict[str, Any]) -> None:
        """Tests dict conversion with a namedtuple field, for valid examples."""
        self._test_dict_convert(obj, d, None)

    def test_namedtuple_invalid_type(self) -> None:
        """Tests dict conversion with a namedtuple field, when the namedtuple has a field of an incorrect type."""
        tup1 = TypedNamedTuple(3, 'a')
        tup2 = TypedNamedTuple(3, 4)  # type: ignore[arg-type]
        obj = DCTypedNamedTuple(tup1)
        object.__setattr__(obj, 't', tup2)
        d = obj.to_dict()
        assert d == {'t': {'x': 3, 'y': 4}}
        with raises_field_type_err(
            DCTypedNamedTuple,
            't',
            TypedNamedTuple,
            tup2,
            msg=f"attribute 'y' of {fully_qualified_class_name(TypedNamedTuple)} is not an instance of str",
        ):
             _ = DCTypedNamedTuple.from_dict(d)

    @pytest.mark.parametrize('d', [
        {'t': {'x': 3}},
        {'t': {'x': 3, 'z': 4}},
    ])
    def test_namedtuple_missing_field(self, d: dict[str, Any]) -> None:
        """Tests converting a dict to a namedtuple when one of the namedtuple fields is missing."""
        with pytest.raises(TypeError, match="missing key 'y' when converting dict to .*UntypedNamedTuple"):
            _ = DCUntypedNamedTuple.from_dict(d)

    def test_namedtuple_extraneous_field(self) -> None:
        """Tests converting a dict to a namedtuple when an extraneous field is present."""
        obj = DCUntypedNamedTuple.from_dict({'t': {'x': 3, 'y': 'a', 'z': 4}})
        assert obj.t == UntypedNamedTuple(3, 'a')

    def test_any(self) -> None:
        # two non-identical objects get mapped to the same dict, resulting in round-trip failure
        obj1 = DCList([DCAny(DCAny(1))])
        obj2 = DCList([DCAny({'val': 1})])
        d = {'vals': [{'val': {'val': 1}}]}
        assert obj1.to_dict() == d
        assert obj2.to_dict() == d
        assert type(obj1).from_dict(d) == obj2
        assert obj1 != obj2

    def test_subclass_json_dataclass(self) -> None:
        def _remove_type(d: dict[str, Any]) -> dict[str, Any]:
            return {key: val for (key, val) in d.items() if (key != 'type')}
        obj = DC1Sub(3, 4.7, 'abc')
        obj1 = DC1Sub.from_dict(obj.to_dict())
        assert obj1 == obj
        assert isinstance(obj1, DC1Sub)
        d = obj.to_dict()
        assert d['type'] == 'tests.test_json.DC1Sub'
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
        assert d3['type'] == 'tests.test_json.DC1'
        # test behavior of inheriting from JSONDataclass
        @dataclass
        class MyDC(JSONDataclass):
            pass
        settings = MyDC._dict_dataclass_settings()
        assert settings.store_type == 'off'
        assert MyDC().to_dict() == {}
        @dataclass
        class MyDC2(MyDC, store_type='qualname'):
            pass
        assert MyDC2._dict_dataclass_settings().store_type == 'qualname'
        # TODO: forbid local types?
        assert MyDC2().to_dict() == {
            'type': 'tests.test_json.TestJSONDataclass.test_subclass_json_dataclass.<locals>.MyDC2',
        }
        @dataclass
        class MyBaseDC(JSONBaseDataclass):
            pass
        @dataclass
        class MyDC3(MyBaseDC):
            pass
        assert MyDC3._dict_dataclass_settings().store_type == 'qualname'
        # inherits from JSONBaseDataclass indirectly (OK)
        @dataclass
        class MyDC4(MyBaseDC):
            pass
        assert MyDC4._dict_dataclass_settings().store_type == 'qualname'
        # inherits from JSONBaseDataclass directly
        @dataclass
        class MyDC5(MyDC, JSONBaseDataclass):
            pass
        assert MyDC5._dict_dataclass_settings().store_type == 'off'
        @dataclass
        class MyDC6(JSONBaseDataclass, MyDC):
            pass
        assert MyDC6._dict_dataclass_settings().store_type == 'qualname'
        @dataclass
        class MyDC7(MyDC, JSONBaseDataclass, store_type='qualname'):
            pass
        assert MyDC7._dict_dataclass_settings().store_type == 'qualname'
        @dataclass
        class MyDC8(MyDC, store_type='off'):
            pass
        assert MyDC8._dict_dataclass_settings().store_type == 'off'
        assert MyDC8().to_dict() == {}
        assert MyDC8.from_dict({}) == MyDC8()

    def test_subclass_json_base_dataclass(self) -> None:
        """Tests JSONBaseDataclass."""
        obj = DC2Sub(3, 4.7, 'abc')
        d = obj.to_dict()
        assert d['type'] == 'tests.test_json.DC2Sub'
        obj1 = DC2Sub.from_dict(d)
        assert obj1 == obj
        obj2 = DC2.from_dict(d)
        assert isinstance(obj2, DC2Sub)
        assert obj2 == obj

    def test_invalid_json_obj(self) -> None:
        """Attempts to convert an object to JSON that is not JSONSerializable."""
        obj = PlainObject()
        outer = DCNestedPlainObj(3, obj)
        d = {'x': 3, 'obj': obj}
        assert outer.to_dict() == d
        # conversion from dict works OK
        assert DCNestedPlainObj.from_dict(d) == outer
        with pytest.raises(TypeError, match='Object of type PlainObject is not JSON serializable'):
            _ = outer.to_json_string()

    def test_from_dict_kwargs(self) -> None:
        """Tests behavior of from_json_string with respect to partitioning kwargs into from_dict and json.loads."""
        @dataclass
        class MyDC(JSONDataclass):
            x: int = 1
        @dataclass
        class MyDCStrict(JSONDataclass, allow_extra_fields=False):
            x: int = 1
        s = '{"x": 1}'
        assert MyDC.from_json_string(s) == MyDC()
        assert MyDCStrict.from_json_string(s) == MyDCStrict()
        with pytest.raises(ValueError, match=re.escape("unknown dict fields for MyDCStrict: ['y']")):
            _ = MyDCStrict.from_json_string('{"x": 1, "y": 2}')
        # kwargs like parse_int get passed to json.load
        parse_int = lambda val: int(val) + 1
        assert MyDC.from_json_string(s, parse_int=parse_int) == MyDC(2)
        assert MyDCStrict.from_json_string(s, parse_int=parse_int) == MyDCStrict(2)
        with pytest.raises(TypeError, match="unexpected keyword argument 'fake_kwarg'"):
            _ = MyDC.from_json_string(s, fake_kwarg=True)

    def test_custom_json_encoder(self) -> None:
        """Tests behavior of overriding the `json_encoder` method."""
        class MyEncoder(JSONEncoder):
            def default(self, o: Any) -> Any:
                if isinstance(o, set):
                    return sorted(o)
                return super().default(o)
        class MyClass(JSONSerializable):
            @classmethod
            def _to_json_value(cls, obj: Self) -> Any:
                return {1, 2, 3}
            @classmethod
            def _from_text_file(cls, fp: IO[str], **kwargs: Any) -> Self:
                return cls()
            @classmethod
            def json_encoder(cls) -> type[JSONEncoder]:
                return MyEncoder
        obj = MyClass()
        assert obj.to_json_string() == '[1, 2, 3]'
        @dataclass
        class MyDC1(JSONBaseDataclass, store_type='off', suppress_defaults=False):
            xs: set[int] = field(default_factory=lambda: {1, 2, 3})
        @dataclass
        class MyDC2(MyDC1):
            @classmethod
            def json_encoder(cls) -> type[JSONEncoder]:
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
