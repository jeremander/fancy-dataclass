from dataclasses import dataclass, is_dataclass
import sys
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Union

import pytest
from pytest import param

from fancy_dataclass.utils import _flatten_dataclass, _is_instance, camel_case_to_kebab_case, coerce_to_dataclass, get_dataclass_fields, merge_dataclasses, snake_case_to_camel_case, traverse_dataclass, type_is_optional


@pytest.mark.parametrize(['snake', 'camel'], [
    ('', ''),
    ('a', 'A'),
    ('abc', 'Abc'),
    ('ABC', 'ABC'),
    ('a_b', 'AB'),
    ('a_bc', 'ABc'),
    ('AB_CD', 'ABCD'),
    ('a_', 'A'),
    ('_', ''),
    ('__', ''),
])
def test_snake_case_to_camel_case(snake, camel):
    """Tests conversion of snake case to camel case."""
    assert snake_case_to_camel_case(snake) == camel

@pytest.mark.parametrize(['camel', 'kebab'], [
    ('', ''),
    ('a', 'a'),
    ('A', 'a'),
    ('ab', 'ab'),
    ('Ab', 'ab'),
    ('AB', 'ab'),
    ('aB', 'a-b'),
    ('Abc', 'abc'),
    ('AbC', 'ab-c'),
    ('ABC', 'abc'),
    ('AbCd', 'ab-cd'),
    ('AbCD', 'ab-cd'),
    ('ABCd', 'ab-cd'),
    ('ab-cd', 'ab-cd'),
    ('Ab-C', 'ab-c'),
    ('A-bC', 'a-b-c'),
    ('a--b', 'a--b'),
    ('a_b', 'a-b'),
    ('a__b', 'a--b'),
    ('a1b', 'a1b'),
    ('a1bc', 'a1bc'),
    ('a1Bc', 'a1-bc'),
])
def test_camel_case_to_kebab_case(camel, kebab):
    """Tests conversion of camel case to kebab case."""
    assert camel_case_to_kebab_case(camel) == kebab

@pytest.mark.parametrize(['tp', 'is_optional'], [
    (int, False),
    (type(None), False),
    (Optional[int], True),
    (Optional[Optional[int]], True),
    (Union[int, Optional[float]], True),
    (Union[Optional[float], int], True),
    (Optional[type(None)], False),  # Optional[NoneType] -> NoneType
    (List[Optional[int]], False),
])
def test_type_is_optional(tp, is_optional):
    assert type_is_optional(tp) == is_optional

@pytest.mark.skipif(sys.version_info[:2] < (3, 10), reason='Py3.10 union type')
def test_type_is_optional_py310():  # novermin
    assert type_is_optional(int | None)
    assert type_is_optional(None | int)
    assert type_is_optional(None | int | str)
    assert type_is_optional(int | str | None)
    assert type_is_optional(Optional[int | str])
    assert type_is_optional(Optional[int] | str)

@pytest.mark.parametrize(['obj', 'tp', 'output'], [
    (1, int, True),
    ('a', int, False),
    (None, int, False),
    (None, type(None), True),
    (1, type(None), False),
    (1, Any, True),
    (None, Any, True),
    (1, Optional[int], True),
    (None, Optional[int], True),
    ('a', Optional[int], False),
    (1.0, int, False),
    (1, float, False),
    (1, Union[int, str], True),
    ('a', Union[int, str], True),
    (1.0, Union[int, str], False),
    ([], List[int], True),
    (1, List[int], False),
    ([1, 2], List[int], True),
    ([1, '2'], List[int], False),
    ({}, Dict[str, int], True),
    (1, Dict[str, int], False),
    ({'a': 1}, Dict[str, int], True),
    ({'a': '1'}, Dict[str, int], False),
    ({'a': 1, 2: 2}, Dict[str, int], False),
    (None, Optional[List[int]], True),
    ([1, 2], Optional[List[int]], True),
    ({}, Optional[List[int]], False),
    ((), Sequence[int], True),
    ((1, 2), Sequence[int], True),
    (None, Sequence[int], False),
    ((1, 2), Optional[Union[int, Sequence[int]]], True),
])
def test_check_isinstance(obj, tp, output):
    assert _is_instance(obj, tp) is output

