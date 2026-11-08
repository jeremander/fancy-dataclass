from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import MISSING, FrozenInstanceError, dataclass, field
import re
from types import NoneType
from typing import Any, ClassVar

import pytest

from fancy_dataclass.utils import TypeLike
from fancy_dataclass.validate import FieldTypeValidationError, ValidatedDataclass


@dataclass
class DC1(ValidatedDataclass):
    x: int
    y: str

@dataclass
class DC2(DC1, validate_init=False):
    x: int
    y: str


@contextmanager
def raises_field_type_err(
    cls: type | str,
    field_name: str,
    field_type: TypeLike,
    val: Any,
    *,
    is_default: bool = False,
) -> Iterator[None]:
    """Context manager expecting a FieldTypeValidationError to be raised with the given parameters."""
    cls2 = NoneType if isinstance(cls, str) else cls
    err = FieldTypeValidationError(cls2, field_name, field_type, val, is_default=is_default)
    err_str = re.escape(str(err))
    if isinstance(cls, str):
        err_str = err_str.replace('NoneType', f'.*{cls}')
    with pytest.raises(FieldTypeValidationError, match=err_str):
        yield


@pytest.mark.parametrize(['args', 'kwargs'], [
    ((1, 'a'), {}),
    ((1,), {'y': 'a'}),
    ((), {'x': 1, 'y': 'a'}),
    ((1, '2'), {}),
])
def test_valid_fields(args: Sequence[Any], kwargs: dict[str, Any]) -> None:
    """Tests validation of ordinary fields on an instance when the field values are valid."""
    for cls in [DC1, DC2]:
        obj = cls(*args, **kwargs)
        assert isinstance(obj.x, int)
        assert isinstance(obj.y, str)

@pytest.mark.parametrize(['kwargs', 'err'], [
    (
        {},
        "missing 2 required positional arguments: 'x' and 'y'",
    ),
    (
        {'x': 1},
        "missing 1 required positional argument: 'y'",
    ),
    (
        {'y': 'a'},
        "missing 1 required positional argument: 'x'",
    ),
    (
        {'x': 1, 'y': 'a', 'z': 2},
        "got an unexpected keyword argument 'z'",
    ),
    (
        {'x': 1, 'y': 2},
        "field 'y' of .*DC1: value 2 does not match expected type str",
    ),
    (
        {'x': 'a', 'y': 'b'},
        "field 'x' of .*DC1: value 'a' does not match expected type int",
    ),
])
def test_invalid_fields(kwargs: dict[str, Any], err: str) -> None:
    """Tests validation of ordinary fields on an instance when the field values are invalid."""
    for cls in [DC1, DC2]:
        if (cls is DC2) and (set(kwargs) == {'x', 'y'}):
            # type validation is skipped
            _ = cls(**kwargs)
        else:
            with pytest.raises(TypeError, match=err):
                _ = cls(**kwargs)

def test_missing_field() -> None:
    """Tests validation when a field is missing."""
    obj = DC1(1, 'a')
    del obj.y
    with raises_field_type_err(DC1, 'y', str, MISSING):
        obj.__post_init__()

def test_int_as_float() -> None:
    """Tests that an integer validates as a float."""
    @dataclass
    class DCFloat(ValidatedDataclass):
        x: float
    obj1 = DCFloat(1.0)
    obj2 = DCFloat(1)
    assert obj1 == obj2
    for val in ['1', '1.0']:
        with raises_field_type_err(DCFloat, 'x', float, val):
            _ = DCFloat(val)  # type: ignore[arg-type]

def test_validate_collection() -> None:
    """Tests that all values in a collection are type-checked."""
    @dataclass
    class DCList(ValidatedDataclass):
        vals: list[int]
    n = 10
    vals = list(range(n))
    assert DCList(vals).vals == vals
    # check that changing an element's type makes it invalid
    for i in range(n):
        vals = [str(j) if (j == i) else j for j in range(n)]
        with raises_field_type_err(DCList, 'vals', list[int], vals):
            _ = DCList(vals)  # type: ignore[arg-type]
    # check that tuple is not valid as a list
    vals = tuple(range(n))
    with raises_field_type_err(DCList, 'vals', list[int], vals):
        _ = DCList(tuple(range(n)))  # type: ignore[arg-type]
    # Sequence field type permits both list and tuple
    @dataclass
    class DCSequence(ValidatedDataclass):
        vals: Sequence[int]
    for tp in [tuple, list]:
        vals = tp(range(n))
        assert DCSequence(vals).vals == vals
        vals = tp(str(j) if (j == n - 1) else j for j in range(n))
        with raises_field_type_err(DCSequence, 'vals', Sequence[int], vals):
            _ = DCSequence(vals)  # pyrefly: ignore[bad-argument-type]

