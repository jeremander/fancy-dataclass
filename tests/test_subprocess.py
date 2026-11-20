from dataclasses import dataclass, field
import re
from typing import ClassVar, Optional

import pytest

from fancy_dataclass.subprocess import SubprocessDataclass


def test_executable() -> None:
    """Tests retrieval of the executable name."""
    # executable in field
    @dataclass
    class DC1(SubprocessDataclass):
        prog: str = field(metadata={'subproc_is_exec': True})
    obj = DC1('myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog']
    # non-string executable
    obj = DC1(1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match=re.escape('executable is 1 (must be a string)')):
        _ = obj.get_executable()
    # executable in ClassVar field
    @dataclass
    class DC2(SubprocessDataclass):
        prog: ClassVar[str] = field(metadata={'subproc_is_exec': True})
    obj = DC2()
    with pytest.raises(ValueError, match=re.escape('executable is None (must be a string)')):
        _ = obj.get_executable()
    DC2.prog = 'myprog'
    assert DC2().get_executable() == 'myprog'
    # executable in class settings
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='myprog'):
        ...
    assert DC3().get_executable() == 'myprog'
    # no executable
    @dataclass
    class DC4(SubprocessDataclass):
        ...
    obj = DC4()
    assert obj.get_executable() is None
    assert obj.get_args() == []
    with pytest.raises(ValueError, match='no executable identified for use with DC4 instance'):
        obj.run_subprocess()
    # multiple exec fields
    with pytest.raises(
        TypeError,
        match=re.escape(
            "cannot have more than one field with 'subproc_is_exec' flag set to True (already set executable to prog1)"
        ),
    ):
        @dataclass
        class DC5(SubprocessDataclass):
            prog1: ClassVar[str] = field(metadata={'subproc_is_exec': True})
            prog2: str = field(metadata={'subproc_is_exec': True})
    # exec in both class settings and field
    with pytest.raises(
        TypeError,
        match=re.escape("cannot set field's 'subproc_is_exec' flag to True (class already set executable to prog1)"),
    ):
        @dataclass
        class DC6(SubprocessDataclass, subproc_exec_name='prog1'):
            prog2: str = field(metadata={'subproc_is_exec': True})
    # executable always comes first in argument list
    @dataclass
    class DC7(SubprocessDataclass):
        x: int
        yy: float
        prog: str = field(metadata={'subproc_is_exec': True})
    obj = DC7(3, 4.7, 'myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog', '-x', '3', '--yy', '4.7']

def test_extra_args() -> None:
    """Tests the extra_args setting."""
    @dataclass
    class DC(SubprocessDataclass, subproc_exec_name='prog', subproc_extra_args=['--arg', '-x']):
        x: int
    obj = DC(1)
    assert obj.get_executable() == 'prog'
    assert obj.get_args() == ['prog', '-x', '1', '--arg', '-x']