def test_coerce_to_dataclass():
    """Tests behavior of `coerce_to_dataclass`."""
    @dataclass
    class DC1:
        x: int
        y: int
    @dataclass
    class DC2:
        x: int
        y: int = 1
    @dataclass
    class DC3:
        x: int
    obj1 = DC1(1, 2)
    assert coerce_to_dataclass(DC1, obj1) == obj1
    obj2 = coerce_to_dataclass(DC2, obj1)
    assert isinstance(obj2, DC2)
    assert obj1 != obj2
    assert obj2 == DC2(1, 2)
    obj3 = coerce_to_dataclass(DC3, obj1)
    assert isinstance(obj3, DC3)
    assert obj3 == DC3(1)
    assert coerce_to_dataclass(DC2, obj3) == DC2(1, 1)
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'y'"):
        _ = coerce_to_dataclass(DC1, obj3)


@dataclass
class C:
    c1: int

@dataclass
class D:
    ...

@dataclass
class B:
    b1: int
    b2: C
    b3: D

@dataclass
class A:
    a1: int
    a2: B

class E:
    e1: int

@dataclass
class F:
    f1: int
    f2: E

@dataclass
class H:
    g1: int
    g2: int

@dataclass
class G:
    g1: int
    g2: H

@dataclass
class GG:
    g3: int
    g4: H

@dataclass
class J:
    j: Optional[int]

@dataclass
class K:
    k: Union[int, str]

@dataclass
class M:
    m: Union[K, str]

@dataclass
class N:
    n: Union[J, K]

@dataclass
class P:
    p: Optional[G]

@dataclass
class Q:
    q: Optional[H]

@dataclass
class R:
    r: 'R'

@dataclass
class S:
    s: Optional['S']

@dataclass
class T:
    t: 'U'

@dataclass
class U:
    u: T

@dataclass
class V:
    v: List[C]

@dataclass
class W:
    w: Dict[str, C]

@dataclass
class X:
    x: int
    y: ClassVar[str] = 'x'

@dataclass
class X2:
    y: ClassVar[str]

@dataclass
class X3:
    x1: X
    x2: X2

@dataclass
class X4:
    x: X
    y: ClassVar[str]

DC_FLATTEN_VALID_PARAMS = [
    param(D(), [], id='empty'),
    param(C(1), ['c1'], id='one field'),
    param(H(1, 2), ['g1', 'g2'], id='two fields'),
    param(A(1, B(2, C(3), D())), ['a1', 'b1', 'c1'], id='double nested'),
    param(F(1, E()), ['f1', 'f2'], id='regular class member'),
    param(J(1), ['j'], id='optional 1'),
    param(J(None), ['j'], id='optional 2'),
    param(Q(None), ['q', 'g1', 'g2'], id='optional 3'),
    param(K(1), ['k'], id='simple union'),
    param(M('a'), ['m', 'k'], id='nested union 1'),
    param(M(K(1)), ['m', 'k'], id='nested union 2'),
    param(N(J(None)), ['j', 'k'], id='nested union 3'),
    param(V([C(1), C(2)]), ['v'], id='list of dataclasses'),
    param(W({'c1': C(1), 'c2': C(2)}), ['w'], id='dict of dataclasses'),
    param(X(1), ['x', 'y'], id='class var'),
]

DC_FLATTEN_INVALID_PARAMS = [
    (G, "duplicate key 'g1'"),
    (P, "duplicate key 'g1'"),
    (R, 'type cannot contain a member field of its own type'),
    (S, 'type cannot contain a ForwardRef'),
    (T, 'type recursion exceeds depth'),
    (U, 'type recursion exceeds depth'),
]