def test_validate_classvar() -> None:
    """Tests validation of a ClassVar."""
    with raises_field_type_err('DCClassVar', 'x', int, 'a'):
        @dataclass
        class DCClassVar(ValidatedDataclass):
            x: ClassVar[int] = 'a'  # type: ignore[assignment]
    @dataclass
    class DCClassVar(ValidatedDataclass):
        x: ClassVar[int]
    with pytest.raises(AttributeError, match="type object 'DCClassVar' has no attribute 'x'"):
        _ = DCClassVar.x
    obj = DCClassVar()
    with pytest.raises(AttributeError, match="'DCClassVar' object has no attribute 'x'"):
        _ = obj.x
    @dataclass
    class DCClassVarSub1(DCClassVar):
        x: ClassVar[int] = 1
    assert DCClassVarSub1.x == 1
    obj = DCClassVarSub1()
    assert obj.x == 1
    with raises_field_type_err('DCClassVarSub2', 'x', int, 'a'):
        @dataclass
        class DCClassVarSub2(DCClassVar):
            x: ClassVar[int] = 'a'  # type: ignore[assignment]
    @dataclass
    class DCClassVarSub3(DCClassVar, validate_init=False):
        x: ClassVar[int] = 'a'  # type: ignore[assignment]
    assert DCClassVarSub3.x == 'a'  # type: ignore[comparison-overlap]
    obj = DCClassVarSub3()
    assert obj.x == 'a'  # type: ignore[comparison-overlap]

def test_nested() -> None:
    """Tests validation of a nested ValidatedDataclass."""
    # proper subclass of DC1
    @dataclass
    class DC1Sub(DC1):
        ...
    # same object structure, but not a subclass of DC1
    @dataclass
    class DC1Fake(ValidatedDataclass):
        x: int
        y: str
    # outer class validates
    @dataclass
    class DCOuterValidate(ValidatedDataclass):
        inner: DC1
    # outer class does not validate
    @dataclass
    class DCOuterNoValidate(ValidatedDataclass, validate_init=False):
        inner: DC1
    outer_cls: type[DCOuterValidate | DCOuterNoValidate]
    for outer_cls in [DCOuterValidate, DCOuterNoValidate]:  # type: ignore[assignment]
        for inner_cls in [DC1, DC1Sub, DC1Fake]:
            should_error = (outer_cls is DCOuterValidate) and (inner_cls is DC1Fake)
            inner = inner_cls(1, 'a')
            if should_error:
                with raises_field_type_err(outer_cls, 'inner', DC1, inner):
                    _ = outer_cls(inner)  # type: ignore[arg-type]
            else:
                outer = outer_cls(inner)  # type: ignore[arg-type]
                assert type(outer) is outer_cls
                assert outer.inner == inner
                assert type(outer.inner) is inner_cls
        should_error = outer_cls is DCOuterValidate
        for inner in [1, 'a']:
            if should_error:
                with raises_field_type_err(outer_cls, 'inner', DC1, inner):
                    _ = outer_cls(inner)  # type: ignore[arg-type]
            else:
                outer = outer_cls(inner)  # type: ignore[arg-type]
                assert outer.inner == inner