def test_option() -> None:
    """Tests behavior of the subprocess options."""
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_option_name': '-a'})
        b: int = field(metadata={'subproc_option_name': '--b'})
        cc: int = field(metadata={'subproc_option_name': '-c'})
        dd: int = field(metadata={'subproc_option_name': '--dd'})
        # if None, use field name prefixed by one dash (if single letter) or two dashes (otherwise)
        e: int
        ff: int
        g: int = field(metadata={'subproc_option_name': None})
        hh: int = field(metadata={'subproc_option_name': None})
    assert DC1(1, 2, 3, 4, 5, 6, 7, 8).get_args() == [
        'prog', '-a', '1', '--b', '2', '-c', '3', '--dd', '4', '-e', '5', '--ff', '6', '-g', '7', '--hh', '8'
    ]
    # option_name without dashes
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_option_name': 'a'})
        bb: int = field(metadata={'subproc_option_name': 'bb'})
        c_value: int = field(metadata={'subproc_option_name': 'c-value'})
    assert DC2(1, 2, 3).get_args() == ['prog', '-a', '1', '--bb', '2', '--c-value', '3']
    # underscore gets converted to dash
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='prog'):
        my_arg_with_underscores_: int
    assert DC3(1).get_args() == ['prog', '--my-arg-with-underscores-', '1']
    # duplicate option names are allowed
    @dataclass
    class DC4(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_option_name': '--option'})
        b: int = field(metadata={'subproc_option_name': 'option'})
        option: int
    assert DC4(1, 2, 3).get_args() == ['prog', '--option', '1', '--option', '2', '--option', '3']
    # optional value is omitted
    @dataclass
    class DC5(SubprocessDataclass, subproc_exec_name='prog'):
        a: Optional[int] = None
    assert DC5().get_args() == ['prog']

def test_positional() -> None:
    """Tests behavior of subprocess positional arguments."""
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_positional': True})
    assert DC1(1).get_args() == ['prog', '1']
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_positional': True})
        b: int
    assert DC2(1, 2).get_args() == ['prog', '1', '-b', '2']
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='prog'):
        a: int
        b: int = field(metadata={'subproc_positional': True})
    assert DC3(1, 2).get_args() == ['prog', '-a', '1', '2']
    @dataclass
    class DC4(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_positional': True})
        b: int
        c: int = field(metadata={'subproc_positional': True})
        d: int = field(metadata={'subproc_option_name': '--option'})
    assert DC4(1, 2, 3, 4).get_args() == ['prog', '1', '-b', '2', '3', '--option', '4']

def test_exclusion() -> None:
    """Tests the subproc_exclude flag."""
    # NOTE: for now we do not error if other subprocess-related fields are set in conjunction with
    # subproc_exclude=True, but this flag takes priority over all else.
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        a: int = field(metadata={'subproc_exclude': True})
        b: int = field(metadata={'subproc_exclude': True, 'subproc_positional': True})
        c: int = field(metadata={'subproc_exclude': True, 'subproc_option_name': '--option'})
        d: int = field(metadata={'subproc_exclude': True, 'subproc_repeat': True})
    assert DC1(1, 2, 3, 4).get_args() == ['prog']

def test_boolean_flag() -> None:
    """Tests a boolean field being treated as an on/off flag."""
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        flag: bool
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        flag: bool = field(metadata={'subproc_flag': True})
    for cls in [DC1, DC2]:
        assert cls(False).get_args() == ['prog']
        assert cls(True).get_args() == ['prog', '--flag']
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='prog'):
        flag: bool = field(metadata={'subproc_flag': False})
    assert DC3(False).get_args() == ['prog', '--flag', 'False']
    assert DC3(True).get_args() == ['prog', '--flag', 'True']
    # subproc_flag is set to False even though field is not boolean (gets ignored)
    @dataclass
    class DC4(SubprocessDataclass, subproc_exec_name='prog'):
        val: int = field(metadata={'subproc_flag': False})
    assert DC4(1).get_args() == ['prog', '--val', '1']
    assert DC4(False).get_args() == ['prog', '--val', 'False']
    # subproc_flag is set to True even though field is not boolean (error)
    with pytest.raises(ValueError, match='cannot use subproc_flag=True when the field type is not bool'):
        @dataclass
        class DC5(SubprocessDataclass, subproc_exec_name='prog'):
            val: int = field(metadata={'subproc_flag': True})

def test_subproc_repeat() -> None:
    """Tests behavior of the subproc_repeat field setting."""
    # ordinary list value, so list multiple values directly
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        my_arg: list[int]
    assert DC1([]).get_args() == ['prog']
    assert DC1([1]).get_args() == ['prog', '--my-arg', '1']
    assert DC1([1, 2]).get_args() == ['prog', '--my-arg', '1', '2']
    # subproc_repeat=True, so repeat the option name multiple times
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        my_arg: list[int] = field(metadata={'subproc_repeat': True})
    assert DC2([]).get_args() == ['prog']
    assert DC2([1]).get_args() == ['prog', '--my-arg', '1']
    assert DC2([1, 2]).get_args() == ['prog', '--my-arg', '1', '--my-arg', '2']

def test_invalid_field_settings() -> None:
    """Tests that subproc_positional is incompatible with subproc_option_name."""
    # empty option_name
    with pytest.raises(ValueError, match='empty string not allowed for subproc_option_name'):
        @dataclass
        class DC(SubprocessDataclass, subproc_exec_name='prog'):
            a: int = field(metadata={'subproc_option_name': ''})
    # set both subproc_positional and subproc_option_name
    with pytest.raises(ValueError, match='cannot specify subproc_option_name when subproc_positional=True'):
        @dataclass
        class DC(SubprocessDataclass, subproc_exec_name='prog'):
            a: int = field(metadata={'subproc_option_name': '-a', 'subproc_positional': True})
    # set both subproc_positional and subproc_repeat
    with pytest.raises(ValueError, match='cannot set both subproc_repeat=True and subproc_positional=True'):
        @dataclass
        class DC(SubprocessDataclass, subproc_exec_name='prog'):
            my_arg: list[int] = field(metadata={'subproc_positional': True, 'subproc_repeat': True})

