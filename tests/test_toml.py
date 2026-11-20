from dataclasses import dataclass, field
from datetime import datetime
import math
from pathlib import Path
from typing import Annotated, Optional

import pytest
import tomlkit as tk
from typing_extensions import Doc

from fancy_dataclass.dict import AnyDict, DictDataclass
from fancy_dataclass.toml import TOMLDataclass
import tests.test_dict as td
import tests.test_serializable as ts

from .test_serializable import (
    NOW,
    Color,
    ErrInfo,
    MyEnum,
    MyStrEnum,
    TypedNamedTuple,
    UntypedNamedTuple,
    _TestDictFileSerializableDataclass,
)


################
# TEST CLASSES #
################

@dataclass
class DCEmpty(TOMLDataclass, ts.DCEmpty): ...

@dataclass
class DC1(TOMLDataclass, ts.DC1): ...

@dataclass
class DC2(TOMLDataclass, ts.DC2): ...

@dataclass
class DC1Sub(DC1): ...

@dataclass
class DC2Sub(DC2): ...

@dataclass
class DC3(TOMLDataclass, ts.DC3): ...

@dataclass
class DCNestedPlainObj(TOMLDataclass, ts.DCNestedPlainObj): ...

@dataclass
class DCOptional(TOMLDataclass, ts.DCOptional): ...

@dataclass
class DCOptionalDefault(TOMLDataclass, ts.DCOptionalDefault): ...

@dataclass
class DCOptionalInt(TOMLDataclass, ts.DCOptionalInt): ...

@dataclass
class DCOptionalStr(TOMLDataclass, ts.DCOptionalStr): ...

@dataclass
class DCUnion(TOMLDataclass, ts.DCUnion): ...

@dataclass
class DCBarUnion(TOMLDataclass, ts.DCBarUnion): ...

@dataclass
class DCLiteral(TOMLDataclass, ts.DCLiteral): ...

@dataclass
class DCDatetime(TOMLDataclass, ts.DCDatetime): ...

@dataclass
class DCEnum(TOMLDataclass, ts.DCEnum): ...

@dataclass
class DCStrEnum(TOMLDataclass, ts.DCStrEnum): ...

@dataclass
class DCColors(TOMLDataclass, ts.DCColors): ...

@dataclass
class DCRange(TOMLDataclass, ts.DCRange): ...

@dataclass
class DCPath(TOMLDataclass, ts.DCPath): ...

@dataclass
class DCAnnotated(TOMLDataclass, ts.DCAnnotated): ...

@dataclass
class DCTypedDict(TOMLDataclass, ts.DCTypedDict): ...

@dataclass
class DCTypedNamedTuple(TOMLDataclass, ts.DCTypedNamedTuple): ...

@dataclass
class DCUntypedNamedTuple(TOMLDataclass, ts.DCUntypedNamedTuple): ...

@dataclass
class DCAny(TOMLDataclass, ts.DCAny): ...

@dataclass(eq=False)
class DCFloat(TOMLDataclass, ts.DCFloat): ...

@dataclass
class DCSuppress(TOMLDataclass, td.DCSuppress): ...

@dataclass
class DCSuppress2(TOMLDataclass, td.DCSuppress2): ...

@dataclass
class DCList(TOMLDataclass):
    vals: list[DCAny]

@dataclass
class DCListOptional(TOMLDataclass, ts.DCListOptional): ...

@dataclass(eq=False)
class DCNumpy(TOMLDataclass, ts.DCNumpy): ...

@dataclass
class TOMLDC(TOMLDataclass):
    x: int


#########
# TESTS #
#########

