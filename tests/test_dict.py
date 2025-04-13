from dataclasses import dataclass, field, make_dataclass
import re
from typing import ClassVar, List, Optional

import pytest
from typing_extensions import Annotated, Doc

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
class NestedList(DictDataclass):
    comps: List[NestedComponentA]

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

@dataclass
class DCSuppress(DictDataclass, suppress_defaults=False):
    cv1: ClassVar[int] = field(default=0)
    x: int = field(default=1)
    y: int = field(default=2, metadata={'suppress': True})
    z: int = field(default=3, metadata={'suppress': False})

@dataclass
class DCSuppress2(DictDataclass, suppress_defaults=True):
    cv1: ClassVar[int] = field(default=0)
    x: int = field(default=1)
    y: int = field(default=2, metadata={'suppress': True})
    z: int = field(default=3, metadata={'suppress': False})

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

def test_nested_list():
    """Tests a list of nested DictDataclasses."""
    obj = NestedList([NestedComponentA(1, 2.0), NestedComponentA(3, 4.0)])
    d = obj.to_dict()
    assert d == {'comps': [{'a1': 1, 'a2': 2.0}, {'a1': 3, 'a2': 4.0}]}
    assert NestedList.from_dict(d) == obj

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
    class DC2(DictDataclass, store_type='name'):
        x: int
    assert DC2(1).to_dict() == {'type': 'DC2', 'x': 1}
    @dataclass
    class DC3(DictDataclass, store_type='qualname'):
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
        class DC4(DictDataclass, store_type='name'):
            type: int
    with pytest.raises(TypeError, match="'type' is a reserved dict field"):
        @dataclass
        class DC5(DictDataclass, store_type='name'):
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
    # NOTE: type is in global scope, so it can be resolved from string annotation
    assert DC7.from_dict(obj.to_dict()) == obj
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
    assert DC9.from_dict(d) == obj
    # Annotated, as a string
    @dataclass
    class DC10(DictDataclass):
        x: 'Annotated[int, Doc("an int")]'
    obj = DC10(1)
    assert DC10.from_dict(obj.to_dict()) == obj

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
    class InnerLax(DictDataclass):
        x: int = 1
    @dataclass
    class InnerStrict(DictDataclass, strict=True):
        x: int = 1
    for cls in [InnerLax, InnerStrict]:
        assert cls.from_dict({}) == cls()
        assert cls.from_dict({'x': 2}) == cls(x=2)
    assert InnerLax.from_dict({'x': 1, 'y': 2}) == InnerLax()
    with pytest.raises(ValueError, match="'y' is not a valid field for InnerStrict"):
        _ = InnerStrict.from_dict({'x': 1, 'y': 2})
    @dataclass
    class OuterLaxInnerLax(DictDataclass):
        z: InnerLax
    @dataclass
    class OuterLaxInnerStrict(DictDataclass):
        z: InnerStrict
    @dataclass
    class OuterStrictInnerLax(DictDataclass, strict=True):
        z: InnerLax
    @dataclass
    class OuterStrictInnerStrict(DictDataclass, strict=True):
        z: InnerStrict
    for cls in [OuterLaxInnerLax, OuterLaxInnerStrict, OuterStrictInnerLax, OuterStrictInnerStrict]:
        inner_cls = cls.__dataclass_fields__['z'].type
        assert cls.from_dict({'z': {'x': 1}}) == cls(inner_cls())
    for cls in [OuterLaxInnerLax, OuterStrictInnerLax]:
        inner_cls = cls.__dataclass_fields__['z'].type
        assert cls.from_dict({'z': {'y': 1}}) == cls(inner_cls())
    for cls in [OuterLaxInnerStrict, OuterStrictInnerStrict]:
        inner_cls = cls.__dataclass_fields__['z'].type
        for d in [{'y': 1}, {'x': 1, 'y': 1}]:
            with pytest.raises(ValueError, match=f"'y' is not a valid field for {inner_cls.__name__}"):
                _ = cls.from_dict({'z': d})
    for cls in [OuterStrictInnerLax, OuterStrictInnerStrict]:
        with pytest.raises(ValueError, match=f"'extra' is not a valid field for {cls.__name__}"):
            _ = cls.from_dict({'z': {'x': 1}, 'extra': None})

