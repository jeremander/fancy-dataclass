from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

import pytest

from fancy_dataclass import ArgparseDataclass, ConfigDataclass, DictDataclass, JSONBaseDataclass, JSONDataclass, SQLDataclass, SubprocessDataclass, TOMLDataclass
from fancy_dataclass.cli import ArgparseDataclassSettings
from fancy_dataclass.dict import DictDataclassSettings
from fancy_dataclass.mixin import DataclassMixin, MixinSettings
from fancy_dataclass.toml import NoneProxy
from fancy_dataclass.utils import coerce_to_dataclass

from .test_cli import DC1


DEFAULT_MIXINS = [JSONBaseDataclass, ArgparseDataclass, ConfigDataclass, SQLDataclass, TOMLDataclass]

TEST_DIR = Path(__file__).parent
PKG_DIR = TEST_DIR.parent


def test_multiple_inheritance():
    """Tests inheritance from multiple DataclassMixins."""
    @dataclass
    class DC1(ArgparseDataclass, JSONDataclass):
        x: int
    assert JSONDataclass.__settings_type__ is DictDataclassSettings
    assert issubclass(DC1.__settings_type__, DictDataclassSettings)
    assert issubclass(DC1.__settings_type__, ArgparseDataclassSettings)
    # alternatively, add in mixins dynamically with wrap_dataclass
    @dataclass
    class DC2:
        x: int
    DC2 = JSONDataclass.wrap_dataclass(ArgparseDataclass.wrap_dataclass(DC2))
    for cls in [DC1, DC2]:
        mro = cls.mro()
        assert mro.index(ArgparseDataclass) < mro.index(JSONDataclass)
        obj = cls(5)
        assert isinstance(obj, ArgparseDataclass)
        assert isinstance(obj, JSONDataclass)
        assert obj.to_json_string() == '{"x": 5}'
        _ = obj.make_parser().format_help()

def test_all_inheritance():
    """Tests a class that inherits from all the default DataclassMixins."""
    @dataclass
    class DC:
        x: int
    cls = DC
    for mixin_cls in DEFAULT_MIXINS:
        cls = mixin_cls.wrap_dataclass(cls, store_type='qualname')
    mro = cls.mro()
    obj = cls(5)
    for mixin_cls in DEFAULT_MIXINS:
        assert mixin_cls in mro
        assert isinstance(obj, mixin_cls)

def test_invalid_inheritance():
    """Tests invalid inheritance (e.g. parent class before its subclass)."""
    # this order works
    @dataclass
    class DC(JSONDataclass, DictDataclass):
        pass
    assert issubclass(DC, DictDataclass)
    assert issubclass(DC, JSONDataclass)
    @dataclass
    class DC:
        pass
    DC1 = JSONDataclass.wrap_dataclass(DC)
    DC2 = DictDataclass.wrap_dataclass(DC1)
    # already a subclass, so wrapping does nothing
    assert DC2 is DC1
    # this order doesn't work
    with pytest.raises(TypeError, match='Cannot create a consistent'):
        @dataclass
        class DC(DictDataclass, JSONDataclass):  # type: ignore[metaclass]
            pass
    DC1 = DictDataclass.wrap_dataclass(DC)
    # this works because JSONDataclass is not a subclass of DC1
    DC2 = JSONDataclass.wrap_dataclass(DC1)
    assert issubclass(DC2, DictDataclass)
    assert issubclass(DC2, JSONDataclass)
    assert issubclass(DC2, DC1)
    assert DC2 is not DC1

def test_post_dataclass_wrap():
    """Tests behavior of `__post_dataclass_wrap__` with multiple inheritance."""
    class Mixin1(DataclassMixin):
        @classmethod
        def __post_dataclass_wrap__(cls, wrapped_cls):
            wrapped_cls.val = 1
            wrapped_cls.val1 = 1
    class Mixin2(DataclassMixin):
        @classmethod
        def __post_dataclass_wrap__(cls, wrapped_cls):
            wrapped_cls.val = 2
            wrapped_cls.val2 = 2
    @dataclass
    class DC1(Mixin1):
        ...
    assert DC1.val == 1
    @dataclass
    class DC12(Mixin1, Mixin2):
        ...
    assert DC12.val == 1  # first base takes priority
    assert DC12.val1 == 1
    assert DC12.val2 == 2

