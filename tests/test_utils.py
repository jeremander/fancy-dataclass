from dataclasses import astuple, dataclass, is_dataclass
from typing import ClassVar, Dict, List, Optional, Union

import pytest
from pytest import param

from fancy_dataclass.utils import DataclassMixin, DataclassMixinSettings, _flatten_dataclass, get_dataclass_fields, merge_dataclasses, traverse_dataclass


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
    (R, 'Type cannot contain a member field of its own type'),
    (S, 'Type cannot contain a ForwardRef'),
    (T, 'Type recursion exceeds depth'),
    (U, 'Type recursion exceeds depth'),
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
        ([D, D, D], []),
        ([C], ['c1']),
        ([D, C, D], ['c1']),
        ([B], ['b1', 'b2', 'b3']),
        ([B, C, D], ['b1', 'b2', 'b3', 'c1']),
        ([H, GG], ['g1', 'g2', 'g3', 'g4']),
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
        with pytest.raises(TypeError, match='must be called with a dataclass type or instance'):
            _ = merge_dataclasses(NonDC())
        with pytest.raises(TypeError, match="duplicate field name 'g1'"):
            _ = merge_dataclasses(G, H)
        with pytest.raises(TypeError, match="duplicate field name 'y'"):
            _ = merge_dataclasses(X, X2)


@dataclass
class MySettingsOpt(DataclassMixinSettings):
    enhanced: bool = False

@dataclass
class MySettingsReq(DataclassMixinSettings):
    enhanced: bool


