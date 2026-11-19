from collections.abc import Sequence
from dataclasses import dataclass
from types import NoneType
from typing import Annotated, Any, ClassVar, Literal, Optional, TypedDict, Union

import pytest
from typing_extensions import Never

from fancy_dataclass.utils import (
    TypeLike,
    TypeValidationError,
    _check_type,
    _is_subtype,
    camel_case_to_kebab_case,
    dataclass_field_type,
    get_type_name,
    snake_case_to_camel_case,
    type_is_optional,
)


class Example:
    ...


class TD(TypedDict):
    x: int
    y: str


@dataclass
class DC:
    a: int
    b: Annotated[int, 'a']
    c: Literal['a', 1]
    d: list[int]
    e: Never


def _check_type_ok(obj: Any, tp: TypeLike) -> bool:
    try:
        _check_type(obj, tp)
        return True
    except TypeValidationError:
        return False


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
def test_snake_case_to_camel_case(snake: str, camel: str) -> None:
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
def test_camel_case_to_kebab_case(camel: str, kebab: str) -> None:
    """Tests conversion of camel case to kebab case."""
    assert camel_case_to_kebab_case(camel) == kebab

@pytest.mark.parametrize(['tp', 'name'], [
    (int, 'int'),
    (float, 'float'),
    (str, 'str'),
    (int | str, 'int | str'),
    (list[int], 'list[int]'),
    (tuple[int, str], 'tuple[int, str]'),
    (dict[str, int], 'dict[str, int]'),
    (None, 'None'),
    (NoneType, 'NoneType'),
    (int | None, 'int | None'),
    (None | int, 'None | int'),
    (Optional[int], str(Optional[int])),  # NOTE: Py3.14 represents Optional[int] as (int | None)
    (Sequence[int], 'collections.abc.Sequence[int]'),
    (ClassVar[int], 'typing.ClassVar[int]'),
    (Any, 'typing.Any'),
    (Example, f'{__name__}.Example'),
])
def test_get_type_name(tp: TypeLike, name: str) -> None:
    """Tests the get_type_name function."""
    assert get_type_name(tp) == name

@pytest.mark.parametrize(['tp', 'is_optional'], [
    (int, False),
    (type(None), False),
    (Optional[int], True),
    (Optional[Optional[int]], True),  # noqa: PYI016
    (int | Optional[float], True),
    (Optional[float] | int, True),
    (Optional[type(None)], False),  # Optional[NoneType] -> NoneType
    (list[Optional[int]], False),
])
def test_type_is_optional(tp: Any, is_optional: bool) -> None:
    """Tests the type_is_optional function."""
    assert type_is_optional(tp) == is_optional

@pytest.mark.parametrize(['tp1', 'tp2', 'output'], [
    (int, int, True),
    (str, str, True),
    (int, str, False),
    (float, int, False),
    (int, float, False),
    (bool, int, True),
    (Optional[int], int, False),
    (int, Optional[int], True),
    (Optional[int], Optional[int], True),
    (Optional[int], Optional[float], False),
    (int | str, int, False),
    (Union[int, str], int, False),
    (int, int | str, True),
    (int, Union[int, str], True),
    (int | str, int | str, True),
    (Union[int, str], Union[int, str], True),
    (int | str | float, int | str, False),
    (int | str, int | str | float, True),
    (int, int | None, True),
    (None, Optional[int], False),
    (NoneType, Optional[int], True),
    (Sequence[str], Sequence[str], True),
    (Sequence[int], Sequence[str], False),
    (list[str], list[str], True),
    (list[int], list[str], False),
    (dict[int, str], dict[int, str], True),
    (dict[int, str], dict[int, int], False),
    (dict[bool, str], dict[int, str], True),
    (ClassVar[int], ClassVar[int], True),
    (ClassVar[bool], ClassVar[int], True),
    (ClassVar[int], ClassVar[str], False),
])
def test_check_is_subtype(tp1: Any, tp2: Any, output: bool) -> None:
    """Tests the _is_subtype helper function."""
    assert _is_subtype(tp1, tp2) is output

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
    # adheres to PEP 484 numeric tower rule that ints type-check as floats
    (1, float, True),
    (1, int | str, True),
    ('a', int | str, True),
    (1.0, int | str, False),
    ([], list[int], True),
    (1, list[int], False),
    ([1, 2], list[int], True),
    ([1, '2'], list[int], False),
    ({}, dict[str, int], True),
    (1, dict[str, int], False),
    ({'a': 1}, dict[str, int], True),
    ({'a': '1'}, dict[str, int], False),
    ({'a': 1, 2: 2}, dict[str, int], False),
    (None, Optional[list[int]], True),
    ([1, 2], Optional[list[int]], True),
    ({}, Optional[list[int]], False),
    ((), Sequence[int], True),
    ((1, 2), Sequence[int], True),
    (None, Sequence[int], False),
    ((1, 2), Optional[int | Sequence[int]], True),
    ({}, TD, False),
    ({'x': 1}, TD, False),
    ({'x': 1, 'y': '2'}, TD, True),
    ({'x': 1, 'y': 2}, TD, False),
    (1, Never, False),
    (None, Never, False),
    ([], list[Never], True),
    # TODO: remove xfail if nested Never type is handled properly
    #   see: https://github.com/agronholm/typeguard/issues/580
    pytest.param([1], list[Never], False, marks=pytest.mark.xfail),
])
def test_check_type(obj: Any, tp: Any, output: bool) -> None:
    """Tests the _check_type helper function."""
    assert _check_type_ok(obj, tp) is output

@pytest.mark.parametrize(['name', 'tp'], [
    ('a', int),
    ('b', int),
    ('c', Literal['a', 1]),
    ('d', list[int]),
    ('e', Never),
])
def test_dataclass_field_type(name: str, tp: TypeLike) -> None:
    """Tests the dataclass_field_type helper function."""
    assert dataclass_field_type(DC, name) == tp
