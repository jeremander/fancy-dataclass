from dataclasses import dataclass, make_dataclass
from typing import List

import pytest

from fancy_dataclass.dict import DictDataclass, safe_dict_insert


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
class MergedComposedAB(DictDataclass, nested = False):
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
    dc = make_dataclass('TestDataclass', [('a', int), ('b', str)], bases = (DictDataclass,))
    obj = dc.from_dict({'a': 3, 'b': 'b'})
    assert isinstance(obj, dc)
    obj = dc.from_dict({'a': 3, 'b': 4})  # coercion succeeds
    assert isinstance(obj, dc)
    with pytest.raises(ValueError, match = 'invalid literal for int'):
        obj = dc.from_dict({'a': '3.7', 'b': 'b'})  # coercion fails
    # no type annotations
    dc = make_dataclass('TestDataclass', ['a', 'b'], bases = (DictDataclass,))
    obj = dc.from_dict({'a': 3, 'b': 'b'})
    assert isinstance(obj, dc)
    obj = dc.from_dict({'a': '3.7', 'b': 'b'})
    assert isinstance(obj, dc)
