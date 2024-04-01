from dataclasses import dataclass, field
from pathlib import Path
import sys

import pytest

from fancy_dataclass.cli import ArgparseDataclass, ArgparseDataclassFieldSettings
from fancy_dataclass.subprocess import SubprocessDataclass, SubprocessDataclassFieldSettings
from fancy_dataclass.utils import merge_dataclasses
from tests.test_cli import DC1


def test_field_settings_collision():
    """Tests inheriting multiple mixins with a FieldSettings name collision."""
    with pytest.raises(TypeError, match="duplicate field name 'args'"):
        @dataclass
        class ArgparseSubprocessDataclass1(ArgparseDataclass, SubprocessDataclass):
            ...
    # field settings have a duplicate field, so make a custom merged settings class and set it explicitly
    ArgparseSubprocessFieldSettings = merge_dataclasses(ArgparseDataclassFieldSettings, SubprocessDataclassFieldSettings, allow_duplicates=True)
    @dataclass
    class ArgparseSubprocessDataclass2(ArgparseDataclass, SubprocessDataclass):
            __field_settings_type__ = ArgparseSubprocessFieldSettings

def test_subprocess_dataclass(tmpdir):
    """Tests SubprocessDataclass behavior."""
    DC2FieldSettings = merge_dataclasses(DC1.__field_settings_type__, SubprocessDataclassFieldSettings, allow_duplicates=True)
    @dataclass
    class DC2(DC1, SubprocessDataclass):
        __field_settings_type__ = DC2FieldSettings
        prog: str = field(default = 'prog', metadata = {'exec': True})
    prog = str(tmpdir / 'prog.py')
    dc2 = DC2(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='a', optional='default', flag=True, extra_items=[], x=7, y=3.14, pair=(0,0), ignored_value='ignored', prog = prog)
    assert dc2.args() == ['positional_arg', '-i', 'my_input', '-o', 'my_output', '--choice', 'a', '--optional', 'default', '--flag', '-x', '7', '-y', '3.14', '--pair', '0', '0']
    assert dc2.args(suppress_defaults=True) == ['positional_arg', '-i', 'my_input', '-o', 'my_output', '--flag']
    # create a script to run the CLIDataclass
    dc1 = DC1.from_dict(dc2.to_dict())
    cwd = str(Path(__file__).parent)
    with open(prog, 'w') as f:
        print(f"""#!{sys.executable}
import sys
sys.path.insert(0, {cwd!r})
from test_cli import DC1
DC1.main()""", file = f)
    Path(prog).chmod(0o770)
    # call the script with subprocess
    res = dc2.run_subprocess(capture_output=True, text=True)
    assert res.stdout.rstrip() == str(dc1)

def test_multiple_exec():
    """Tests that an error occurs if the 'exec' flag is set to True for multiple fields."""
    with pytest.raises(TypeError, match = "cannot have more than one field with 'exec' flag set to True"):
        @dataclass
        class TwoExec(SubprocessDataclass):
            prog1: str = field(metadata = {'exec': True})
            prog2: str = field(metadata = {'exec': True})
