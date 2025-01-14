from dataclasses import dataclass, is_dataclass
from types import ModuleType

import pytest

from fancy_dataclass.utils import MissingRequiredFieldError, fully_qualified_class_name
from fancy_dataclass.versioned import _VERSIONED_DATACLASS_REGISTRY, VersionedDataclass, _VersionedDataclassGroup, _VersionedDataclassRegistry, version


@pytest.fixture(autouse=True)
def _clear_registry() -> None:
    """Clears the global VersionedDataclass registry (does this when invoking every test function in this module)."""
    _VERSIONED_DATACLASS_REGISTRY.clear()


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
    with pytest.raises(MissingRequiredFieldError, match="'x' field is required"):
        assert A.from_dict({'version': 1}) == a
    with pytest.raises(MissingRequiredFieldError, match="'x' field is required"):
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

def test_global_versioned_dataclass_registry():
    """Tests behavior of the global `_VERSIONED_DATACLASS_REGISTRY`."""
    reg = _VERSIONED_DATACLASS_REGISTRY
    assert reg.groups_by_name == {}
    for ver in [None, 1]:
        with pytest.raises(ValueError, match="no class registered with name 'A'"):
            reg.get_class('A', version=ver)
    class A(VersionedDataclass, version=0):
        ...
    A_v0 = A
    assert reg.groups_by_name == {'A': _VersionedDataclassGroup('A', {0: A_v0}, {A_v0: 0})}
    assert reg.get_class('A', version=0) is A_v0
    assert reg.get_class('A') is A_v0
    with pytest.raises(TypeError, match="class already registered with name 'A', version 0: .*A"):
        class A(VersionedDataclass, version=0):
            ...
    @version(5)
    @dataclass
    class A:
        ...
    A_v5 = A
    assert reg.groups_by_name == {'A': _VersionedDataclassGroup('A', {0: A_v0, 5: A_v5}, {A_v0: 0, A_v5: 5})}
    assert reg.get_class('A', version=5) is A_v5
    assert reg.get_class('A') is A_v5
    # simulate importing from a module
    src1 = """
from fancy_dataclass.versioned import VersionedDataclass
class A(VersionedDataclass, version=1):
    ...
    """
    mod1 = ModuleType('mod1')
    exec(src1, mod1.__dict__)
    A_v1 = reg.get_class('A', 1)
    assert issubclass(A_v1, VersionedDataclass)
    assert A_v1.__module__ == 'mod1'
    assert fully_qualified_class_name(A_v1) == 'mod1.A'
    mod2 = ModuleType('mod2')
    with pytest.raises(TypeError, match="class already registered with name 'A', version 1: mod2.A"):
        exec(src1, mod2.__dict__)
    src2 = """
from dataclasses import dataclass
from fancy_dataclass.versioned import version
@version(2)
@dataclass
class A:
    ...
    """
    exec(src2, mod2.__dict__)
    A_v2 = reg.get_class('A', 2)
    assert issubclass(A_v2, VersionedDataclass)
    assert A_v2.__module__ == 'mod2'
    assert fully_qualified_class_name(A_v2) == 'mod2.A'

def test_migrate():
    """Tests migration behavior."""
    @version(1)
    @dataclass
    class A:
        x: int
    A1 = A
    a1 = A(1)
    # version 2 adds a field
    @version(2)
    @dataclass
    class A:
        x: int
        y: str = 'a'
    A2 = A
    a2 = A(2, '2')
    # version 3 renames a field
    @version(3)
    @dataclass
    class A:
        x: int
        z: str = 'a'
    A3 = A
    # version 4 subtracts a field
    @version(4)
    @dataclass
    class A:
        x: int
    A4 = A
    a4 = A(4)
    # version 1 migration
    assert a1.migrate(version=1) is a1
    assert isinstance(a1.migrate(version=2), A2)
    assert a1.migrate(version=2) == A2(1, 'a')
    assert isinstance(a1.migrate(version=3), A3)
    assert a1.migrate(version=3) == A3(1, 'a')
    for ver in [4, None]:
        assert isinstance(a1.migrate(version=ver), A4)
        assert a1.migrate(version=ver) == A4(1)
    # version 2 migration
    assert isinstance(a2.migrate(version=1), A1)
    assert a2.migrate(version=1) == A1(2)
    assert a2.migrate(version=2) is a2
    assert isinstance(a2.migrate(version=3), A3)
    assert a2.migrate(version=3) == A3(2, 'a')
    for ver in [4, None]:
        assert isinstance(a2.migrate(version=ver), A4)
        assert a2.migrate(version=ver) == A4(2)
    # version 4 migration
    assert isinstance(a4.migrate(version=1), A1)
    assert a4.migrate(version=1) == A1(4)
    assert isinstance(a4.migrate(version=2), A2)
    assert a4.migrate(version=2) == A2(4, 'a')
    for ver in [4, None]:
        assert a4.migrate(version=ver) is a4
    # remove required field
    @version(5)
    @dataclass
    class A:
        ...
    A5 = A
    a5 = A()
    for obj in [a1, a2, a4]:
        assert isinstance(obj.migrate(version=5), A5)
        assert obj.migrate(version=5) == a5
        with pytest.raises(MissingRequiredFieldError, match="'x' field is required"):
            _ = a5.migrate(version=obj.version)
    with pytest.raises(ValueError, match="no class registered with name 'A', version 6"):
        _ = a5.migrate(version=6)

