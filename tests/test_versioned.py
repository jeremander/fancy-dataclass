from dataclasses import dataclass, is_dataclass

import pytest

from fancy_dataclass.versioned import VersionedDataclass, _VersionedDataclassGroup, _VersionedDataclassRegistry, version


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

def test_set_version():
    """Tests what happens when trying to set the 'version' attribute."""
    class A(VersionedDataclass, version=1):
        ...
    # NOTE: class-level setting is allowed (for now)
    A.version = 2
    a = A()
    assert a.to_dict() == {'version': 2}
    with pytest.raises(AttributeError, match="cannot assign to field 'version'"):
        a.version = 3  # type: ignore[misc]
    assert a.to_dict() == {'version': 2}

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

def test_from_dict_same_version():
    """Tests behavior of `from_dict` when the version is consistent."""
    @version(1)
    @dataclass
    class A:
        x: str
    a = A('a')
    assert A.from_dict({'version': 1, 'x': 'a'}) == a
    assert A.from_dict({'x': 'a'}) == a
    # missing required field
    with pytest.raises(ValueError, match="'x' field is required"):
        assert A.from_dict({'version': 1}) == a
    with pytest.raises(ValueError, match="'x' field is required"):
        assert A.from_dict({}) == a
    # extraneous field gets ignored
    assert A.from_dict({'version': 1, 'x': 'a', 'y': 5}) == a
    assert A.from_dict({'x': 'a', 'y': 5}) == a

def test_versioned_dataclass_group():
    """Tests behavior of `_VersionedDataclassGroup`."""
    group = _VersionedDataclassGroup('A')
    assert group.name == 'A'
    assert group.class_by_version == {}
    assert group.version_by_class == {}
    for ver in [None, 1]:
        with pytest.raises(ValueError, match="no class registered with name 'A'"):
            group.get_class(version=ver)
    # register non-VersionedDataclass
    class A:
        ...
    with pytest.raises(TypeError, match='class must be a subclass of VersionedDataclass'):
        group.register_class(1, A)
    # register class with the wrong name
    class B(VersionedDataclass, version=1):
        ...
    with pytest.raises(TypeError, match="mismatch between group name 'A' and class name 'B'"):
        group.register_class(1, B)
    class A(VersionedDataclass, version=1):
        ...
    A_v1 = A
    group.register_class(1, A_v1)
    assert group.class_by_version == {1: A_v1}
    assert group.version_by_class == {A_v1: 1}
    assert group.get_class(1) is A_v1
    assert group.get_class(None) is A_v1
    with pytest.raises(ValueError, match="no class registered with name 'A', version 2"):
        _ = group.get_class(2)
    # register same class again
    with pytest.raises(TypeError, match="class already registered with name 'A', version 1: .*A"):
        group.register_class(1, A_v1)
    with pytest.raises(TypeError, match='class .* is already registered with version 1'):
        group.register_class(2, A_v1)
    # register another class
    class A(VersionedDataclass, version=2):
        ...
    A_v2 = A
    with pytest.raises(TypeError, match="class already registered with name 'A', version 1: .*A"):
        group.register_class(1, A_v2)
    group.register_class(2, A_v2)
    assert group.class_by_version == {1: A_v1, 2: A_v2}
    assert group.version_by_class == {A_v1: 1, A_v2: 2}
    assert group.get_class(1) is A_v1
    assert group.get_class(2) is A_v2
    assert group.get_class(None) is A_v2
    with pytest.raises(ValueError, match="no class registered with name 'A', version 3"):
        _ = group.get_class(3)

def test_versioned_dataclass_registry():
    """Tests behavior of `_VersionedDataclassRegistry`."""
    reg = _VersionedDataclassRegistry()
    assert reg.groups_by_name == {}
    for ver in [None, 1]:
        with pytest.raises(ValueError, match="no class registered with name 'A'"):
            reg.get_class('A', version=ver)
    with pytest.raises(TypeError, match='class must be a subclass of VersionedDataclass'):
        reg.register_class(1, int)
    class A(VersionedDataclass, version=-1):
        ...
    A_v1 = A
    reg.register_class(1, A_v1)
    assert reg.groups_by_name == {'A': _VersionedDataclassGroup('A', {1: A_v1}, {A_v1: 1})}
    for ver in [None, 1]:
        assert reg.get_class('A', version=ver) is A_v1
    with pytest.raises(ValueError, match="no class registered with name 'B'"):
        reg.get_class('B', version=None)
    class A(VersionedDataclass, version=2):
        ...
    A_v2 = A
    reg.register_class(2, A_v2)
    assert reg.groups_by_name == {'A': _VersionedDataclassGroup('A', {1: A_v1, 2: A_v2}, {A_v1: 1, A_v2: 2})}
    assert reg.get_class('A', version=1) is A_v1
    assert reg.get_class('A', version=2) is A_v2
    assert reg.get_class('A', version=None) is A_v2