class TestFlatten:

    def test_traverse(self):
        """Tests depth-first traversal of dataclass fields."""
        def get_names(cls):
            return ['.'.join(path) for (path, _) in traverse_dataclass(cls)]
        # test a nested dataclass
        assert get_names(D) == []
        assert get_names(A) == ['a1', 'a2.b1', 'a2.b2.c1']
        assert get_names(F)== ['f1', 'f2']
        msg = 'must be called with a dataclass type or instance'
        with pytest.raises(TypeError, match=msg):
            _ = get_names(int)
        with pytest.raises(TypeError, match=msg):
            _ = get_names(E)
        # duplicate leaf-level field names are OK
        assert get_names(G) == ['g1', 'g2.g1', 'g2.g2']
        assert get_names(J) == ['j']
        assert next(traverse_dataclass(J))[1].type == Optional[int]
        assert get_names(K) == ['k']
        assert get_names(M) == ['m', 'm.k']
        assert get_names(N) == ['n.j', 'n.k']
        assert get_names(P) == ['p', 'p.g1', 'p.g2.g1', 'p.g2.g2']
        assert all(type_is_optional(fld.type) for (_, fld) in traverse_dataclass(P))
        assert get_names(Q) == ['q', 'q.g1', 'q.g2']
        with pytest.raises(TypeError, match='type cannot contain a member field of its own type'):
            _ = get_names(R)
        with pytest.raises(TypeError, match='type cannot contain a ForwardRef'):
            _ = get_names(S)
        with pytest.raises(TypeError, match='type recursion exceeds depth'):
            _ = get_names(T)
        with pytest.raises(TypeError, match='type recursion exceeds depth'):
            _ = get_names(U)
        assert get_names(V) == ['v']
        assert get_names(W) == ['w']
        assert get_names(X) == ['x', 'y']

    @pytest.mark.parametrize(['obj', 'flat_fields'], DC_FLATTEN_VALID_PARAMS)
    def test_flatten_valid(self, obj, flat_fields):
        def _lookup_field_by_path(obj, path):
            if not path:
                return obj
            if is_dataclass(obj):
                return _lookup_field_by_path(getattr(obj, path[0]), path[1:])
            return None
        nested_cls = type(obj)
        (field_map, conv) = _flatten_dataclass(nested_cls)
        assert nested_cls is conv.from_type
        flat_cls = conv.to_type
        assert is_dataclass(flat_cls)
        assert nested_cls.__name__ == flat_cls.__name__
        flat_obj = conv.forward(obj)
        assert isinstance(flat_obj, flat_cls)
        for (name, path) in field_map.items():
            val = getattr(flat_obj, name)
            # value could be an object in a Union, which would be None in the flattened version
            assert (val is None) or (_lookup_field_by_path(obj, path) == val)
        assert [fld.name for fld in get_dataclass_fields(flat_obj, include_classvars=True)] == flat_fields
        assert set(flat_fields) == set(field_map)
        assert conv.backward is not None
        nested_obj = conv.backward(flat_obj)
        # exceptional cases exist where the flattened representation is ambiguous
        is_ambiguous = obj in [Q(None), M('a')]
        if not is_ambiguous:
            assert nested_obj == obj
        assert nested_obj is not obj
        assert isinstance(nested_obj, nested_cls)
        flat_obj2 = conv.forward(nested_obj)
        assert flat_obj2 == flat_obj
        assert flat_obj2 is not flat_obj
        assert isinstance(flat_obj2, flat_cls)

    @pytest.mark.parametrize(['cls', 'err'], DC_FLATTEN_INVALID_PARAMS)
    def test_flatten_invalid(self, cls, err):
        """Tests various conditions where flattening a dataclass type raises an error."""
        with pytest.raises(TypeError, match=err):
            _ = _flatten_dataclass(cls)

    def test_flatten_classvar_collision(self):
        """Tests ClassVar name collisions."""
        with pytest.raises(TypeError, match="duplicate key 'y'"):
            _ = _flatten_dataclass(X3)
        with pytest.raises(TypeError, match="duplicate key 'y'"):
            _ = _flatten_dataclass(X4)


