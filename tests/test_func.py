# ruff: noqa: B004,B006
from dataclasses import dataclass
from typing import List

import pytest

from fancy_dataclass.func import func_dataclass


def test_func_dataclass():
    """Tests the func_dataclass decorator which constructs a new dataclass type from a function with default arguments."""
    # no args
    def return_123() -> int:
        return 123
    Return123 = func_dataclass(return_123)
    # snake case to camel case
    assert Return123.__name__ == 'Return123'
    obj1 = Return123()
    assert isinstance(obj1, Return123)
    assert obj1() == 123
    # one arg
    def square(x: int) -> int:
        return x ** 2
    # explicit cls_nameg
    Square = func_dataclass(square, cls_name='MySquare')
    assert Square.__name__ == 'MySquare'
    obj2 = Square()
    assert isinstance(obj2, Square)
    assert obj2(5) == 25
    # two args
    def add2(x: int, y: int) -> int:
        return x + y
    Add2 = func_dataclass(add2)
    assert Add2()(3, 4) == 7
    with pytest.raises(TypeError, match='takes 2 positional arguments but 3 were given'):
        _ = Add2()(1, 2, 3)
    # kwargs
    def concat_lists(x: List[int] = [], y: List[int] = []) -> List[int]:
        return x + y
    ConcatLists = func_dataclass(concat_lists)
    assert ConcatLists()() == []
    assert ConcatLists([1, 2, 3])() == [1, 2, 3]
    obj3 = ConcatLists([1, 2], [3])
    assert obj3.x == [1, 2]
    assert obj3.y == [3]
    assert obj3() == [1, 2, 3]
    # arg and kwarg
    def append_list(x: List[int], y: List[int] = []) -> List[int]:
        return y + x
    AppendList = func_dataclass(append_list)
    assert AppendList([])([]) == []
    assert AppendList([1])([2, 3]) == [1, 2, 3]
    # args and kwargs
    def append_numbers(x: List[int], y: int = 1, z: int = 2) -> List[int]:
        return x + [y, z]
    AppendNumbers = func_dataclass(append_numbers)
    assert AppendNumbers()([]) == [1, 2]
    assert AppendNumbers()(['a']) == ['a', 1, 2]
    assert AppendNumbers(z=100)(['a']) == ['a', 1, 100]
    # varargs
    def add_args(*args: int) -> int:
        return sum(args)
    AddArgs = func_dataclass(add_args)
    assert AddArgs()() == 0
    assert AddArgs()(1, 2, 3) == 6
    # varkwargs (not allowed)
    def add_kwargs(**kwargs: int) -> int:
        return sum(kwargs.values())
    with pytest.raises(TypeError, match='with keyword arguments'):
        _ = func_dataclass(add_kwargs)
    # explicit method_name
    Square = func_dataclass(square, method_name='func')
    assert hasattr(Square, '__call__')  # constructor exists
    obj4 = Square()
    assert not hasattr(obj4, '__call__')
    assert obj4.func(5) == 25
    # explicit base class
    @dataclass
    class Base:
        y: str = 'abc'
        def square_twice(self, x: int) -> int:
            return self(self(x))  # type: ignore
    SquareTwice = func_dataclass(square, bases=(Base,))
    obj5 = SquareTwice()
    assert issubclass(SquareTwice, Base)
    assert isinstance(obj5, SquareTwice)
    assert obj5.y == 'abc'
    assert obj5(5) == 25
    assert obj5.square_twice(3) == 81
    obj6 = SquareTwice('')
    assert obj6.y == ''
    assert obj6.square_twice(3) == 81
    assert obj5 == SquareTwice()
    assert obj5 != obj6