def test_class_var() -> None:
    """Tests behavior of ClassVar fields."""
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        a: ClassVar[int] = 1
        b: ClassVar[int] = field(default=2, metadata={'subproc_exclude': False})
        c: ClassVar[int] = field(default=3, metadata={'subproc_exclude': True})
        d: int
        e: int = field(metadata={'subproc_exclude': False})
        f: int = field(metadata={'subproc_exclude': True})
    assert DC1(4, 5, 6).get_args() == ['prog', '-b', '2', '-d', '4', '-e', '5']
    # can make a ClassVar positional or set its option name
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        a: ClassVar[int] = field(default=1, metadata={'subproc_exclude': False})
        b: ClassVar[int] = field(default=2, metadata={'subproc_positional': True, 'subproc_exclude': False})
        c: ClassVar[int] = field(default=3, metadata={'subproc_option_name': 'option', 'subproc_exclude': False})
    assert DC2().get_args() == ['prog', '-a', '1', '2', '--option', '3']

def test_nested() -> None:
    """Tests a nested SubprocessDataclass field."""
    @dataclass
    class DC1(SubprocessDataclass):
        a: int
        b: int = field(metadata={'subproc_option_name': 'option'})
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='inner'):
        a: int
        b: int = field(metadata={'subproc_option_name': 'option'})
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='outer'):
        dc1: DC1
        c: int
    @dataclass
    class DC4(SubprocessDataclass, subproc_exec_name='outer'):
        dc2: DC2
        c: int
    @dataclass
    class DC5(SubprocessDataclass, subproc_exec_name='outer'):
        c: int
        dc1: DC1
    @dataclass
    class DC6(SubprocessDataclass, subproc_exec_name='outer'):
        c: int
        dc2: DC2
    @dataclass
    class DC7(SubprocessDataclass):
        dc1: DC1
        c: int
    @dataclass
    class DC8(SubprocessDataclass):
        dc2: DC2
        c: int
    assert DC3(DC1(1, 2), 3).get_args() == ['outer', '-a', '1', '--option', '2', '-c', '3']
    assert DC4(DC2(1, 2), 3).get_args() == ['outer', 'inner', '-a', '1', '--option', '2', '-c', '3']
    assert DC5(3, DC1(1, 2)).get_args() == ['outer', '-c', '3', '-a', '1', '--option', '2']
    assert DC6(3, DC2(1, 2)).get_args() == ['outer', '-c', '3', 'inner', '-a', '1', '--option', '2']
    obj = DC7(DC1(1, 2), 3)
    assert obj.get_args() == ['-a', '1', '--option', '2', '-c', '3']
    with pytest.raises(ValueError, match='no executable identified for use with DC7 instance'):
        obj.run_subprocess()
    obj = DC8(DC2(1, 2), 3)
    assert obj.get_args() == ['inner', '-a', '1', '--option', '2', '-c', '3']
    with pytest.raises(ValueError, match='no executable identified for use with DC8 instance'):
        obj.run_subprocess()

def test_union() -> None:
    """Tests fields with a union type."""
    @dataclass
    class DC1(SubprocessDataclass, subproc_exec_name='prog'):
        a: int | str
    assert DC1(1).get_args() == ['prog', '-a', '1']
    assert DC1('val').get_args() == ['prog', '-a', 'val']
    @dataclass
    class Inner1(SubprocessDataclass):
        a: int
    @dataclass
    class Inner2(SubprocessDataclass):
        b: int
    @dataclass
    class DC2(SubprocessDataclass, subproc_exec_name='prog'):
        inner: Inner1 | Inner2
    assert DC2(Inner1(1)).get_args() == ['prog', '-a', '1']
    assert DC2(Inner2(1)).get_args() == ['prog', '-b', '1']
    @dataclass
    class DC3(SubprocessDataclass, subproc_exec_name='prog'):
        inner: int | Inner2
    assert DC3(1).get_args() == ['prog', '--inner', '1']
    assert DC3(Inner2(1)).get_args() == ['prog', '-b', '1']
    @dataclass
    class DC4(SubprocessDataclass, subproc_exec_name='prog'):
        inner: Inner1 | int
    assert DC4(Inner1(1)).get_args() == ['prog', '-a', '1']
    assert DC4(1).get_args() == ['prog', '--inner', '1']
