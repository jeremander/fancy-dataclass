from dataclasses import dataclass, is_dataclass

import pytest

from fancy_dataclass.versioned import VersionedDataclass, version


def test_versioned_dataclass():
    """Tests behavior of VersionedDataclass."""
    # explicit version attribute
    class A(VersionedDataclass):
        version = 1
    assert A.version == 1
    # NOTE: unlike most other DataclassMixins, VersionedDataclass is already a dataclass type
    a = A()
    assert is_dataclass(A)
    assert is_dataclass(a)
    assert a.to_dict() == {'version': 1}
    @dataclass
    class B(VersionedDataclass):
        version = 2
        x: str
    b = B('b')
    assert is_dataclass(B)
    assert is_dataclass(b)
    assert b.to_dict() == {'version': 2, 'x': 'b'}
    # version as keyword arg (preferred)
    @dataclass
    class C(VersionedDataclass, version=3):
        x: str
    c = C('c')
    assert c.to_dict() == {'version': 3, 'x': 'c'}
    # negative version is OK
    @dataclass
    class D(VersionedDataclass, version=-1):
        x: str
    d = D('d')
    assert d.to_dict() == {'version': -1, 'x': 'd'}
    # suppress_version=True
    @dataclass
    class E(VersionedDataclass, version=4, suppress_version=True):
        x: str
    e = E('e')
    assert e.to_dict() == {'x': 'e'}

def test_missing_version():
    """Tests what happens when the version field is missing."""
    with pytest.raises(TypeError, match='must supply an integer `version` attribute'):
        class A(VersionedDataclass):
            ...

def test_invalid_version():
    """Tests what happens when the version field is not an integer."""
    with pytest.raises(TypeError, match='must supply an integer `version` attribute'):
        class A(VersionedDataclass, version=1.0):
            ...
    with pytest.raises(TypeError, match='must supply an integer `version` attribute'):
        class B(VersionedDataclass, version='3'):
            ...

def test_version_decorator():
    """Tests behavior of the `version` decorator."""
    @version(1)
    @dataclass
    class A:
        ...
    a = A()
    assert a.to_dict() == {'version': 1}
    @version(1, suppress_version=True)
    @dataclass
    class B:
        ...
    b = B()
    assert b.to_dict() == {}
    with pytest.raises(TypeError, match='C is not a dataclass'):
        @version(1)
        class C:
            ...
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'version'"):
        @version()
        @dataclass
        class D:
            ...

# def test_from_dict