TEST_TOML_DATACLASS = [
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


class TestTOMLDataclass(_TestDictFileSerializableDataclass):
    """Unit tests for TOMLDataclass."""

    base_cls = TOMLDataclass
    ext = 'toml'

    @pytest.mark.parametrize('obj', TEST_TOML_DATACLASS)
    def test_dict_round_trip(self, obj: DictDataclass) -> None:
        """Tests round-trip to dict and back."""
        assert isinstance(obj, TOMLDataclass)
        self._test_dict_round_trip(obj)

    @pytest.mark.parametrize('obj', TEST_TOML_DATACLASS)
    def test_toml_round_trip(self, tmp_path: Path, obj: TOMLDataclass) -> None:
        """Tests round-trip to TOML and back."""
        assert isinstance(obj, TOMLDataclass)
        self._test_serialize_round_trip(tmp_path, obj)

    @pytest.mark.parametrize(['obj', 's'], [
        (DCFloat(1), 'x = 1\n'),
        (DCFloat(1.0), 'x = 1.0\n'),
        (DCFloat(1e-12), 'x = 1e-12\n'),
        (DCFloat(math.inf), 'x = inf\n'),
        (DCFloat(math.nan), 'x = nan\n'),
    ])
    def test_float(self, obj: TOMLDataclass, s: str) -> None:
        """Tests floating-point support."""
        self._test_serialize_convert(obj, s, None)

    @pytest.mark.parametrize(['obj', 's'], [
        (DCAny(None), '# val = \n'),
        (DCAny(1), 'val = 1\n'),
        (DCAny([]), 'val = []\n'),
        (DCAny({}), '[val]\n'),
        (DCAny({'x': 5}), '[val]\nx = 5\n'),
    ])
    def test_any(self, obj: TOMLDataclass, s: str) -> None:
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
    def test_optional(self, obj: TOMLDataclass, s: str, err: Optional[ErrInfo]) -> None:
        """Tests behavior of Optional types with TOML conversion."""
        self._test_serialize_convert(obj, s, err)

    @pytest.mark.parametrize(['obj', 's'], [
        (DCDatetime(datetime.strptime('2024-01-01', '%Y-%m-%d')), 'dt = 2024-01-01T00:00:00\n'),
    ])
    def test_datetime(self, obj: TOMLDataclass, s: str) -> None:
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
    def test_list(self, obj: TOMLDataclass, s: str, err: Optional[ErrInfo]) -> None:
        """Tests behavior of list types."""
        self._test_serialize_convert(obj, s, err)

    def test_nested_dict(self, tmp_path: Path) -> None:
        """Tests serialization of a dict whose values are TOMLDataclass."""
        @dataclass
        class DCInner0(TOMLDataclass):
            ...
        @dataclass
        class DCOuter0(TOMLDataclass):
            inner: dict[str, DCInner0]
        obj = DCOuter0({'key': DCInner0()})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '[inner.key]\n'
        obj = DCOuter0({'key1': DCInner0(), 'key2': DCInner0()})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '[inner.key1]\n\n[inner.key2]\n'
        @dataclass
        class DCOuter01(TOMLDataclass):
            inner: Annotated[dict[str, DCInner0], Doc('An inner field')]
        obj = DCOuter01({'key': DCInner0()})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# An inner field\n[inner.key]\n'
        obj = DCOuter01({'key1': DCInner0(), 'key2': DCInner0()})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# An inner field\n\n[inner.key1]\n\n[inner.key2]\n'
        @dataclass
        class DCInner1(TOMLDataclass):
            x: int = 5
        @dataclass
        class DCOuter1(TOMLDataclass):
            inner: dict[str, DCInner1]
        obj = DCOuter1({'key': DCInner1()})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '[inner.key]\nx = 5\n'
        obj = DCOuter1({'key1': DCInner1(1), 'key2': DCInner1(2)})
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '[inner.key1]\nx = 1\n\n[inner.key2]\nx = 2\n'

    def test_field_doc(self, tmp_path: Path) -> None:
        """Tests field-level documentation in TOML serialization."""
        @dataclass
        class DCDoc(TOMLDataclass):
            a: int = 1
            b: int = field(default=2, metadata={'doc': 'b value'})
            c: Annotated[int, Doc('c value')] = 3
            d: Annotated[int, Doc('fake')] = field(default=4, metadata={'doc': 'd value'})
            # multi-line Doc strings
            e: Annotated[int, Doc('Comment Line 1\nComment Line 2')] = 5
            f: Annotated[int, Doc('Comment Line 1\nComment Line 2\n\t\n\nComment Line 3')] = 6
        obj = DCDoc()
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == (
            'a = 1\n# b value\nb = 2\n# c value\nc = 3\n# d value\nd = 4\n# Comment Line 1\n# Comment Line 2\ne = 5\n'
            '# Comment Line 1\n# Comment Line 2\n# \t\n#\n# Comment Line 3\nf = 6\n'
        )
        @dataclass
        class DCDocOuter(TOMLDataclass):
            string: Annotated[str, Doc('a string')] = 'abc'
            nested: Annotated[DCDoc, Doc('nested object')] = field(default_factory=DCDoc)
            flag: Annotated[bool, Doc('a flag')] = False
        obj = DCDocOuter()
        self._test_serialize_round_trip(tmp_path, obj)
        # NOTE: nested gets moved to the end, to prevent parsing ambiguity
        assert obj.to_toml_string() == (
            '# a string\nstring = "abc"\n# a flag\nflag = false\n\n# nested object\n[nested]\na = 1\n# b value\nb = 2\n'
            '# c value\nc = 3\n# d value\nd = 4\n# Comment Line 1\n# Comment Line 2\ne = 5\n# Comment Line 1\n'
            '# Comment Line 2\n# \t\n#\n# Comment Line 3\nf = 6\n'
        )
        @dataclass
        class DCList(TOMLDataclass):
            vals: Annotated[list[int], Doc('a list')]
        obj = DCList([1, 2, 3])
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# a list\nvals = [1, 2, 3]\n'
        @dataclass
        class DCOptional(TOMLDataclass):
            val: Annotated[Optional[int], Doc('nullable')] = None
        obj = DCOptional()
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# nullable\n# val = \n'
        obj = DCOptional(1)
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# nullable\nval = 1\n'

    def test_top_level_doc(self, tmp_path: Path) -> None:
        """Tests top-level comments in TOML serialization."""
        @dataclass
        class DC1(TOMLDataclass, comment='DC1'):
            x: int = 5
        obj = DC1()
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# DC1\n\nx = 5\n'
        @dataclass
        class DC2(TOMLDataclass, doc_as_comment=True):
            """DC2

Subtitle"""
            x: int = 5
        obj = DC2()
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# DC2\n\n# Subtitle\n\nx = 5\n'
        # comment with no fields
        @dataclass
        class DC3(TOMLDataclass, comment='DC3\nSubtitle'):
            ...
        obj = DC3()
        self._test_serialize_round_trip(tmp_path, obj)
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
        self._test_serialize_round_trip(tmp_path, obj)
        assert obj.to_toml_string() == '# DC5\n\nx = 4\ny = 6\n\n[nested]\n# DC1\n\nx = 5\n'

    @pytest.mark.parametrize(['data', 'document'], [
        (
            {},
            tk.document(),
        ),
        (
            {'x': 1},
            tk.document().add('x', 1),
        ),
        (
            {'y': 2},
            tk.document(),
        ),
        (
            {'x': 1, 'y': 2},
            tk.document().add('x', 1),
        ),
    ])
    def test_dict_to_document(self, data: AnyDict, document: tk.TOMLDocument) -> None:
        """Tests the _dict_to_document helper method."""
        result = TOMLDC._dict_to_document(data)
        assert type(result) is tk.TOMLDocument
        assert result == document
