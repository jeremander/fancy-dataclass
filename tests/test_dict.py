from dataclasses import dataclass, make_dataclass
from typing import List, Optional

import pytest

from fancy_dataclass.dict import DictDataclass, safe_dict_insert
from fancy_dataclass.mixin import DataclassMixin


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
class FlattenedComponentA(DictDataclass):
    a1: int
    a2: float

@dataclass
class FlattenedComponentB(DictDataclass):
    b1: str
    b2: List[int]

@dataclass
class FlattenedComposedAB(DictDataclass, flattened=True):
    comp_a: FlattenedComponentA
    comp_b: FlattenedComponentB

TEST_NESTED = NestedComposedAB(
    NestedComponentA(3, 4.5),
    NestedComponentB('b', [1, 2, 3])
)

TEST_FLATTENED = FlattenedComposedAB(
    FlattenedComponentA(3, 4.5),
    FlattenedComponentB('b', [1, 2, 3])
)

def test_safe_dict_insert():
    """Tests behavior of safe_dict_insert."""
    d = {'a': 1, 'b': 2}
    safe_dict_insert(d, 'c', 3)
    with pytest.raises(ValueError, match="duplicate key 'c'"):
        safe_dict_insert(d, 'c', 3)

def test_composition_nested():
    """Tests behavior of nested components."""
    assert TEST_NESTED.to_dict() == {'comp_a' : {'a1' : 3, 'a2' : 4.5}, 'comp_b' : {'b1' : 'b', 'b2' : [1, 2, 3]}}

def test_composition_flattened():
    """Tests behavior of flattened components."""
    assert TEST_FLATTENED.to_dict() == {'a1' : 3, 'a2' : 4.5, 'b1' : 'b', 'b2' : [1, 2, 3]}

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
    """Tests behavior of the 'type' field in a DictDataclass's output dict."""
    @dataclass
    class DC1(DictDataclass):
        type: int
    assert DC1(1).to_dict() == {'type': 1}
    @dataclass
    class DC2(DictDataclass, store_type=True):
        x: int
    assert DC2(1).to_dict() == {'type': 'DC2', 'x': 1}
    @dataclass
    class DC3(DictDataclass, qualified_type=True):
        x: int
    obj: object = DC3(1)
    d = obj.to_dict()
    assert d == {'type': 'tests.test_dict.test_type_field.<locals>.DC3', 'x': 1}
    assert DC3.from_dict(d) == obj
    assert DC3.from_dict({'type': 'DC3', 'x': 1}) == obj
    with pytest.raises(ValueError, match='fake is not a known subclass of DC3'):
        _ = DC3.from_dict({'type': 'fake', 'x': 1})
    # 'type' dataclass field prohibited (this is caught at dataclass wrap time)
    with pytest.raises(TypeError, match="'type' is a reserved dict field"):
        @dataclass
        class DC4(DictDataclass, store_type=True):
            type: int
    with pytest.raises(TypeError, match="'type' is a reserved dict field"):
        @dataclass
        class DC5(DictDataclass, store_type=True):
            type: Optional[int] = None
    # string-annotated dataclass fields
    @dataclass
    class DC6(DictDataclass):
        x: 'int'
        y: 'numbers.Number'  # type: ignore[name-defined]  # noqa: F821
    obj = DC6(1, 2)
    assert DC6.from_dict(obj.to_dict()) == obj
    # globally-scoped class, as string
    @dataclass
    class DC7(DictDataclass):
        a: 'NestedComponentA'
    obj = DC7(NestedComponentA(1, 3.7))
    d = obj.to_dict()
    assert 'NestedComponentA' in globals()
    # NOTE: inner function cannot access globals/locals of higher stack frame
    with pytest.raises(NameError, match="name 'NestedComponentA' is not defined"):
        _ = DC7.from_dict(obj.to_dict())
    # fully qualified name OK
    @dataclass
    class DC8(DictDataclass):
        a: 'tests.test_dict.NestedComponentA'  # type: ignore[name-defined]  # noqa: F821
    obj = DC8(NestedComponentA(1, 3.7))
    assert DC8.from_dict(obj.to_dict()) == obj
    # locally-scoped class, as string (no way to fully qualify it)
    @dataclass
    class DC9(DictDataclass):
        x: 'DC1'
    obj = DC9(DC1(1))
    d = obj.to_dict()
    with pytest.raises(NameError, match="name 'DC1' is not defined"):
        _ = DC9.from_dict(d)

def test_flattened():
    """Tests the flattened=True option for DictDataclass."""
    @dataclass
    class DC3(DictDataclass):
        y3: int
    @dataclass
    class DC2(DictDataclass):
        x2: DC3
        y2: int
    @dataclass
    class DC1Nested(DictDataclass):
        x1: DC2
        y1: int
    obj_nested = DC1Nested(DC2(DC3(3), 2),1)
    assert obj_nested.to_dict() == {'x1': {'x2': {'y3': 3}, 'y2': 2}, 'y1': 1}
    @dataclass
    class DC1Flat(DictDataclass, flattened=True):
        x1: DC2
        y1: int
    obj_flat = DC1Flat(DC2(DC3(3),2),1)
    assert obj_flat.to_dict() == {'y1': 1, 'y2': 2, 'y3': 3}

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