@pytest.mark.parametrize('frozen', [False, True])
@pytest.mark.parametrize('init', [False, True])
@pytest.mark.parametrize('assign', [False, True])
def test_validate_init_and_assign(frozen: bool, init: bool, assign: bool) -> None:
    """Tests validation of a field with varying flags for validate_init and validate_assign."""
    @dataclass(frozen=frozen)
    class DCClassFlags(ValidatedDataclass, validate_init=init, validate_assign=assign):
        x: int
    @dataclass(frozen=frozen)
    class DCFieldFlags(ValidatedDataclass):
        x: int = field(metadata={'validate_init': init, 'validate_assign': assign})
    for cls in [DCClassFlags, DCFieldFlags]:
        # valid type is always OK
        obj = cls(1)
        assert obj.x == 1  # type: ignore[attr-defined]
        # initialize with invalid type
        if init or ((not frozen) and assign):
            with raises_field_type_err(cls, 'x', int, 'a'):
                _ = cls('a')  # type: ignore[arg-type]
        else:
            obj = cls('a')  # type: ignore[arg-type]
            assert obj.x == 'a'  # type: ignore[attr-defined]
        # initialize with valid type, assign with invalid type
        obj = cls(1)
        if frozen:
            with pytest.raises(FrozenInstanceError, match="cannot assign to field 'x'"):
                obj.x = 'a'  # type: ignore[attr-defined]
            with pytest.raises(FrozenInstanceError, match="cannot assign to field 'y'"):
                obj.y = 'a'  # type: ignore[attr-defined]
        else:
            if assign:
                with raises_field_type_err(cls, 'x', int, 'a'):
                    obj.x = 'a'  # type: ignore[attr-defined]
            else:
                obj.x = 'a'  # type: ignore[attr-defined]
                assert obj.x == 'a'  # type: ignore[attr-defined]
            # assigning a non-field attribute is not prevented if the dataclass is not frozen
            assert not hasattr(obj, 'y')
            obj.y = 'a'  # type: ignore[attr-defined]
            assert obj.y == 'a'  # type: ignore[attr-defined]
    # try setting a default value of the wrong type
    if init:
        # field gets rejected at dataclass wrap time, since defaults can be checked then
        with raises_field_type_err('DCClassFlagsBadDefault', 'x', int, 'a', is_default=True):
            @dataclass(frozen=frozen)
            class DCClassFlagsBadDefault(ValidatedDataclass, validate_init=init, validate_assign=assign):
                x: int = 'a'  # type: ignore[assignment]
        with raises_field_type_err('DCFieldFlagsBadDefault', 'x', int, 'a', is_default=True):
            @dataclass(frozen=frozen)
            class DCFieldFlagsBadDefault(ValidatedDataclass):
                x: int = field(default='a', metadata={'validate_init': init, 'validate_assign': assign})  # type: ignore[assignment]
    else:
        # field does not get rejected because default_factory is not called until object construction time
        @dataclass(frozen=frozen)
        class DCClassFlagsBadDefault(ValidatedDataclass, validate_init=init, validate_assign=assign):
            x: int = 'a'  # type: ignore[assignment]
        @dataclass(frozen=frozen)
        class DCFieldFlagsBadDefault(ValidatedDataclass):
            x: int = field(default='a', metadata={'validate_init': init, 'validate_assign': assign})  # type: ignore[assignment]
        for cls in [DCClassFlagsBadDefault, DCFieldFlagsBadDefault]:
            if (not frozen) and assign:
                with raises_field_type_err(cls, 'x', int, 'a'):
                    _ = cls()
            else:
                # NOTE: assignment is bypassed if frozen=True
                obj = cls()
                assert obj.x == 'a'  # type: ignore[attr-defined]
    # try setting a default_factory value of the wrong type
    @dataclass(frozen=frozen)
    class DCClassFlagsBadDefaultFactory(ValidatedDataclass, validate_init=init, validate_assign=assign):
        x: int = field(default_factory=lambda: 'a')  # type: ignore[assignment]
    @dataclass(frozen=frozen)
    class DCFieldFlagsBadDefaultFactory(ValidatedDataclass):
        x: int = field(default_factory=lambda: 'a', metadata={'validate_init': init, 'validate_assign': assign})  # type: ignore[assignment]
    for cls in [DCClassFlagsBadDefaultFactory, DCFieldFlagsBadDefaultFactory]:
        if init or ((not frozen) and assign):
            with raises_field_type_err(cls, 'x', int, 'a'):
                _ = cls()
        else:
            obj = cls()
            assert obj.x == 'a'  # type: ignore[attr-defined]
