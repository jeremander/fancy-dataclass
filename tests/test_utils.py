from dataclasses import dataclass, fields, is_dataclass
from typing import Optional, Union

import pytest
from pytest import param

from fancy_dataclass.utils import DataclassMixin, DataclassMixinSettings, _flatten_dataclass, traverse_dataclass


def test_dataclass_mixin_settings():
    """Tests the settings instantiation mechanism of DataclassMixin."""
    @dataclass
    class MySettings(DataclassMixinSettings):
        enhanced: bool = False
    class MyMixin(DataclassMixin):
        pass
    assert MyMixin.__settings_type__ is None
    assert MyMixin.__settings__ is None
    with pytest.raises(TypeError, match="unknown settings field 'enhanced' for MyDC"):
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
    class MyMixin(DataclassMixin):
        __settings_type__ = MySettings
    assert MyMixin.__settings_type__ is MySettings
    # base class instantiates the default settings from the type
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    @dataclass
    class MyDC(MyMixin):  # noqa: F811
        pass
    assert MyDC.__settings_type__ is MySettings
    assert MyDC.__settings__ == MySettings(enhanced=False)
    @dataclass
    class MyDC(MyMixin, enhanced=True):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    with pytest.raises(TypeError, match="unknown settings field 'fake' for MyDC"):
        @dataclass
        class MyDC(MyMixin, fake=True):
            pass
    # test required settings
    @dataclass
    class MySettings(DataclassMixinSettings):
        enhanced: bool
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
        @dataclass
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettings
    # can set keyword argument on the base mixin class
    @dataclass
    class MyMixin(DataclassMixin, enhanced=False):
        __settings_type__ = MySettings
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    # test that subclass overrides settings
    @dataclass
    class MyDC(MyMixin, enhanced=True):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    @dataclass
    class MyDC2(MyDC, enhanced=False):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    assert MyDC2.__settings__ == MySettings(enhanced=False)
    # explicitly set __settings__ attribute
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
        @dataclass
        class MyDC(MyMixin):
            __settings__ = None
    with pytest.raises(TypeError, match='settings type of MyDC must be MySettings'):
        @dataclass
        class MyDC(MyMixin):
            __settings__ = 1
    @dataclass
    class MyDC(MyMixin):
        __settings__ = MySettings(enhanced=True)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    # inheritance kwargs override __settings__ attribute
    @dataclass
    class MyDC(MyMixin, enhanced=False):
        __settings__ = MySettings(enhanced=True)
    assert MyDC.__settings__ == MySettings(enhanced=False)

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

def test_traverse_dataclass():
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
    assert all('typing.Optional' in str(fld.type) for (_, fld) in traverse_dataclass(P))
    assert get_names(Q) == ['q', 'q.g1', 'q.g2']
    with pytest.raises(TypeError, match='Type cannot contain a member field of its own type'):
        _ = get_names(R)
    with pytest.raises(TypeError, match='Type cannot contain a ForwardRef'):
        _ = get_names(S)
    with pytest.raises(TypeError, match='Type recursion exceeds depth'):
        _ = get_names(T)
    with pytest.raises(TypeError, match='Type recursion exceeds depth'):
        _ = get_names(U)

def _lookup_field_by_path(obj, path):
    if not path:
        return obj
    if is_dataclass(obj):
        return _lookup_field_by_path(getattr(obj, path[0]), path[1:])
    return None

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
]

@pytest.mark.parametrize(['obj', 'flat_fields'], DC_FLATTEN_VALID_PARAMS)
def test_flatten_dataclass_valid(obj, flat_fields):
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
    assert [fld.name for fld in fields(flat_obj)] == flat_fields
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

DC_FLATTEN_INVALID_PARAMS = [
    (G, "duplicate key 'g1'"),
    (P, "duplicate key 'g1'"),
    (R, 'Type cannot contain a member field of its own type'),
    (S, 'Type cannot contain a ForwardRef'),
    (T, 'Type recursion exceeds depth'),
    (U, 'Type recursion exceeds depth'),
]

@pytest.mark.parametrize(['cls', 'err'], DC_FLATTEN_INVALID_PARAMS)
def test_flatten_dataclass_invalid(cls, err):
    with pytest.raises(TypeError, match=err):
        _ = _flatten_dataclass(cls)
