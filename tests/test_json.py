from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, Flag, auto
import json
import re
import sys
from typing import Any, ClassVar, List, Literal, NamedTuple, Optional, TypedDict

import pytest
from typing_extensions import Annotated, Doc

from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass


NOW = datetime.now()


@dataclass
class DCEmpty(JSONDataclass):
    ...

@dataclass
class DC1(JSONDataclass):
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

@dataclass
class DCNonJSONSerializable(JSONDataclass):
    x: int
    obj: MyObject

@dataclass
class DCOptionalInt(JSONDataclass):
    x: int
    y: Optional[int]

@dataclass
class DCOptionalStr(JSONDataclass):
    x: str
    y: Optional[str]

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
    from enum import StrEnum

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
class DCAnnotated(JSONDataclass):
    x: Annotated[int, 'an integer']
    y: Annotated[float, Doc('a float')]

class MyTypedDict(TypedDict):
    x: int
    y: str

@dataclass
class DCTypedDict(JSONDataclass):
    d: MyTypedDict

MyUntypedNamedTuple = namedtuple('MyUntypedNamedTuple', ['x', 'y'])

class MyTypedNamedTuple(NamedTuple):
    x: int
    y: str

@dataclass
class DCUntypedNamedTuple(JSONDataclass):
    t: MyUntypedNamedTuple

@dataclass
class DCTypedNamedTuple(JSONDataclass):
    t: MyTypedNamedTuple

@dataclass
class DCAny(JSONDataclass):
    val: Any

@dataclass
class DCSuppress(JSONDataclass, suppress_defaults=False):
    cv1: ClassVar[int] = field(default=0)
    x: int = field(default=1)
    y: int = field(default=2, metadata={'suppress': True})
    z: int = field(default=3, metadata={'suppress': False})


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
    DCLiteral('a'),
    DCLiteral(1),
    DCDatetime(NOW),
    DCEnum(MyEnum.a),
    DCStrEnum(MyStrEnum.a),
    DCColors(list(Color)),
    DCAnnotated(3, 4.7),
    DCTypedDict({'x': 3, 'y': 'a'}),
    DCUntypedNamedTuple(MyUntypedNamedTuple(3, 'a')),
    DCTypedNamedTuple(MyTypedNamedTuple(3, 'a')),
    DCAny(3),
    DCAny('a'),
    DCAny({}),
    DCAny(None),
    DCSuppress(),
]

@pytest.mark.parametrize('obj', TEST_JSON)
def test_json_convert(obj, tmp_path):
    # write to JSON text file
    json_path = tmp_path / 'test.json'
    if isinstance(obj, JSONBaseDataclass):
        assert 'type' in obj.to_dict()
    else:
        assert 'type' not in obj.to_dict()
    with open(json_path, 'w') as f:
        obj.to_json(f)
    with open(json_path) as f:
        obj1 = type(obj).from_json(f)
    assert obj1 == obj
    # write to JSON binary file
    with open(json_path, 'wb') as f:
        obj.to_json(f)
    with open(json_path, 'rb') as f:
        obj2 = type(obj).from_json(f)
    assert obj2 == obj
    # convert to JSON string
    s = obj.to_json_string()
    assert s == json.dumps(obj.to_dict())
    obj3 = type(obj).from_json_string(s)
    assert obj3 == obj

def test_optional():
    obj: Any = DCOptionalInt(1, 2)
    d = obj.to_dict()
    assert d == {'x': 1, 'y': 2}
    assert DCOptionalInt.from_dict(d) == obj
    obj = DCOptionalInt(1, None)
    d = obj.to_dict()
    assert d == {'x': 1, 'y': None}
    assert DCOptionalInt.from_dict(d) == obj
    obj = DCOptionalInt(None, 1)  # type: ignore[arg-type]
    # validation does not occur when converting to dict, only the reverse
    d = obj.to_dict()
    assert d == {'x': None, 'y': 1}
    with pytest.raises(ValueError, match="could not convert None to type 'int'"):
        _ = DCOptionalInt.from_dict(d)
    obj = DCOptionalStr('a', 'b')
    d = obj.to_dict()
    assert d == {'x': 'a', 'y': 'b'}
    assert DCOptionalStr.from_dict(d) == obj
    obj = DCOptionalStr('a', None)
    d = obj.to_dict()
    assert d == {'x': 'a', 'y': None}
    assert DCOptionalStr.from_dict(d) == obj
    obj = DCOptionalStr(None, 'b')  # type: ignore[arg-type]
    d = obj.to_dict()
    assert d == {'x': None, 'y': 'b'}
    with pytest.raises(ValueError, match="could not convert None to type 'str'"):
        _ = DCOptionalStr.from_dict(d)

def test_literal():
    obj = DCLiteral(1)
    assert obj.to_dict() == {'lit': 1}
    obj = DCLiteral('b')  # type: ignore[arg-type]
    d = obj.to_dict()
    assert d == {'lit': 'b'}
    with pytest.raises(ValueError, match=re.escape("could not convert 'b' to type \"typing.Literal['a', 1]\"")):
        _ = DCLiteral.from_dict(d)

def test_datetime():
    obj = DCDatetime(NOW)
    d = obj.to_dict()
    s = NOW.isoformat()
    assert d == {'dt': s}
    assert DCDatetime.from_dict(d) == obj
    # some prefixes of full isoformat are valid
    assert DCDatetime.from_dict({'dt': NOW.strftime('%Y-%m-%dT%H:%M:%S')}).dt.isoformat() == s[:19]
    assert DCDatetime.from_dict({'dt': NOW.strftime('%Y-%m-%d')}).dt.isoformat()[:10] == s[:10]
    # other datetime formats are invalid
    with pytest.raises(ValueError, match='Invalid isoformat string'):
        DCDatetime.from_dict({'dt': NOW.strftime('%m/%d/%Y %H:%M:%S')})
    with pytest.raises(ValueError, match='Invalid isoformat string'):
        DCDatetime.from_dict({'dt': NOW.strftime('%d/%m/%Y')})

