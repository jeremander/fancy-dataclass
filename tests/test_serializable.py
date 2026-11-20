from collections import namedtuple
from contextlib import nullcontext
from dataclasses import dataclass, field, make_dataclass
from datetime import datetime
from enum import Enum, Flag, auto
import math
from pathlib import Path
import sys
from typing import Annotated, Any, Literal, NamedTuple, Optional, TypedDict, TypeVar

import numpy as np
import pytest
from typing_extensions import Doc

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.serialize import DictFileSerializableDataclass

from .test_dict import DCSuppress, DCSuppress2


D = TypeVar('D', bound=DictDataclass)
T = TypeVar('T')

ErrInfo = tuple[bool, type[Exception], str]

NOW = datetime.now()


################
# TEST CLASSES #
################

if sys.version_info[:2] < (3, 11):
    class StrEnum(str, Enum):
        pass
else:
    from enum import StrEnum  # novermin

class MyEnum(Enum):
    a = auto()
    b = auto()

class MyStrEnum(StrEnum):
    a = 'a'
    b = 'b'

class Color(Flag):
    RED = auto()
    GREEN = auto()
    BLUE = auto()

UntypedNamedTuple = namedtuple('UntypedNamedTuple', ['x', 'y'])

class TypedNamedTuple(NamedTuple):
    x: int
    y: str

class PlainObject:
    """A plain object (not a DictDataclass)."""
    def __eq__(self, other: object) -> bool:
        return isinstance(other, PlainObject)

class MyTypedDict(TypedDict):
    x: int
    y: str

# DATACLASSES

@dataclass
class DCEmpty(DictDataclass):
    ...

@dataclass
class DC1(DictDataclass):
    x: int
    y: float
    z: str

@dataclass
class DC2(DictDataclass):
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
class DC3(DictDataclass):
    list: list[int]

@dataclass
class DCNestedPlainObj(DictDataclass):
    x: int
    obj: PlainObject

@dataclass
class DCOptional(DictDataclass):
    x: Optional[int]

@dataclass
class DCOptionalDefault(DictDataclass):
    x: Optional[int] = 1

@dataclass
class DCOptionalInt(DictDataclass):
    x: int
    y: Optional[int]

@dataclass
class DCOptionalStr(DictDataclass):
    x: str
    y: Optional[str]

@dataclass
class DCUnion(DictDataclass):
    x: int | str

@dataclass
class DCBarUnion(DictDataclass):
    x: int | str

@dataclass
class DCLiteral(DictDataclass):
    lit: Literal['a', 1]

@dataclass
class DCDatetime(DictDataclass):
    dt: datetime

@dataclass
class DCEnum(DictDataclass):
    enum: MyEnum

@dataclass
class DCStrEnum(DictDataclass):
    enum: MyStrEnum

@dataclass
class DCColors(DictDataclass):
    colors: list[Color]

@dataclass
class DCRange(DictDataclass):
    range: range

@dataclass
class DCPath(DictDataclass):
    path: Path

@dataclass
class DCAnnotated(DictDataclass):
    x: Annotated[int, 'an integer']
    y: Annotated[float, Doc('a float')]

@dataclass
class DCTypedDict(DictDataclass):
    d: MyTypedDict

@dataclass
class DCUntypedNamedTuple(DictDataclass):
    t: UntypedNamedTuple

@dataclass
class DCTypedNamedTuple(DictDataclass):
    t: TypedNamedTuple

@dataclass
class DCAny(DictDataclass):
    val: Any

@dataclass
class DCFloat(DictDataclass):
    x: float
    def __eq__(self, other: object) -> bool:
        # make nan equal, for comparison testing
        return (math.isnan(self.x) and math.isnan(other.x)) or (self.x == other.x)  # type: ignore[attr-defined]

@dataclass
class DCList(DictDataclass):
    vals: list[DCAny]

