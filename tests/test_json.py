from dataclasses import dataclass
from datetime import datetime
from enum import Enum, Flag, auto
import json
import re
import sys
from typing import Any, List, Literal, Optional, TypedDict

import pytest
from typing_extensions import Annotated, Doc

from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass


NOW = datetime.now()


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
class NonJSONSerializable(JSONDataclass):
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


TEST_JSON = [
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
    obj = DC2Sub(3, 4.7, 'abc')
    obj1 = DC2Sub.from_dict(obj.to_dict())
    assert obj1 == obj
    obj2 = DC2.from_dict(obj.to_dict())
    assert obj2 == obj

def test_invalid_json_obj():
    """Attempts to convert an object to JSON that is not JSONSerializable."""
    obj = NonJSONSerializable(3, MyObject())
    with pytest.raises(TypeError):
        obj.to_json_string()
