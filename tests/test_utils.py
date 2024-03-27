from dataclasses import dataclass
from typing import Optional, Union

import pytest

from fancy_dataclass.utils import DataclassMixin, DataclassMixinSettings, traverse_dataclass


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

def test_traverse_dataclass():
    """Tests depth-first traversal of dataclass fields."""
    def get_names(cls):
        return ['.'.join(path) for (path, _) in traverse_dataclass(cls)]
    # test a nested dataclass
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
    assert get_names(D) == []
    assert get_names(A) == ['a1', 'a2.b1', 'a2.b2.c1']
    class E:
        e1: int
    @dataclass
    class F:
        f1: int
        f2: E
    assert get_names(F)== ['f1', 'f2']
    msg = 'must be called with a dataclass type or instance'
    with pytest.raises(TypeError, match=msg):
        _ = get_names(int)
    with pytest.raises(TypeError, match=msg):
        _ = get_names(E)
    # duplicate leaf-level field names are OK
    @dataclass
    class H:
        g1: int
        g2: int
    @dataclass
    class G:
        g1: int
        g2: H
    assert get_names(G) == ['g1', 'g2.g1', 'g2.g2']
    @dataclass
    class J:
        j: Optional[int]
    assert get_names(J) == ['j']
    assert next(traverse_dataclass(J))[1].type is Optional[int]
    @dataclass
    class K:
        k: Union[int, str]
    assert get_names(K) == ['k']
    @dataclass
    class M:
        m: Union[K, str]
    with pytest.raises(TypeError, match='Union field cannot include a dataclass type'):
        _ = get_names(M)
    @dataclass
    class N:
        n: Union[J, K]
    with pytest.raises(TypeError, match='Union field cannot include a dataclass type'):
        _ = get_names(N)
    @dataclass
    class P:
        p: Optional[G]
    assert get_names(P) == ['p.g1', 'p.g2.g1', 'p.g2.g2']
    assert all(str(fld.type) == 'typing.Optional[int]' for (_, fld) in traverse_dataclass(P))
