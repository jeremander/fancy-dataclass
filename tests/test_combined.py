from dataclasses import dataclass

from fancy_dataclass import ArgparseDataclass, ConfigDataclass, JSONDataclass, SQLDataclass, SubprocessDataclass


DEFAULT_MIXINS = [ArgparseDataclass, ConfigDataclass, JSONDataclass, SQLDataclass, SubprocessDataclass]


def test_multiple_inheritance():
    """Tests inheritance from multiple DataclassMixins."""
    @dataclass
    class MyDC1(ArgparseDataclass, JSONDataclass):  # type: ignore[misc]
        x: int
    # alternatively, add in mixins dynamically with wrap_dataclass
    @dataclass
    class MyDC2:
        x: int
    MyDC2 = JSONDataclass.wrap_dataclass(ArgparseDataclass.wrap_dataclass(MyDC2))  # type: ignore
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
        cls = mixin_cls.wrap_dataclass(cls)  # type: ignore[assignment]
    mro = cls.mro()
    obj = cls(5)
    for mixin_cls in DEFAULT_MIXINS:
        assert mixin_cls in mro
        assert isinstance(obj, mixin_cls)