def test_enum():
    obj1 = DCEnum(MyEnum.a)
    assert obj1.to_dict() == {'enum': 1}
    obj2 = DCStrEnum(MyStrEnum.a)
    assert obj2.to_dict() == {'enum': 'a'}
    obj3 = DCColors(list(Color))
    assert obj3.to_dict() == {'colors': [1, 2, 4]}

def test_annotated():
    obj = DCAnnotated(3, 4.7)
    assert obj.to_dict() == {'x': 3, 'y': 4.7}

def test_typed_dict():
    td: MyTypedDict = {'x': 3, 'y': 'a'}
    obj = DCTypedDict(td)
    assert obj.to_dict() == {'d': td}
    # invalid TypedDicts
    for d in [{'x': 3}, {'x': 3, 'y': 'a', 'z': 1}, {'x': 3, 'y': 4}, {'x': 3, 'y': None}]:
        with pytest.raises(ValueError, match="could not convert .* to type .*"):
            _ = DCTypedDict.from_dict({'d': d})

def test_namedtuple():
    nt1 = MyUntypedNamedTuple(3, 'a')
    obj1 = DCUntypedNamedTuple(nt1)
    assert obj1.to_dict() == {'t': {'x': 3, 'y': 'a'}}
    nt2 = MyTypedNamedTuple(3, 'a')
    obj2 = DCTypedNamedTuple(nt2)
    assert obj2.to_dict() == {'t': {'x': 3, 'y': 'a'}}
    # invalid NamedTuple field (validation occurs on from_dict)
    nt2 = MyTypedNamedTuple(3, 4)  # type: ignore[arg-type]
    obj2 = DCTypedNamedTuple(nt2)
    d = {'t': {'x': 3, 'y': 4}}
    assert obj2.to_dict() == d
    with pytest.raises(ValueError, match="could not convert 4 to type 'str'"):
        _ = DCTypedNamedTuple.from_dict(d)

def test_subclass_json_dataclass():
    obj = DC1Sub(3, 4.7, 'abc')
    obj1 = DC1Sub.from_dict(obj.to_dict())
    assert obj1 == obj
    obj2 = DC1.from_dict(obj.to_dict())
    # objects have the same dict but are of different type
    assert obj2.to_dict() == obj.to_dict()
    assert isinstance(obj2, DC1)
    assert not isinstance(obj2, DC1Sub)
    assert obj2 != obj

def test_subclass_json_base_dataclass():
    """Tests JSONBaseDataclass."""
    obj = DC2Sub(3, 4.7, 'abc')
    obj1 = DC2Sub.from_dict(obj.to_dict())
    assert obj1 == obj
    obj2 = DC2.from_dict(obj.to_dict())
    assert obj2 == obj

def test_invalid_json_obj():
    """Attempts to convert an object to JSON that is not JSONSerializable."""
    obj = MyObject()
    njs = DCNonJSONSerializable(3, obj)
    d = {'x': 3, 'obj': obj}
    assert njs.to_dict() == d
    # conversion from dict works OK
    assert DCNonJSONSerializable.from_dict(d) == njs
    with pytest.raises(TypeError, match='Object of type MyObject is not JSON serializable'):
        _ = njs.to_json_string()

def test_suppress():
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

def test_suppress_required_field():
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

def test_suppress_defaults():
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

def test_class_var():
    """Tests the behavior of ClassVars."""
    @dataclass
    class MyDC(JSONDataclass):
        x: ClassVar[int]
    obj = MyDC()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {}
    assert MyDC.from_dict({}) == obj
    with pytest.raises(AttributeError, match='object has no attribute'):
        _ = obj.x
    @dataclass
    class MyDC(JSONDataclass):
        x: ClassVar[int] = field(metadata={'suppress': False})
    obj = MyDC()
    with pytest.raises(AttributeError, match='object has no attribute'):
        _ = obj.to_dict()
    assert MyDC.from_dict({}) == obj
    @dataclass
    class MyDC(JSONDataclass):
        x: ClassVar[int] = 1
    obj = MyDC()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {}
    obj0 = MyDC.from_dict({})
    assert obj0 == obj
    assert obj0.x == 1
    # ClassVar gets ignored when loading from dict
    obj1 = MyDC.from_dict({'x': 1})
    assert obj1 == obj
    assert obj1.x == 1
    obj2 = MyDC.from_dict({'x': 2})
    assert obj2 == obj
    assert obj2.x == 1
    MyDC.x = 2
    obj = MyDC()
    assert obj.to_dict() == {}
    # ClassVar field has to override with suppress=False to include it
    assert obj.to_dict(full=True) == {}
    @dataclass
    class MyDC(JSONDataclass):
        x: ClassVar[int] = field(default=1, metadata={'suppress': False})
    obj = MyDC()
    assert obj.to_dict() == {}  # equals default, so suppress it
    assert obj.to_dict(full=True) == {'x': 1}
    obj0 = MyDC.from_dict({})
    assert obj0 == obj
    obj2 = MyDC.from_dict({'x': 2})
    assert obj2 == obj
    assert obj2.x == 1
    MyDC.x = 2
    obj = MyDC()
    assert obj.to_dict() == {'x': 2}  # no longer equals default
    assert obj.to_dict(full=True) == {'x': 2}

def test_from_dict_kwargs():
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
