from dataclasses import dataclass
import json
from typing import List

import pytest

from fancy_dataclass.json import JSONBaseDataclass, JSONDataclass


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
    list: List[int]  # noqa: A003


TEST_JSON = [
    DC1(3, 4.7, 'abc'),
    DC2(3, 4.7, 'abc'),
    DC1Sub(3, 4.7, 'abc'),
    DC2Sub(3, 4.7, 'abc'),
    DC3([1, 2, 3]),
]

@pytest.mark.parametrize('obj', TEST_JSON)
def test_json_convert(obj, tmp_path):
    # write to JSON text file
    json_path = tmp_path / 'test.json'
    if isinstance(obj, JSONBaseDataclass):
        assert ('type' in obj.to_dict())
    else:
        assert ('type' not in obj.to_dict())
    with open(json_path, 'w') as f:
        obj.to_json(f)
    with open(json_path) as f:
        obj1 = type(obj).from_json(f)
    assert (obj1 == obj)
    with open(json_path, 'wb') as f:
        obj.to_json(f)
    with open(json_path, 'rb') as f:
        obj2 = type(obj).from_json(f)
    assert (obj2 == obj)
    # write to JSON binary file
    # convert to JSON string
    s = obj.to_json_string()
    assert (s == json.dumps(obj.to_dict()))
    obj3 = type(obj).from_json_string(s)
    assert (obj3 == obj)

def test_base_json_dataclass():
    obj = DC1Sub(3, 4.7, 'abc')  # regular JSONDataclass
    obj1 = DC1Sub.from_dict(obj.to_dict())
    assert (obj1 == obj)
    obj1 = DC1.from_dict(obj.to_dict())
    # objects have the same dict but are of different type
    assert (obj1.to_dict() == obj.to_dict())
    assert isinstance(obj1, DC1)
    assert (not isinstance(obj1, DC1Sub))
    assert (obj1 != obj)
    obj = DC2Sub(3, 4.7, 'abc')  # JSONBaseDataclass
    obj2 = DC2Sub.from_dict(obj.to_dict())
    assert (obj2 == obj)
    obj2 = DC2.from_dict(obj.to_dict())
    assert (obj2 == obj)
