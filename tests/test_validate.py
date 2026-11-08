from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pytest

from fancy_dataclass.validate import ValidatedDataclass


@dataclass
class DC1(ValidatedDataclass):
    x: int
    y: str

@dataclass
class DC2(DC1, validate_init=False):
    x: int
    y: str


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
        "field 'y' of .*DC1: value has type int, expected str",
    ),
    (
        {'x': 'a', 'y': 'b'},
        "field 'x' of .*DC1: value has type str, expected int",
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

def test_int_as_float() -> None:
    """Tests that an integer validates as a float."""
    @dataclass
    class DCFloat(ValidatedDataclass):
        x: float
    obj1 = DCFloat(1.0)
    obj2 = DCFloat(1)
    assert obj1 == obj2
    for val in ['1', '1.0']:
        with pytest.raises(TypeError, match="field 'x' of .*DCFloat: value has type str, expected float"):
            _ = DCFloat(val)  # type: ignore[arg-type]

def test_collection_validation() -> None:
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
        with pytest.raises(TypeError, match=r"field 'vals' of .*DCList: value has type list, expected list\[int\]"):
            _ = DCList(vals)  # type: ignore[arg-type]
    # check that tuple is not valid as a list
    with pytest.raises(TypeError, match=r"field 'vals' of .*DCList: value has type tuple, expected list\[int\]"):
        _ = DCList(tuple(range(n)))  # type: ignore[arg-type]
    # Sequence field type permits both list and tuple
    @dataclass
    class DCSequence(ValidatedDataclass):
        vals: Sequence[int]
    for tp in [tuple, list]:
        vals = tp(range(n))
        assert DCSequence(vals).vals == vals
        vals = tp(str(j) if (j == n - 1) else j for j in range(n))
        with pytest.raises(
            TypeError,
            match=r"field 'vals' of .*DCSequence: value has type .*, expected .*Sequence\[int\]",
        ):
            _ = DCSequence(vals)  # pyrefly: ignore[bad-argument-type]

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
                with pytest.raises(TypeError, match=r"field 'inner' of .*: value has type .*DC1Fake, expected .*DC1"):
                    _ = outer_cls(inner)  # type: ignore[arg-type]
            else:
                outer = outer_cls(inner)  # type: ignore[arg-type]
                assert type(outer) is outer_cls
                assert outer.inner == inner
                assert type(outer.inner) is inner_cls
        should_error = outer_cls is DCOuterValidate
        for inner in [1, 'a']:
            if should_error:
                with pytest.raises(
                    TypeError,
                    match=r"field 'inner' of .*DCOuterValidate: value has type .*, expected .*DC1",
                ):
                    _ = outer_cls(inner)  # type: ignore[arg-type]
            else:
                outer = outer_cls(inner)  # type: ignore[arg-type]
                assert outer.inner == inner