class TestMerge:

    @pytest.mark.parametrize(['classes', 'field_names'], [
        ([], []),
        ([D], []),
        ([C], ['c1']),
        ([D, C], ['c1']),
        ([B], ['b1', 'b2', 'b3']),
        # NOTE: the field ordering is rearranged from what we expect, since fields are processed in reverse MRO order
        ([B, C, D], ['b1', 'b2', 'b3', 'c1']),
        # ([B, C, D], ['c1', 'b1', 'b2', 'b3']),
        ([H, GG], ['g1', 'g2', 'g3', 'g4']),
        # ([H, GG], ['g3', 'g4', 'g1', 'g2']),
        ([X, X3], ['x', 'y', 'x1', 'x2']),
    ])
    def test_merge_valid(self, classes, field_names):
        """Merges dataclass types together and checks the resulting fields match what we expect."""
        cls = merge_dataclasses(*classes)
        assert cls.__name__ == '_'  # default name
        actual_field_names = [fld.name for fld in get_dataclass_fields(cls, include_classvars=True)]
        assert actual_field_names == field_names

    def test_merge_invalid(self):
        """Tests error conditions for merge_dataclasses."""
        with pytest.raises(TypeError, match='must be called with a dataclass type or instance'):
            _ = merge_dataclasses(None)
        class NonDC:
            pass
        with pytest.raises(TypeError, match='duplicate base class D'):
            _ = merge_dataclasses(D, D)
        with pytest.raises(TypeError, match='must be called with a dataclass type or instance'):
            _ = merge_dataclasses(NonDC())
        with pytest.raises(TypeError, match="duplicate field name 'g1'"):
            _ = merge_dataclasses(G, H)
        with pytest.raises(TypeError, match="duplicate field name 'g2' with mismatched types"):
            _ = merge_dataclasses(G, H, allow_duplicates=True)
        with pytest.raises(TypeError, match="duplicate field name 'y'"):
            _ = merge_dataclasses(X, X2)
        X3 = merge_dataclasses(X, X2, allow_duplicates=True)
        assert [fld.name for fld in get_dataclass_fields(X3, include_classvars=True)] == ['x', 'y']

    def test_merge_inheritance(self):
        @dataclass
        class DC1:
            x: int
        @dataclass
        class DC1_1:
            x: int
            y: int
        @dataclass
        class DC2(DC1):
            ...
        @dataclass
        class DC3(DC1):
            y: int
        @dataclass
        class DC4(DC2, DC3):
            ...
        @dataclass
        class DC5(DC4):
            z: int
        @dataclass
        class DC6(DC1):
            w: int
        def get_names(cls):
            return [fld.name for fld in get_dataclass_fields(cls)]
        with pytest.raises(TypeError, match="duplicate field name 'x'"):
            _ = merge_dataclasses(DC1, DC1_1)
        with pytest.raises(TypeError, match='duplicate base class DC1'):
            _ = merge_dataclasses(DC1, DC1)
        assert get_names(merge_dataclasses(DC1, DC1, bases=())) == ['x']
        with pytest.raises(TypeError, match='Cannot create a consistent'):
            _ = merge_dataclasses(DC1, DC2)
        assert get_names(merge_dataclasses(DC1, DC2, bases=())) == ['x']
        assert get_names(merge_dataclasses(DC1)) == ['x']
        assert get_names(merge_dataclasses(DC2, DC1)) == ['x']
        assert get_names(merge_dataclasses(DC2, DC3)) == ['x', 'y']
        assert get_names(merge_dataclasses(DC3, DC4, bases=())) == ['x', 'y']
        assert get_names(merge_dataclasses(DC4, DC3)) == ['x', 'y']
        assert get_names(merge_dataclasses(DC6, DC5)) == ['x', 'w', 'y', 'z']
        assert get_names(merge_dataclasses(DC1, DC2, DC3, DC4, bases=())) == ['x', 'y']
