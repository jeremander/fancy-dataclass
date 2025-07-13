from dataclasses import dataclass, field
import re
from typing import ClassVar, List

import pytest

from fancy_dataclass.subprocess import SubprocessDataclass


def test_executable():
    """Tests retrieval of the executable name."""
    # executable in field
    @dataclass
    class DC1(SubprocessDataclass):
        prog: str = field(metadata={'exec': True})
    obj = DC1('myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog']
    # non-string executable
    obj = DC1(1)
    with pytest.raises(ValueError, match=re.escape('executable is 1 (must be a string)')):
        _ = obj.get_executable()
    # executable in ClassVar field
    @dataclass
    class DC2(SubprocessDataclass):
        prog: ClassVar[str] = field(metadata={'exec': True})
    obj = DC2()
    with pytest.raises(ValueError, match=re.escape('executable is None (must be a string)')):
        _ = obj.get_executable()
    DC2.prog = 'myprog'
    assert DC2().get_executable() == 'myprog'
    # executable in class settings
    @dataclass
    class DC3(SubprocessDataclass, exec='myprog'):
        ...
    assert DC3().get_executable() == 'myprog'
    # no executable
    @dataclass
    class DC4(SubprocessDataclass):
        ...
    obj = DC4()
    assert obj.get_executable() is None
    with pytest.raises(ValueError, match='no executable identified for use with DC4 instance'):
        _ = obj.get_args()
    # multiple exec fields
    with pytest.raises(TypeError, match=re.escape("cannot have more than one field with 'exec' flag set to True (already set executable to prog1)")):
        @dataclass
        class DC5(SubprocessDataclass):
            prog1: ClassVar[str] = field(metadata={'exec': True})
            prog2: str = field(metadata={'exec': True})
    # exec in both class settings and field
    with pytest.raises(TypeError, match = re.escape("cannot set field's 'exec' flag to True (class already set executable to prog1)")):
        @dataclass
        class DC6(SubprocessDataclass, exec='prog1'):
            prog2: str = field(metadata={'exec': True})
    # executable always comes first in argument list
    @dataclass
    class DC7(SubprocessDataclass):
        x: int
        yy: float
        prog: str = field(metadata={'exec': True})
    obj = DC7(3, 4.7, 'myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog', '-x', '3', '--yy', '4.7']

def test_option():
    """Tests behavior of the subprocess options."""
    @dataclass
    class DC1(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'option_name': '-a'})
        b: int = field(metadata={'option_name': '--b'})
        cc: int = field(metadata={'option_name': '-c'})
        dd: int = field(metadata={'option_name': '--dd'})
        # if None, use field name prefixed by one dash (if single letter) or two dashes (otherwise)
        e: int
        ff: int
        g: int = field(metadata={'option_name': None})
        hh: int = field(metadata={'option_name': None})
    assert DC1(1, 2, 3, 4, 5, 6, 7, 8).get_args() == ['prog', '-a', '1', '--b', '2', '-c', '3', '--dd', '4', '-e', '5', '--ff', '6', '-g', '7', '--hh', '8']
    # option_name without dashes
    @dataclass
    class DC2(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'option_name': 'a'})
        bb: int = field(metadata={'option_name': 'bb'})
        c_value: int = field(metadata={'option_name': 'c-value'})
    assert DC2(1, 2, 3).get_args() == ['prog', '-a', '1', '--bb', '2', '--c-value', '3']
    # empty option_name
    with pytest.raises(ValueError, match='empty string not allowed for option_name'):
        @dataclass
        class DC3(SubprocessDataclass, exec='prog'):
            a: int = field(metadata={'option_name': ''})
    # underscore gets converted to dash
    @dataclass
    class DC4(SubprocessDataclass, exec='prog'):
        my_arg_with_underscores_: int
    assert DC4(1).get_args() == ['prog', '--my-arg-with-underscores-', '1']

def test_positional():
    """Tests behavior of subprocess positional arguments."""
    @dataclass
    class DC1(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'subprocess_positional': True})
    assert DC1(1).get_args() == ['prog', '1']
    @dataclass
    class DC2(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'subprocess_positional': True})
        b: int
    assert DC2(1, 2).get_args() == ['prog', '1', '-b', '2']
    @dataclass
    class DC3(SubprocessDataclass, exec='prog'):
        a: int
        b: int = field(metadata={'subprocess_positional': True})
    assert DC3(1, 2).get_args() == ['prog', '-a', '1', '2']
    @dataclass
    class DC4(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'subprocess_positional': True})
        b: int
        c: int = field(metadata={'subprocess_positional': True})
        d: int = field(metadata={'option_name': '--option'})
    assert DC4(1, 2, 3, 4).get_args() == ['prog', '1', '-b', '2', '3', '--option', '4']
    with pytest.raises(ValueError, match='cannot specify a field option_name when subprocess_positional=True'):
        @dataclass
        class DC5(SubprocessDataclass, exec='prog'):
            a: int = field(metadata={'option_name': '-a', 'subprocess_positional': True})

def test_boolean_flag():
    """Tests a boolean field being treated as an on/off flag."""
    @dataclass
    class DC1(SubprocessDataclass, exec='prog'):
        flag: bool
    @dataclass
    class DC2(SubprocessDataclass, exec='prog'):
        flag: bool = field(metadata={'subprocess_flag': True})
    for cls in [DC1, DC2]:
        assert cls(False).get_args() == ['prog']
        assert cls(True).get_args() == ['prog', '--flag']
    @dataclass
    class DC3(SubprocessDataclass, exec='prog'):
        flag: bool = field(metadata={'subprocess_flag': False})
    assert DC3(False).get_args() == ['prog', '--flag', 'False']
    assert DC3(True).get_args() == ['prog', '--flag', 'True']
    # subprocess_flag is set to False even though field is not boolean (gets ignored)
    @dataclass
    class DC4(SubprocessDataclass, exec='prog'):
        val: int = field(metadata={'subprocess_flag': False})
    assert DC4(1).get_args() == ['prog', '--val', '1']
    assert DC4(False).get_args() == ['prog', '--val', 'False']
    # subprocess_flag is set to True even though field is not boolean (error)
    with pytest.raises(ValueError, match='cannot use subprocess_flag=True when the field type is not bool'):
        @dataclass
        class DC5(SubprocessDataclass, exec='prog'):
            val: int = field(metadata={'subprocess_flag': True})

def test_repeat_option_name():
    """Tests behavior of the `repeat_option_name` field setting."""
    # ordinary list value, so list multiple values directly
    @dataclass
    class DC1(SubprocessDataclass, exec='prog'):
        my_arg: List[int]
    assert DC1([]).get_args() == ['prog']
    assert DC1([1]).get_args() == ['prog', '--my-arg', '1']
    assert DC1([1, 2]).get_args() == ['prog', '--my-arg', '1', '2']
    # repeat_option_name=True, so repeat the option name multiple times
    @dataclass
    class DC2(SubprocessDataclass, exec='prog'):
        my_arg: List[int] = field(metadata={'repeat_option_name': True})
    assert DC2([]).get_args() == ['prog']
    assert DC2([1]).get_args() == ['prog', '--my-arg', '1']
    assert DC2([1, 2]).get_args() == ['prog', '--my-arg', '1', '--my-arg', '2']
    # not allowed with positional arg
    with pytest.raises(ValueError, match=r'cannot repeat option name for positional field \(subprocess_positional=True\)'):
        @dataclass
        class DC3(SubprocessDataclass, exec='prog'):
            my_arg: List[int] = field(metadata={'subprocess_positional': True, 'repeat_option_name': True})

# TODO: test exclusion
# TODO: duplicate names
