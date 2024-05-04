from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Optional, Sequence

import pytest

from fancy_dataclass import ArgparseDataclass, ConfigDataclass, DictDataclass, JSONBaseDataclass, JSONDataclass, SQLDataclass, SubprocessDataclass, TOMLDataclass
from fancy_dataclass.cli import ArgparseDataclassFieldSettings, ArgparseDataclassSettings
from fancy_dataclass.dict import DictDataclassSettings
from fancy_dataclass.mixin import DataclassMixin, DataclassMixinSettings, FieldSettings
from fancy_dataclass.subprocess import SubprocessDataclassFieldSettings
from fancy_dataclass.utils import merge_dataclasses


DEFAULT_MIXINS = [JSONBaseDataclass, ArgparseDataclass, ConfigDataclass, SQLDataclass, TOMLDataclass]


def test_multiple_inheritance():
    """Tests inheritance from multiple DataclassMixins."""
    @dataclass
    class MyDC1(ArgparseDataclass, JSONDataclass):
        x: int
    assert JSONDataclass.__settings_type__ is DictDataclassSettings
    assert issubclass(MyDC1.__settings_type__, DictDataclassSettings)
    assert issubclass(MyDC1.__settings_type__, ArgparseDataclassSettings)
    # assert all(cls.__settings_type__ is DictDataclassSettings for cls in [JSONDataclass, MyDC1])
    # alternatively, add in mixins dynamically with wrap_dataclass
    @dataclass
    class MyDC2:
        x: int
    MyDC2 = JSONDataclass.wrap_dataclass(ArgparseDataclass.wrap_dataclass(MyDC2))
    for cls in [MyDC1, MyDC2]:
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
    class MyDC:
        x: int
    cls = MyDC
    for mixin_cls in DEFAULT_MIXINS:
        cls = mixin_cls.wrap_dataclass(cls, qualified_type=True)
    mro = cls.mro()
    obj = cls(5)
    for mixin_cls in DEFAULT_MIXINS:
        assert mixin_cls in mro
        assert isinstance(obj, mixin_cls)

def test_invalid_inheritance():
    """Tests invalid inheritance (e.g. parent class before its subclass)."""
    # this order works
    @dataclass
    class MyDC(JSONDataclass, DictDataclass):
        pass
    assert issubclass(MyDC, DictDataclass)
    assert issubclass(MyDC, JSONDataclass)
    @dataclass
    class MyDC:
        pass
    MyDC1 = JSONDataclass.wrap_dataclass(MyDC)
    MyDC2 = DictDataclass.wrap_dataclass(MyDC1)
    # already a subclass, so wrapping does nothing
    assert MyDC2 is MyDC1
    # this order doesn't work
    with pytest.raises(TypeError, match='Cannot create a consistent'):
        @dataclass
        class MyDC(DictDataclass, JSONDataclass):
            pass
    MyDC1 = DictDataclass.wrap_dataclass(MyDC)
    # this works because JSONDataclass is not a subclass of MyDC1
    MyDC2 = JSONDataclass.wrap_dataclass(MyDC1)
    assert issubclass(MyDC2, DictDataclass)
    assert issubclass(MyDC2, JSONDataclass)
    assert issubclass(MyDC2, MyDC1)
    assert MyDC2 is not MyDC1

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
    """Tests multiple inheritance from `DataclassMixinSettings` classes with overlapping field names."""
    @dataclass
    class Settings1(DataclassMixinSettings):
        a: int = 1
    @dataclass
    class Settings2(DataclassMixinSettings):
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

def test_argparse_subprocess():
    """Tests inheritance from both ArgparseDataclass and SubprocessDataclass."""
    # field settings have a name collision, 'args'
    with pytest.raises(TypeError, match="duplicate field name 'args'"):
        class ArgparseSubprocessDC(ArgparseDataclass, SubprocessDataclass):
            ...
    # field settings have a duplicate field, so make a custom merged settings class and set it explicitly
    ArgparseSubprocessFieldSettings = merge_dataclasses(ArgparseDataclassFieldSettings, SubprocessDataclassFieldSettings, allow_duplicates=True)
    class ArgparseSubprocessDC2(ArgparseDataclass, SubprocessDataclass):
        __field_settings_type__ = ArgparseSubprocessFieldSettings
    @dataclass
    class MyDC2(ArgparseSubprocessDC2):
        x: int = field(metadata={'args': ['--ex']})
    # same attribute is used for both parent classes' FieldSettings
    obj = MyDC2(1)
    fld_settings = MyDC2._field_settings(obj.__dataclass_fields__['x'])
    assert fld_settings.adapt_to(ArgparseDataclassFieldSettings).args == ['--ex']
    assert fld_settings.adapt_to(SubprocessDataclassFieldSettings).args == ['--ex']
    # custom adapter for FieldSettings
    @dataclass
    class FieldSettings3(FieldSettings):
        input_args: Optional[Sequence[str]] = None
        output_args: Optional[Sequence[str]] = None
        def adapt_to(self, dest_type):
            if dest_type is ArgparseDataclassFieldSettings:
                return dest_type(args=self.input_args)
            if dest_type is SubprocessDataclassFieldSettings:
                return dest_type(args=self.output_args)
            return super().adapt_to(dest_type)
    class ArgparseSubprocessDC3(ArgparseDataclass, SubprocessDataclass):
        __field_settings_type__ = FieldSettings3
    @dataclass
    class MyDC3(ArgparseSubprocessDC3):
        x: int = field(metadata={'args': ['--ex']})
    obj = MyDC3(1)
    fld_settings = MyDC3._field_settings(obj.__dataclass_fields__['x'])
    assert fld_settings == FieldSettings3(input_args=None, output_args=None)
    assert fld_settings.adapt_to(ArgparseDataclassFieldSettings).args is None
    assert fld_settings.adapt_to(SubprocessDataclassFieldSettings).args is None
    @dataclass
    class MyDC4(ArgparseSubprocessDC3):
        x: int = field(metadata={'input_args': ['--ex1'], 'output_args': ['--ex2']})
    obj = MyDC4(1)
    fld_settings = MyDC4._field_settings(obj.__dataclass_fields__['x'])
    assert fld_settings == FieldSettings3(input_args=['--ex1'], output_args=['--ex2'])
    assert fld_settings.adapt_to(ArgparseDataclassFieldSettings).args == ['--ex1']
    assert fld_settings.adapt_to(SubprocessDataclassFieldSettings).args == ['--ex2']