def test_store_type_setting():
    """Tests behavior of the store_type setting."""
    # invalid mode
    with pytest.raises(ValueError, match="invalid value 'fake' for store_type mode"):
        @dataclass
        class DC1(DictDataclass, store_type='fake'):
            ...
    # 'auto' mode inherits from base class
    @dataclass
    class DC2(DictDataclass):
        ...
    @dataclass
    class DC3(DC2):
        ...
    assert DC3.__settings__.store_type == 'auto'
    assert DC3.__settings__._store_type == 'off'
    assert DC3.__settings__.should_store_type() is False
    @dataclass
    class DC4(DC2, store_type='auto'):
        ...
    assert DC4.__settings__.store_type == 'auto'
    assert DC4.__settings__._store_type == 'off'
    @dataclass
    class DC5(DC2, store_type='name'):
        ...
    assert DC5.__settings__.store_type == 'name'
    assert DC5.__settings__.should_store_type() is True
    @dataclass
    class DC6(DC5):
        ...
    assert DC6.__settings__.store_type == 'name'
    @dataclass
    class DC7(DC5, store_type='off'):
        ...
    assert DC7.__settings__.store_type == 'off'
    # other base class won't interfere
    class OtherClass:
        pass
    @dataclass
    class DC8(OtherClass, DC5):
        ...
    assert DC8.__settings__.store_type == 'name'
    # multiple inheritance with conflicting settings (uses MRO)
    class DC9(DictDataclass, store_type='qualname'):
        ...
    @dataclass
    class DC10(DC5, DC9):
        ...
    assert DC10.__settings__.store_type == 'name'
    @dataclass
    class DC11(DC9, DC5):
        ...
    assert DC11.__settings__._store_type == 'qualname'
    # multiple inheritance where one is 'auto'
    # (inherits settings from first base class, but then iterates to find non-auto)
    @dataclass
    class DC11(DC2, DC9):
        ...
    assert DC11.__settings__.store_type == 'auto'
    assert DC11.__settings__._store_type == 'qualname'
    @dataclass
    class DC12(DC9, DC2):
        ...
    assert DC12.__settings__.store_type == 'qualname'
    assert DC12.__settings__._store_type == 'qualname'

def test_suppress_field():
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
    d2 = {'z': 3}
    obj2 = DCSuppress2()
    assert obj2.to_dict() == d2
    assert obj2.to_dict(full=True) == d
    assert DCSuppress2.from_dict(d2) == obj2
    assert DCSuppress2.from_dict(d) == obj2
    obj2 = DCSuppress2(y=100)
    assert obj2.to_dict() == {'z': 3}
    assert obj2.to_dict(full=True) == d
    assert DCSuppress2.from_dict(d).y == 2

def test_suppress_required_field():
    """Tests that a required field with suppress=True cannot create a valid dict."""
    @dataclass
    class DCSuppressRequired(DictDataclass):
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
    class DC(DictDataclass):
        x: int = 1
    assert DC.__settings__.suppress_defaults is True
    obj = DC()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {'x': 1}
    obj = DC(2)
    assert obj.to_dict() == {'x': 2}
    assert obj.to_dict(full=True) == {'x': 2}
    @dataclass
    class DC(DictDataclass, suppress_defaults=False):
        x: int = 1
    obj = DC()
    assert obj.to_dict() == {'x': 1}
    assert obj.to_dict(full=True) == {'x': 1}
    @dataclass
    class DC(DictDataclass):
        x: int = field(default=1, metadata={'suppress_default': False})
    obj = DC()
    assert obj.to_dict() == {'x': 1}
    assert obj.to_dict(full=True) == {'x': 1}
    @dataclass
    class DC(DictDataclass, suppress_defaults=False):
        x: int = field(default=1, metadata={'suppress_default': True})
    obj = DC()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {'x': 1}

