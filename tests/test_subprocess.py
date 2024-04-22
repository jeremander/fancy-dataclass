from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import ClassVar

import pytest

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.subprocess import SubprocessDataclass, SubprocessDataclassFieldSettings
from fancy_dataclass.utils import coerce_to_dataclass, merge_dataclasses
from tests.test_cli import DC1


def test_subprocess_dataclass(tmpdir):
    """Tests SubprocessDataclass behavior."""
    DC2FieldSettings = merge_dataclasses(DC1.__field_settings_type__, SubprocessDataclassFieldSettings, allow_duplicates=True)
    @dataclass
    class DC2(DictDataclass, DC1, SubprocessDataclass):
        __field_settings_type__ = DC2FieldSettings
        prog: str = field(default = 'prog', metadata = {'exec': True})
    prog = str(tmpdir / 'prog.py')
    dc2 = DC2(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='a', optional='default', flag=True, extra_items=[], x=7, y=3.14, pair=(0,0), ignored_value='ignored', prog = prog)
    assert dc2.get_args() == [prog, 'positional_arg', '-i', 'my_input', '-o', 'my_output', '--choice', 'a', '--optional', 'default', '--flag', '-x', '7', '-y', '3.14', '--pair', '0', '0']
    assert dc2.get_args(suppress_defaults=True) == [prog, 'positional_arg', '-i', 'my_input', '-o', 'my_output', '--flag']
    # create a script to run the CLIDataclass
    dc1 = coerce_to_dataclass(DC1, dc2)
    cwd = str(Path(__file__).parent)
    with open(prog, 'w') as f:
        print(f"""#!/usr/bin/env python3
import sys
sys.path.insert(0, {cwd!r})
from test_cli import DC1
DC1.main()""", file=f)
    Path(prog).chmod(0o770)
    # call the script with subprocess
    res = dc2.run_subprocess(capture_output=True, text=True)
    assert res.stdout.rstrip() == str(dc1)

def test_executable():
    """Tests retrieval of the executable name."""
    # executable in field
    @dataclass
    class DC3(SubprocessDataclass):
        prog: str = field(metadata={'exec': True})
    obj = DC3('myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog']
    # non-string executable
    obj = DC3(1)
    with pytest.raises(ValueError, match=re.escape('executable is 1 (must be a string)')):
        _ = obj.get_executable()
    # executable in ClassVar field
    @dataclass
    class DC4(SubprocessDataclass):
        prog: ClassVar[str] = field(metadata={'exec': True})
    obj = DC4()
    with pytest.raises(ValueError, match=re.escape('executable is None (must be a string)')):
        _ = obj.get_executable()
    DC4.prog = 'myprog'
    assert DC4().get_executable() == 'myprog'
    # executable in class settings
    @dataclass
    class DC5(SubprocessDataclass, exec='myprog'):
        ...
    assert DC5().get_executable() == 'myprog'
    # no executable
    @dataclass
    class DC6(SubprocessDataclass):
        ...
    obj = DC6()
    assert obj.get_executable() is None
    with pytest.raises(ValueError, match='no executable identified for use with DC6 instance'):
        _ = obj.get_args()
    # multiple exec fields
    with pytest.raises(TypeError, match=re.escape("cannot have more than one field with 'exec' flag set to True (already set executable to prog1)")):
        @dataclass
        class DC7(SubprocessDataclass):
            prog1: ClassVar[str] = field(metadata={'exec': True})
            prog2: str = field(metadata={'exec': True})
    # exec in both class settings and field
    with pytest.raises(TypeError, match = re.escape("cannot set field's 'exec' flag to True (class already set executable to prog1)")):
        @dataclass
        class DC8(SubprocessDataclass, exec='prog1'):
            prog2: str = field(metadata={'exec': True})
    # executable always comes first in argument list
    @dataclass
    class DC9(SubprocessDataclass):
        x: int
        yy: float
        prog: str = field(metadata={'exec': True})
    obj = DC9(3, 4.7, 'myprog')
    assert obj.get_executable() == 'myprog'
    assert obj.get_args() == ['myprog', '-x', '3', '--yy', '4.7']

def test_field_args():
    """Tests behavior of the 'args' metadata in a field."""
    @dataclass
    class DC10(SubprocessDataclass, exec='prog'):
        # if a non-empty list, use the first entry as the argument name (only if it starts with a dash)
        a: int = field(metadata={'args': ['-a']})
        b: int = field(metadata={'args': ['-b', '--bb']})
        c: int = field(metadata={'args': ['--c']})
        # if None, use field name prefixed by dash
        d: int
        ee: int
        f: int = field(metadata={'args': None})
        # if an empty list, exclude this field from the arguments
        g: int = field(metadata={'args': []})
        # string is the same as singleton list
        h: int = field(metadata={'args': '--hh'})
    assert DC10(1, 2, 3, 4, 5, 6, 7, 8).get_args() == ['prog', '-a', '1', '-b', '2', '--c', '3', '-d', '4', '--ee', '5', '-f', '6', '--hh', '8']
    # args not starting with dash
    @dataclass
    class DC11(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'args': ['a']})
    assert DC11(1).get_args() == ['prog', '1']
    @dataclass
    class DC12(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'args': ['a']})
        b: int = field(metadata={'args': ''})
        c: int = field(metadata={'args': ['c', '-c']})
    assert DC12(1, 2, 3).get_args() == ['prog', '1', '2', '3']
    @dataclass
    class DC13(SubprocessDataclass, exec='prog'):
        a: int = field(metadata={'args': ['a']})
        b: int
    assert DC13(1, 2).get_args() == ['prog', '1', '-b', '2']
    @dataclass
    class DC14(SubprocessDataclass, exec='prog'):
        a: int
        b: int = field(metadata={'args': ['b']})
    assert DC14(1, 2).get_args() == ['prog', '-a', '1', '2']

def test_flag():
    """Tests a boolean field being treated as an on/off flag."""
    @dataclass
    class DC15(SubprocessDataclass, exec='prog'):
        flag: bool
    assert DC15(False).get_args() == ['prog']
    assert DC15(True).get_args() == ['prog', '--flag']

def test_underscore_conversion():
    """Tests that underscores are converted to dashes for automatic argument naming."""
    @dataclass
    class DC16(SubprocessDataclass, exec='prog'):
        my_arg: int
    assert DC16(1).get_args() == ['prog', '--my-arg', '1']