@dataclass
class DCListOptional(DictDataclass):
    vals: list[Optional[int]]

@dataclass
class DCNumpy(DictDataclass, suppress_defaults=False):
    num_int: np.int64 = np.int64(1)  # noqa: RUF009
    num_float: np.float64 = np.float64(1)  # noqa: RUF009
    arr_int: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.int64))
    arr_float: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float64))
    def __eq__(self, other: object) -> bool:
        for name in self.__dataclass_fields__:
            val1, val2 = getattr(self, name), getattr(other, name)
            if isinstance(val1, np.ndarray):
                if not np.array_equal(val1, val2):
                    return False
            elif val1 != val2:
                return False
        return True


#########
# TESTS #
#########

TEST_DICT_DATACLASS = [
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


class _TestDictDataclass:
    """Base class for testing DictDataclass."""

    base_cls = DictDataclass

    def _test_dict_round_trip(self, obj: DictDataclass) -> None:
        """Tests round-trip conversion to/from a dict."""
        assert isinstance(obj, DictDataclass)
        settings = obj._dict_dataclass_settings()
        if settings.should_store_type():
            assert 'type' in obj.to_dict()
        else:
            assert 'type' not in obj.to_dict()
        assert type(obj).from_dict(obj.to_dict()) == obj

    def _get_conversion_contexts(self, err: Optional[ErrInfo]) -> tuple[bool, Any, Any]:
        if err is None:
            return (True, nullcontext(), nullcontext())
        (fwd_ok, errtype, match) = err
        err_ctx = pytest.raises(errtype, match=match)
        if fwd_ok:  # error occurs when converting back
            return (True, nullcontext(), err_ctx)
        return (False, err_ctx, nullcontext())

    def _test_dict_convert(self, obj: DictDataclass, d: dict[str, Any], err: Optional[ErrInfo]) -> None:
        """Tests that an object gets converted to the expected dict and back."""
        (fwd_ok, fwd_ctx, bwd_ctx) = self._get_conversion_contexts(err)
        with fwd_ctx:
            assert obj.to_dict() == d
        if fwd_ok:
            with bwd_ctx:
                assert type(obj).from_dict(d) == obj

    def test_float_type_int_value(self) -> None:
        """Tests that from_dict does not convert an int value to a float if the field is annotated as a float."""
        DC = make_dataclass('DC', [('x', float)], bases=(self.base_cls,))
        d = {'x': 1}
        assert type(d['x']) is int
        obj = DC.from_dict({'x': 1})  # type: ignore[attr-defined]
        assert obj.x == 1
        assert type(obj.x) is int
        self._test_dict_round_trip(obj)


class _TestDictFileSerializableDataclass(_TestDictDataclass):
    """Unit tests for DictFileSerializableDataclass."""

    ext: Optional[str] = None

    def _test_serialize_round_trip(self, tmp_path: Path, obj: DictFileSerializableDataclass) -> None:
        """Tests round-trip conversion to/from the serialized format."""
        assert isinstance(obj, DictFileSerializableDataclass)
        tp = type(obj)
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

    def _test_serialize_convert(self, obj: DictFileSerializableDataclass, s: str, err: Optional[ErrInfo]) -> None:
        """Tests that an object gets serialized to the expected string and back."""
        ext = self.ext
        (fwd_ok, fwd_ctx, bwd_ctx) = self._get_conversion_contexts(err)
        with fwd_ctx:
            assert getattr(obj, f'to_{ext}_string')() == s
        if fwd_ok:
            with bwd_ctx:
                assert getattr(type(obj), f'from_{ext}_string')(s) == obj


class TestDictDataclass(_TestDictDataclass):
    """Unit tests for DictDataclass."""

    @pytest.mark.parametrize('obj', TEST_DICT_DATACLASS)
    def test_dict_round_trip(self, obj: DictDataclass) -> None:
        """Tests round-trip to dict and back."""
        self._test_dict_round_trip(obj)