def test_settings_field_collision():
    """Tests multiple inheritance from `MixinSettings` classes with overlapping field names."""
    @dataclass
    class Settings1(MixinSettings):
        a: int = 1
    @dataclass
    class Settings2(MixinSettings):
        a: int = 2
        b: int = 3
    @dataclass
    class Settings3(Settings1, Settings2):
        ...
    assert list(Settings3.__dataclass_fields__) == ['a', 'b']
    assert Settings3() == Settings3(1, 3)
    class DC1(DataclassMixin):
        __settings_type__ = Settings1
    class DC2(DataclassMixin):
        __settings_type__ = Settings2
    with pytest.raises(TypeError, match="error merging base class settings for DC3: duplicate field name 'a'"):
        class DC3(DC1, DC2):
            ...
    class DC4(DC1, DC2):
        __settings_type__ = Settings2

def test_json_toml():
    """Tests inheritance from both JSONDataclass and TOMLDataclass."""
    dt = datetime.strptime('2024-01-01', '%Y-%m-%d')
    json_str = '{"dt": "2024-01-01T00:00:00"}'
    toml_str = 'dt = 2024-01-01T00:00:00\n'
    @dataclass
    class JSONTOMLDC(JSONDataclass, TOMLDataclass):
        dt: datetime
    @dataclass
    class TOMLJSONDC(TOMLDataclass, JSONDataclass):
        dt: datetime
    obj1 = JSONTOMLDC(dt)
    obj2 = TOMLJSONDC(dt)
    for obj in [obj1, obj2]:
        assert isinstance(obj.to_dict()['dt'], datetime)
        assert obj.to_json_string() == json_str
        assert obj.to_toml_string() == toml_str
    # first class in inheritance list takes priority for saving/loading
    with StringIO() as sio:
        obj1.save(sio)
        sio.seek(0)
        assert type(obj1).from_json_string(sio.read()) == obj1
        sio.seek(0)
        assert type(obj1).load(sio) == obj1
    with StringIO() as sio:
        obj2.save(sio)
        sio.seek(0)
        assert type(obj2).from_toml_string(sio.read()) == obj2
        sio.seek(0)
        assert type(obj2).load(sio) == obj2

def test_argparse_subprocess_dataclass():
    """Tests inheritance from both ArgparseDataclass and SubprocessDataclass."""
    # no name collision in field settings, so inheritance works OK
    class ArgparseSubprocessDC(ArgparseDataclass, SubprocessDataclass):
        ...
    @dataclass
    class DC1(ArgparseSubprocessDC, exec='prog'):
        a: int = field(default=1, metadata={'args': ['--a-value']})
        b: int = field(default=2, metadata={'option_name': 'b-value'})
        c: int = field(default=3)
        d: int = field(default=4, metadata={'args': ['--name1'], 'option_name': '--name2'})
    assert DC1(1, 2, 3, 4).get_args() == ['prog', '-a', '1', '--b-value', '2', '-c', '3', '--name2', '4']
    assert DC1(1, 2, 3, 4).get_args(suppress_defaults=True) == ['prog']
    assert DC1.from_cli_args(['--a-value', '1', '-b', '2', '-c', '3', '--name1', '4']) == DC1(1, 2, 3, 4)

def test_cli_subprocess_dataclass(tmpdir):
    """Tests subclassing both CLIDataclass and SubprocessDataclass."""
    @dataclass
    class DC2(DC1, SubprocessDataclass):
        prog: str = field(default='prog', metadata={'exec': True})
        # ensure the positional arg is positional for both argument parsing *and* subprocess output
        required_string: str = field(metadata={'args': ['required_string'], 'subprocess_positional': True, 'help': 'a required string'})
        # ensure the ignored value is excluded from both argument parsing *and* subprocess output
        ignored_value: str = field(default='ignored', metadata={'args': [], 'parse_exclude': True, 'subprocess_exclude': True})
    prog = str(tmpdir / 'prog.py')
    dc2 = DC2(required_string='positional', input_file='my_input', output_file='my_output', choice='a', optional='default', flag=True, extra_items=[], x=7, y=3.14, pair=(0,0), ignored_value='ignored', prog = prog)
    assert dc2.get_args() == [prog, 'positional', '--input-file', 'my_input', '--output-file', 'my_output', '--choice', 'a', '--optional', 'default', '--flag', '-x', '7', '-y', '3.14', '--pair', '0', '0']
    assert dc2.get_args(suppress_defaults=True) == [prog, 'positional', '--input-file', 'my_input', '--output-file', 'my_output', '--flag']
    # create a script to run the CLIDataclass
    dc1 = coerce_to_dataclass(DC1, dc2)
    with open(prog, 'w') as f:
        print(f"""#!/usr/bin/env python3
import sys
sys.path.insert(0, {str(TEST_DIR)!r})
sys.path.insert(0, {str(PKG_DIR)!r})
from test_cli import DC1
DC1.main()""", file=f)
    Path(prog).chmod(0o770)
    # call the script with subprocess
    res = dc2.run_subprocess(capture_output=True, text=True)
    assert res.stdout.rstrip() == str(dc1)

