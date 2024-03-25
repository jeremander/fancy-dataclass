from dataclasses import dataclass

import pytest

from fancy_dataclass.utils import DataclassMixin, DataclassMixinSettings


def test_dataclass_mixin_settings():
    """Tests the settings instantiation mechanism of DataclassMixin."""
    @dataclass
    class MySettings(DataclassMixinSettings):
        enhanced: bool = False
    class MyMixin(DataclassMixin):
        pass
    assert MyMixin.__settings_type__ is None
    assert MyMixin.__settings__ is None
    with pytest.raises(TypeError, match="unknown settings field 'enhanced' for MyDC"):
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
    class MyMixin(DataclassMixin):
        __settings_type__ = MySettings
    assert MyMixin.__settings_type__ is MySettings
    # base class instantiates the default settings from the type
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    @dataclass
    class MyDC(MyMixin):  # noqa: F811
        pass
    assert MyDC.__settings_type__ is MySettings
    assert MyDC.__settings__ == MySettings(enhanced=False)
    @dataclass
    class MyDC(MyMixin, enhanced=True):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    with pytest.raises(TypeError, match="unknown settings field 'fake' for MyDC"):
        @dataclass
        class MyDC(MyMixin, fake=True):
            pass
    # test required settings
    @dataclass
    class MySettings(DataclassMixinSettings):
        enhanced: bool
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
        @dataclass
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettings
    # can set keyword argument on the base mixin class
    @dataclass
    class MyMixin(DataclassMixin, enhanced=False):
        __settings_type__ = MySettings
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    # test that subclass overrides settings
    @dataclass
    class MyDC(MyMixin, enhanced=True):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    @dataclass
    class MyDC2(MyDC, enhanced=False):
        pass
    assert MyMixin.__settings__ == MySettings(enhanced=False)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    assert MyDC2.__settings__ == MySettings(enhanced=False)
    # explicitly set __settings__ attribute
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
        @dataclass
        class MyDC(MyMixin):
            __settings__ = None
    with pytest.raises(TypeError, match='settings type of MyDC must be MySettings'):
        @dataclass
        class MyDC(MyMixin):
            __settings__ = 1
    @dataclass
    class MyDC(MyMixin):
        __settings__ = MySettings(enhanced=True)
    assert MyDC.__settings__ == MySettings(enhanced=True)
    # inheritance kwargs override __settings__ attribute
    @dataclass
    class MyDC(MyMixin, enhanced=False):
        __settings__ = MySettings(enhanced=True)
    assert MyDC.__settings__ == MySettings(enhanced=False)
