from dataclasses import dataclass, make_dataclass
from typing import List

import pytest

from fancy_dataclass.dict import DictDataclass, safe_dict_insert
from fancy_dataclass.utils import DataclassMixin


@dataclass
class NestedComponentA(DictDataclass):
    a1: int
    a2: float

@dataclass
class NestedComponentB(DictDataclass):
    b1: str
    b2: List[int]

@dataclass
class NestedComposedAB(DictDataclass):
    comp_a: NestedComponentA
    comp_b: NestedComponentB

@dataclass
class MergedComponentA(DictDataclass):
    a1: int
    a2: float

@dataclass
class MergedComponentB(DictDataclass):
    b1: str
    b2: List[int]

@dataclass
class MergedComposedAB(DictDataclass, nested=False):
    comp_a: MergedComponentA
    comp_b: MergedComponentB

TEST_NESTED = NestedComposedAB(
    NestedComponentA(3, 4.5),
    NestedComponentB('b', [1, 2, 3])
)

TEST_MERGED = MergedComposedAB(
    MergedComponentA(3, 4.5),
    MergedComponentB('b', [1, 2, 3])
)

def test_safe_dict_insert():
    """Tests behavior of safe_dict_insert."""
    d = {'a': 1, 'b': 2}
    safe_dict_insert(d, 'c', 3)
    with pytest.raises(TypeError):
        safe_dict_insert(d, 'c', 3)

def test_composition_nested():
    """Tests behavior of merged components."""
    assert TEST_NESTED.to_dict() == {'comp_a' : {'a1' : 3, 'a2' : 4.5}, 'comp_b' : {'b1' : 'b', 'b2' : [1, 2, 3]}}

def test_composition_merged():
    """Tests behavior of merged components."""
    assert TEST_MERGED.to_dict() == {'a1' : 3, 'a2' : 4.5, 'b1' : 'b', 'b2' : [1, 2, 3]}

def test_make_dataclass():
    """Tests behavior of make_dataclass."""
    # with type annotations
    dc = make_dataclass('TestDataclass', [('a', int), ('b', str)], bases=(DictDataclass,))
    obj = dc.from_dict({'a': 3, 'b': 'b'})
    assert isinstance(obj, dc)
    assert obj.to_dict() == {'a': 3, 'b': 'b'}
    with pytest.raises(ValueError, match="could not convert 4 to type 'str'"):
        _ = dc.from_dict({'a': 3, 'b': 4})
    with pytest.raises(ValueError, match="could not convert '3.7' to type 'int'"):
        _ = dc.from_dict({'a': '3.7', 'b': 'b'})
    # no type annotations
    dc = make_dataclass('TestDataclass', ['a', 'b'], bases=(DictDataclass,))
    obj = dc.from_dict({'a': 3, 'b': 'b'})
    assert isinstance(obj, dc)
    obj = dc.from_dict({'a': '3.7', 'b': 'b'})
    assert isinstance(obj, dc)

def test_wrap_dataclass():
    """Tests behavior of wrap_dataclass."""
    class WrappedDataclass(DataclassMixin):
        pass
    WrappedCompA = WrappedDataclass.wrap_dataclass(NestedComponentA)
    assert issubclass(WrappedCompA, NestedComponentA)
    assert issubclass(WrappedCompA, WrappedDataclass)
    obj = WrappedCompA(3, 4.7)
    assert obj.to_dict() == {'a1': 3, 'a2': 4.7}

def test_type_field():
    """Tests that a DictDataclass is not permitted to have a 'type' field."""
    @dataclass
    class DCWithTypeField(DictDataclass):
        type: str
    obj = DCWithTypeField('mytype')
    with pytest.raises(ValueError, match="'type' is a reserved dict field"):
        _ = obj.to_dict()

def test_from_dict_strict():
    """Tests behavior of strict=True for DictDataclass."""
    @dataclass
    class MyDC(DictDataclass):
        x: int = 1
    assert MyDC.from_dict({}) == MyDC()
    assert MyDC.from_dict({'x': 2}) == MyDC(x=2)
    assert MyDC.from_dict({'x': 1, 'y': 2}) == MyDC()
    with pytest.raises(ValueError, match="'y' is not a valid field for MyDC"):
        _ = MyDC.from_dict({'x': 1, 'y': 2}, strict=True)
    @dataclass
    class OuterDC(DictDataclass):
        inner: MyDC
    assert OuterDC.from_dict({'inner': {'x': 1}}) == OuterDC(MyDC())
    assert OuterDC.from_dict({'inner': {'y': 1}}) == OuterDC(MyDC())
    with pytest.raises(ValueError, match="'y' is not a valid field for MyDC"):
        _ = OuterDC.from_dict({'inner': {'y': 1}}, strict=True)
    with pytest.raises(ValueError, match="'extra' is not a valid field for OuterDC"):
        OuterDC.from_dict({'inner': {'x': 1}, 'extra': None}, strict=True)