def test_config_json_dataclass():
    """Tests subclassing both ConfigDataclass and JSONDataclass."""
    @dataclass
    class DC1(ConfigDataclass, JSONBaseDataclass):
        x: int
    assert DC1.from_dict({'x': 1}) == DC1(1)
    @dataclass
    class DC2(DC1):
        y: int
    assert DC2.from_dict({'x': 1, 'y': 2}) == DC2(1, 2)

def test_toml_json_dataclass():
    """Tests subclassing both TOMLDataclass and JSONDataclass."""
    @dataclass
    class DC1(TOMLDataclass, JSONDataclass):
        x: int
        y: Optional[int] = None
    obj = DC1(1)
    # NOTE: this is hacky and should probably be fixed, but at present the dict representation for TOMLDataclass must contain NoneProxy, which is not directly JSON serializable
    assert obj.to_dict() == {'x': 1, 'y': NoneProxy()}
    assert obj.to_toml_string() == 'x = 1\n# y = \n'
    assert obj.to_json_string() == '{"x": 1, "y": null}'

def test_json_argparse_dataclass():
    """Tests subclassing both JSONDataclass and ArgparseDataclass."""
    @dataclass
    class DC1(JSONDataclass, ArgparseDataclass, prog='prog'):
        pass
    assert DC1.__settings__.prog == 'prog'
    @dataclass
    class DC2(ArgparseDataclass, prog='prog'):
        pass
    assert DC2.__settings__.prog == 'prog'
    @dataclass
    class DC3(JSONDataclass, DC2):
        pass
    assert DC3.__settings__.prog == 'prog'
    @dataclass
    class DC4(JSONDataclass, DC2, prog='new-prog'):
        pass
    assert DC4.__settings__.prog == 'new-prog'
    @dataclass
    class DC5(ArgparseDataclass, JSONDataclass, prog='prog'):
        pass
    assert DC5.__settings__.prog == 'prog'
    @dataclass
    class DC6(JSONBaseDataclass, ArgparseDataclass, prog='prog'):
        pass
    assert DC6.__settings__.prog == 'prog'
    @dataclass
    class DC7(ArgparseDataclass, JSONBaseDataclass, prog='prog'):
        pass
    assert DC7.__settings__.prog == 'prog'

def test_json_subprocess_dataclass():
    """Tests subclassing both JSONDataclass and SubprocessDataclass."""
    @dataclass
    class DC1(JSONDataclass, SubprocessDataclass):
        pass
    assert DC1.__settings__._store_type == 'off'
    assert DC1.__settings__.exec is None
    @dataclass
    class DC2(SubprocessDataclass, JSONDataclass):
        pass
    assert DC2.__settings__._store_type == 'off'
    assert DC2.__settings__.exec is None
    @dataclass
    class DC(JSONBaseDataclass):
        pass
    @dataclass
    class DC3(DC, SubprocessDataclass):
        pass
    assert DC3.__settings__._store_type == 'qualname'
    assert DC3.__settings__.exec is None
    @dataclass
    class DC4(SubprocessDataclass, DC):
        pass
    assert DC4.__settings__._store_type == 'qualname'
    assert DC4.__settings__.exec is None
    @dataclass
    class DC5(SubprocessDataclass, DC, store_type='off', exec='prog'):
        pass
    assert DC5.__settings__._store_type == 'off'
    assert DC5.__settings__.exec == 'prog'