class TestDataclassMixin:

    def test_dataclass_mixin_settings_valid(self):
        """Tests the settings instantiation mechanism of DataclassMixin."""
        class MyMixin(DataclassMixin):
            pass
        assert MyMixin.__settings_type__ is None
        assert MyMixin.__settings__ is None
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings_type__ is MySettingsOpt
        # base class instantiates the default settings from the type
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        @dataclass
        class MyDC(MyMixin):
            pass
        assert MyDC.__settings_type__ is MySettingsOpt
        assert MyDC.__settings__ == MySettingsOpt(enhanced=False)
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        # settings propagate to subclasses
        @dataclass
        class MyDCSub(MyDC):
            pass
        assert MyDCSub.__settings_type__ is MySettingsOpt
        assert MyDCSub.__settings__ == MySettingsOpt(enhanced=True)
        # can set keyword argument on the base mixin class
        @dataclass
        class MyMixin(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        # test that subclass overrides settings
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        @dataclass
        class MyDC2(MyDC, enhanced=False):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        assert MyDC2.__settings__ == MySettingsOpt(enhanced=False)
        # valid settings
        @dataclass
        class MyDC(MyMixin):
            __settings__ = MySettingsOpt(enhanced=True)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        # # __settings__ attribute conflicts with inheritance kwargs
        # @dataclass
        # class MyDC(MyMixin, enhanced=False):
        #     __settings__ = MySettings(enhanced=True)
        # assert MyDC.__settings__ == MySettings(enhanced=True)
        # can set required keyword arg on the base class
        @dataclass
        class MyMixinReq(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsReq
        @dataclass
        class MyDC(MyMixinReq):
            ...
        assert MyDC.__settings__ == MySettingsReq(enhanced=False)
        @dataclass
        class MyDC(MyMixinReq):
            __settings__ = None
        assert MyDC.__settings__ == MySettingsReq(enhanced=False)

    def test_dataclass_mixin_settings_invalid(self):
        """Tests error conditions for DataclassMixin settings."""
        class MyMixin(DataclassMixin):
            pass
        # pass unrecognized kwarg
        with pytest.raises(TypeError, match="unknown settings field 'enhanced' for MyDC1"):
            @dataclass
            class MyDC1(MyMixin, enhanced=True):
                pass
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettingsOpt
        with pytest.raises(TypeError, match="unknown settings field 'fake' for MyDC2"):
            @dataclass
            class MyDC2(MyMixin, fake=True):
                pass
        # fail to pass required setting
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
            @dataclass
            class MyMixin(DataclassMixin):
                __settings_type__ = MySettingsReq
        @dataclass
        class MyMixinReq(DataclassMixin):
            __settings_type__ = MySettingsReq
            __settings__ = MySettingsReq(enhanced=False)
        # explicitly set __settings__ attribute
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
            @dataclass
            class MyDC3(MyMixinReq):
                __settings__ = None
        with pytest.raises(TypeError, match="settings for MyDC4 missing expected field 'enhanced'"):
            @dataclass
            class MyDC4(MyMixin):
                __settings__ = 1
        # set settings to a regular class
        class NonDCSettings:
            pass
        with pytest.raises(TypeError, match='invalid settings type NonDCSettings for MyDC5'):
            @dataclass
            class MyDC5(MyMixin):
                __settings_type__ = NonDCSettings
        # set settings to a non-dataclass subclass of DataclassMixinSettings
        class NonDCSettings(DataclassMixinSettings):
            pass
        with pytest.raises(TypeError, match='NonDCSettings is not a dataclass'):
            @dataclass
            class MyDC6(MyMixin):
                __settings_type__ = NonDCSettings

    def test_dataclass_mixin_settings_merged(self):
        """Tests merging of settings when subclassing multiple DataclassMixins."""
        @dataclass
        class Settings1(DataclassMixinSettings):
            a: int = 1
        class Mixin1(DataclassMixin):
            __settings_type__ = Settings1
        @dataclass
        class Settings2(DataclassMixinSettings):
            b: int = 2
            c: int = 3
        class Mixin2(DataclassMixin):
            __settings_type__ = Settings2
        @dataclass
        class Settings3(DataclassMixinSettings):
            pass
        class Mixin3(DataclassMixin):
            __settings_type__ = Settings3
        @dataclass
        class Settings4(DataclassMixinSettings):
            b: int = 4
        def _check_stype(cls, field_names):
            assert [fld.name for fld in get_dataclass_fields(cls.__settings_type__)] == field_names
            assert isinstance(cls.__settings__, cls.__settings_type__)
        @dataclass
        class DC1(Mixin1):
            ...
        _check_stype(DC1, ['a'])
        assert DC1.__settings__.a == 1
        @dataclass
        class DC2(Mixin1, Mixin2, Mixin3):
            ...
        assert DC2.__settings_type__.__name__ == 'MiscDataclassSettings'
        _check_stype(DC2, ['a', 'b', 'c'])
        assert astuple(DC2.__settings__) == (1, 2, 3)
        @dataclass
        class DC3(Mixin1, Mixin2, Mixin3):
            __settings_type__ = None
        _check_stype(DC3, ['a', 'b', 'c'])
        assert astuple(DC3.__settings__) == (1, 2, 3)
        @dataclass
        class DC4(Mixin1, Mixin2, Mixin3):
            __settings_type__ = Settings2
        assert DC4.__settings_type__ is Settings2
        assert isinstance(DC4.__settings__, Settings2)
        _check_stype(DC4, ['b', 'c'])
        assert DC4.__settings__ == Settings2(2, 3)
        @dataclass
        class DC5(Mixin1, Mixin2, Mixin3, a=100):
            ...
        assert astuple(DC5.__settings__) == (100, 2, 3)
        with pytest.raises(TypeError, match="unknown settings field 'a' for DC6"):
            @dataclass
            class DC6(Mixin1, Mixin2, Mixin3, a=100):
                __settings_type__ = Settings2
        @dataclass
        class DC7(Mixin1, Mixin2, Mixin3, b=100):
            __settings_type__ = Settings2
        assert astuple(DC7.__settings__) == (100, 3)
        # custom settings type that accommodates all the base classes' fields
        @dataclass
        class Settings5(DataclassMixinSettings):
            a: int = 1
            b: int = 2
            c: int = 3
            d: int = 4
        @dataclass
        class DC8(Mixin1, Mixin2, Mixin3):
            __settings_type__ = Settings5
        assert DC8.__settings__ == Settings5(1, 2, 3, 4)
        @dataclass
        class DC9(Mixin1, Mixin2, Mixin3, b=100):
            __settings_type__ = Settings5
        assert DC9.__settings__ == Settings5(1, 100, 3, 4)
        @dataclass
        class DC10(Mixin1, Mixin2, Mixin3, b=50, d=100):
            __settings_type__ = Settings5
        assert DC10.__settings__ == Settings5(1, 50, 3, 100)