def test_suppress_none():
    """Tests behavior of the suppress_none option, both at the class level and the field level."""
    # class-level suppress_none
    @dataclass
    class DC(DictDataclass, suppress_none=True):
        x: Optional[int] = 1
    obj = DC(None)
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {'x': None}
    assert DC.from_dict({}) == DC(1)
    assert DC.from_dict({'x': None}) == obj
    # field-level suppress_none
    @dataclass
    class DC(DictDataclass):
        x: Optional[int] = 1
        y: Optional[int] = field(default=2, metadata={'suppress_none': True})
    obj = DC(None, None)
    assert obj.to_dict() == {'x': None}
    assert obj.to_dict(full=True) == {'x': None, 'y': None}
    assert DC.from_dict({}) == DC(1, 2)
    # field-level overrides class level
    @dataclass
    class DC(DictDataclass, suppress_none=True):
        x: Optional[int] = field(default=1, metadata={'suppress_none': False})
    assert DC(None).to_dict() == {'x': None}
    # suppress overrides suppress_none at class level
    @dataclass
    class DC(DictDataclass, suppress_none=True):
        x: Optional[int] = field(default=1, metadata={'suppress': False})
    assert DC(None).to_dict() == {'x': None}
    # suppress overrides suppress_none at field level
    @dataclass
    class DC(DictDataclass):
        x: Optional[int] = field(default=1, metadata={'suppress_none': True, 'suppress': False})
    assert DC(None).to_dict() == {'x': None}
    @dataclass
    class DC(DictDataclass):
        x: Optional[int] = field(default=1, metadata={'suppress_none': False, 'suppress': True})
    assert DC(None).to_dict() == {}
    # non-default field is fine
    @dataclass
    class DC(DictDataclass, suppress_none=True):
        x: Optional[int]
    assert DC(None).to_dict() == {}
    assert DC(1).to_dict() == {'x': 1}
    with pytest.raises(ValueError, match="'x' field is required"):
        _ = DC.from_dict({})
    # suppress_none is based on the value, not the type
    @dataclass
    class DC(DictDataclass, suppress_none=True):
        x: int
    assert DC(None).to_dict() == {}

def test_class_var():
    """Tests the behavior of ClassVars."""
    @dataclass
    class MyDC1(DictDataclass):
        x: ClassVar[int]
    obj = MyDC1()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {}
    assert MyDC1.from_dict({}) == obj
    with pytest.raises(AttributeError, match='object has no attribute'):
        _ = obj.x
    @dataclass
    class MyDC2(DictDataclass):
        x: ClassVar[int] = field(metadata={'suppress': False})
    obj = MyDC2()
    with pytest.raises(AttributeError, match='object has no attribute'):
        _ = obj.to_dict()
    assert MyDC2.from_dict({}) == obj
    @dataclass
    class MyDC3(DictDataclass):
        x: ClassVar[int] = 1
    obj = MyDC3()
    assert obj.to_dict() == {}
    assert obj.to_dict(full=True) == {}
    obj0 = MyDC3.from_dict({})
    assert obj0 == obj
    assert obj0.x == 1
    # ClassVar gets ignored when loading from dict
    obj1 = MyDC3.from_dict({'x': 1})
    assert obj1 == obj
    assert obj1.x == 1
    obj2 = MyDC3.from_dict({'x': 2})
    assert obj2 == obj
    assert obj2.x == 1
    MyDC3.x = 2
    obj = MyDC3()
    assert obj.to_dict() == {}
    # ClassVar field has to override with suppress=False to include it
    assert obj.to_dict(full=True) == {}
    @dataclass
    class MyDC4(DictDataclass):
        x: ClassVar[int] = field(default=1, metadata={'suppress': False})
    obj = MyDC4()
    assert obj.to_dict() == {'x': 1}  # equals default, but suppress=False overrides it
    assert obj.to_dict(full=True) == {'x': 1}
    obj0 = MyDC4.from_dict({})
    assert obj0 == obj
    obj2 = MyDC4.from_dict({'x': 2})
    assert obj2 == obj
    assert obj2.x == 1
    MyDC4.x = 2
    obj = MyDC4()
    assert obj.to_dict() == {'x': 2}  # no longer equals default
    assert obj.to_dict(full=True) == {'x': 2}

def test_alias():
    """Tests the 'alias' field setting for DictDataclass."""
    with pytest.raises(TypeError, match="duplicate field name or alias 'y'"):
        @dataclass
        class MyDC(DictDataclass):
            x: int = field(metadata={'alias': 'y'})
            y: int
    with pytest.raises(TypeError, match="duplicate field name or alias 'y'"):
        @dataclass
        class MyDC(DictDataclass):
            y: int
            x: int = field(metadata={'alias': 'y'})
    with pytest.raises(TypeError, match="duplicate field name or alias 'y'"):
        @dataclass
        class MyDC(DictDataclass):
            x1: int = field(metadata={'alias': 'y'})
            x2: int = field(metadata={'alias': 'y'})
    @dataclass
    class MyDC(DictDataclass):
        x: int = field(metadata={'alias': 'y'})
    obj = MyDC(3)
    assert obj == MyDC(x=3)
    assert obj.to_dict() == {'y': 3}
    assert MyDC.from_dict(obj.to_dict()) == obj
    with pytest.raises(ValueError, match=re.escape("'x' field (alias 'y') is required")):
        _ = MyDC.from_dict({'x': 4})
    assert MyDC.from_dict({'x': 4, 'y': 3}) == obj