def test_migrate_nested():
    """Tests migration of nested VersionedDataclass types."""
    @version(1)
    @dataclass
    class Inner:
        ...
    Inner1 = Inner
    @version(1)
    @dataclass
    class Outer:
        inner: Inner
    Outer1 = Outer
    @version(2)
    @dataclass
    class Inner:
        ...
    Inner2 = Inner
    @version(2)
    @dataclass
    class Outer:
        inner: Inner
    Outer2 = Outer
    obj1 = Outer1(Inner1())
    obj2 = Outer2(Inner2())
    assert obj1.to_dict() == {'version': 1, 'inner': {'version': 1}}
    assert obj2.to_dict() == {'version': 2, 'inner': {'version': 2}}
    assert obj1 != obj2
    obj12 = obj1.migrate()
    assert isinstance(obj12, Outer2)
    assert isinstance(obj12.inner, Inner2)
    assert obj12 == obj2

def test_from_dict():
    """Tests behavior of `VersionedDataclass.from_dict`."""
    @version(1)
    @dataclass
    class A:
        x: int
        y: str = 'a'
    A1 = A
    a1 = A1(1)
    d1 = {'version': 1, 'x': 1}
    @version(2)
    @dataclass
    class A:
        x: int
        y: str = 'b'
        z: float = 3.14
    A2 = A
    a2 = A2(2, z=7.0)
    d2 = {'version': 2, 'x': 2, 'z': 7.0}
    @version(3)
    @dataclass
    class A:
        x: int
        y: int = 123
    A3 = A
    a3 = A3(3)
    d3 = {'version': 3, 'x': 3}
    assert a1.to_dict() == d1
    for cls in [A1, A2, A3]:
        for strict in [True, False]:
            cls.__settings__.strict = strict
            assert cls.from_dict(d1) == a1
            assert cls.from_dict(d2) == a2
            assert cls.from_dict(d3) == a3
    for strict in [False, True]:
        A1.__settings__.strict = strict
        assert A1.from_dict(d1, migrate=True) == a1
        assert A1.from_dict(d2, migrate=True) == A1(x=2, y='b')
        # NOTE: type of y is wrong after migration
        # TODO: error if this happens during migration? Or just do general validation.
        assert A1.from_dict(d3, migrate=True) == A1(x=3, y=123)
    A1.__settings__.strict = False
    assert A1.from_dict({'version': 1, 'x': 1, 'z': 7.0}, migrate=True) == A1(x=1, y='a')
    A1.__settings__.strict = True
    with pytest.raises(ValueError, match="'z' is not a valid field for A"):
        _ = A1.from_dict({'version': 1, 'x': 1, 'z': 7.0}, migrate=True)
    for strict in [False, True]:
        A2.__settings__.strict = strict
        assert A2.from_dict(d2, migrate=True) == a2
        assert A2.from_dict(d1, migrate=True) == A2(x=1, y='a', z=3.14)
        assert A2.from_dict(d3, migrate=True) == A2(x=3, y=123)
    for strict in [False, True]:
        A3.__settings__.strict = strict
        assert A3.from_dict(d3, migrate=True) == a3
        assert A3.from_dict(d1, migrate=True) == A3(x=1, y='a')
        assert A3.from_dict(d2, migrate=True) == A3(x=2, y='b')
