from dataclasses import dataclass
from typing import List

from fancy_dataclass.json import JSONDataclass


@dataclass
class NestedComponentA(JSONDataclass):
    a1: int
    a2: float

@dataclass
class NestedComponentB(JSONDataclass):
    b1: str
    b2: List[int]

@dataclass
class NestedComposedAB(JSONDataclass):
    comp_a: NestedComponentA
    comp_b: NestedComponentB

def test_composition_nested():
    comp_a = NestedComponentA(3, 4.5)
    comp_b = NestedComponentB('b', [1, 2, 3])
    comp_ab = NestedComposedAB(comp_a, comp_b)
    assert comp_ab.to_dict() == {'comp_a' : {'a1' : 3, 'a2' : 4.5}, 'comp_b' : {'b1' : 'b', 'b2' : [1, 2, 3]}}

@dataclass
class MergedComponentA(JSONDataclass):
    a1: int
    a2: float

@dataclass
class MergedComponentB(JSONDataclass):
    b1: str
    b2: List[int]

@dataclass
class MergedComposedAB(JSONDataclass, nested = False):
    comp_a: MergedComponentA
    comp_b: MergedComponentB

def test_composition_merged():
    comp_a = MergedComponentA(3, 4.5)
    comp_b = MergedComponentB('b', [1, 2, 3])
    comp_ab = MergedComposedAB(comp_a, comp_b)
    assert comp_ab.to_dict() == {'a1' : 3, 'a2' : 4.5, 'b1' : 'b', 'b2' : [1, 2, 3]}
