from dataclasses import dataclass

import pytest

from fancy_dataclass import ArgparseDataclass, ConfigDataclass, DictDataclass, JSONBaseDataclass, JSONDataclass, SQLDataclass, SubprocessDataclass


# DEFAULT_MIXINS = [ArgparseDataclass, ConfigDataclass, JSONBaseDataclass, SQLDataclass, SubprocessDataclass]
DEFAULT_MIXINS = [JSONBaseDataclass, ArgparseDataclass, ConfigDataclass, SQLDataclass, SubprocessDataclass]


def test_multiple_inheritance():
    """Tests inheritance from multiple DataclassMixins."""
    @dataclass
    class MyDC1(ArgparseDataclass, JSONDataclass):
        x: int
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
        cls = mixin_cls.wrap_dataclass(cls)
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
