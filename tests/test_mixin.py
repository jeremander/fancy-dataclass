from dataclasses import astuple, dataclass, field
from typing import ClassVar

import pytest

from fancy_dataclass.mixin import DataclassMixin, DataclassMixinSettings, FieldSettings
from fancy_dataclass.utils import get_dataclass_fields


def test_field_settings():
    """Tests the FieldSettings class."""
    fld_empty = field()
    fld_pos = field(metadata={'positive': True})
    fld_wrong_type = field(metadata={'positive': 1})
    class MyFieldSettings1(FieldSettings):
        pass
    with pytest.raises(TypeError, match='MyFieldSettings1 is not a dataclass'):
        _ = MyFieldSettings1.from_field(fld_pos)
    MyFieldSettings1 = dataclass(MyFieldSettings1)
    # extra metadata is ignored
    assert MyFieldSettings1.from_field(fld_pos) == MyFieldSettings1()
    @dataclass
    class MyFieldSettings2(FieldSettings):
        positive: bool
    assert MyFieldSettings2.from_field(fld_pos) == MyFieldSettings2(True)
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'positive'"):
        _ = MyFieldSettings2.from_field(fld_empty)
    with pytest.raises(TypeError, match="expected type .* for field 'positive', got .*"):
        _ = MyFieldSettings2.from_field(fld_wrong_type)
    @dataclass
    class MyFieldSettings3(FieldSettings):
        positive: bool = False
    assert MyFieldSettings3.from_field(fld_pos) == MyFieldSettings3(True)
    assert MyFieldSettings3.from_field(fld_empty) == MyFieldSettings3(False)


@dataclass
class MySettingsOpt(DataclassMixinSettings):
    enhanced: bool = False

@dataclass
class MySettingsReq(DataclassMixinSettings):
    enhanced: bool


class TestDataclassMixin:
    """Tests the DataclassMixin class."""

    def test_post_dataclass_wrap_hook(self):
        """Tests the __post_dataclass_wrap__ hook."""
        class MyMixin(DataclassMixin):
            @classmethod
            def __post_dataclass_wrap__(cls, wrapped_cls) -> None:
                wrapped_cls._my_value = 123
        assert not hasattr(MyMixin, '_my_value')
        # method triggers when wrapped into a dataclass
        MyMixin2 = dataclass(MyMixin)
        assert MyMixin2 is MyMixin
        assert MyMixin2.__name__ == 'MyMixin'
        assert MyMixin2._my_value == 123

    def test_settings_valid(self):
        """Tests the settings instantiation mechanism of DataclassMixin."""
        class MyMixin(DataclassMixin):
            pass
        assert MyMixin.__settings_type__ is None
        assert MyMixin.__settings__ is None
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings_type__ is MySettingsOpt
        # base class instantiates the default settings from the type
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        @dataclass
        class MyDC(MyMixin):
            pass
        assert MyDC.__settings_type__ is MySettingsOpt
        assert MyDC.__settings__ == MySettingsOpt(enhanced=False)
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        # settings propagate to subclasses
        @dataclass
        class MyDCSub(MyDC):
            pass
        assert MyDCSub.__settings_type__ is MySettingsOpt
        assert MyDCSub.__settings__ == MySettingsOpt(enhanced=True)
        # can set keyword argument on the base mixin class
        @dataclass
        class MyMixin(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        # test that subclass overrides settings
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        @dataclass
        class MyDC2(MyDC, enhanced=False):
            pass
        assert MyMixin.__settings__ == MySettingsOpt(enhanced=False)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        assert MyDC2.__settings__ == MySettingsOpt(enhanced=False)
        # valid settings
        @dataclass
        class MyDC(MyMixin):
            __settings__ = MySettingsOpt(enhanced=True)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        # can set required keyword arg on the base class
        @dataclass
        class MyMixinReq(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsReq
        @dataclass
        class MyDC(MyMixinReq):
            ...
        assert MyDC.__settings__ == MySettingsReq(enhanced=False)
        @dataclass
        class MyDC(MyMixinReq):
            __settings__ = None
        assert MyDC.__settings__ == MySettingsReq(enhanced=False)

    def test_settings_invalid(self):
        """Tests error conditions for DataclassMixin settings."""
        class MyMixin(DataclassMixin):
            pass
        # pass unrecognized kwarg
        with pytest.raises(TypeError, match="unknown settings field 'enhanced' for MyDC1"):
            @dataclass
            class MyDC1(MyMixin, enhanced=True):
                pass
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettingsOpt
        with pytest.raises(TypeError, match="unknown settings field 'fake' for MyDC2"):
            @dataclass
            class MyDC2(MyMixin, fake=True):
                pass
        # fail to pass required setting
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
            @dataclass
            class MyMixin(DataclassMixin):
                __settings_type__ = MySettingsReq
        @dataclass
        class MyMixinReq(DataclassMixin):
            __settings_type__ = MySettingsReq
            __settings__ = MySettingsReq(enhanced=False)
        # explicitly set __settings__ attribute
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'enhanced'"):
            @dataclass
            class MyDC3(MyMixinReq):
                __settings__ = None
        with pytest.raises(TypeError, match="settings for MyDC4 missing expected field 'enhanced'"):
            @dataclass
            class MyDC4(MyMixin):
                __settings__ = 1
        # set settings to a regular class
        class NonDCSettings:
            pass
        with pytest.raises(TypeError, match='invalid settings type NonDCSettings for MyDC5'):
            @dataclass
            class MyDC5(MyMixin):
                __settings_type__ = NonDCSettings
        # set settings to a non-dataclass subclass of DataclassMixinSettings
        class NonDCSettings(DataclassMixinSettings):
            pass
        with pytest.raises(TypeError, match='NonDCSettings is not a dataclass'):
            @dataclass
            class MyDC6(MyMixin):
                __settings_type__ = NonDCSettings
        # __settings__ attribute conflicts with inheritance kwargs
        with pytest.raises(TypeError, match="redundant specification of field 'enhanced' for MyDC7"):
            @dataclass
            class MyDC7(MyMixinReq, enhanced=False):
                __settings__ = MySettingsReq(enhanced=True)

    def test_settings_merged(self):
        """Tests merging of settings when subclassing multiple DataclassMixins."""
        @dataclass
        class Settings1(DataclassMixinSettings):
            a: int = 1
        class Mixin1(DataclassMixin):
            __settings_type__ = Settings1
        @dataclass
        class Settings2(DataclassMixinSettings):
            b: int = 2
            c: int = 3
        class Mixin2(DataclassMixin):
            __settings_type__ = Settings2
        @dataclass
        class Settings3(DataclassMixinSettings):
            pass
        class Mixin3(DataclassMixin):
            __settings_type__ = Settings3
        @dataclass
        class Settings4(DataclassMixinSettings):
            c: int = 4
            d: int = 5
        class Mixin4(DataclassMixin):
            __settings_type__ = Settings4
        def _check_stype(cls, field_names):
            assert [fld.name for fld in get_dataclass_fields(cls.__settings_type__)] == field_names
            assert isinstance(cls.__settings__, cls.__settings_type__)
        @dataclass
        class DC1(Mixin1):
            ...
        _check_stype(DC1, ['a'])
        assert DC1.__settings__.a == 1
        @dataclass
        class DC2(Mixin1, Mixin2, Mixin3):
            ...
        assert DC2.__settings_type__.__name__ == 'MiscDataclassSettings'
        _check_stype(DC2, ['a', 'b', 'c'])
        assert astuple(DC2.__settings__) == (1, 2, 3)
        @dataclass
        class DC3(Mixin1, Mixin2, Mixin3):
            __settings_type__ = None
        _check_stype(DC3, ['a', 'b', 'c'])
        assert astuple(DC3.__settings__) == (1, 2, 3)
        @dataclass
        class DC4(Mixin1, Mixin2, Mixin3):
            __settings_type__ = Settings2
        assert DC4.__settings_type__ is Settings2
        assert isinstance(DC4.__settings__, Settings2)
        _check_stype(DC4, ['b', 'c'])
        assert DC4.__settings__ == Settings2(2, 3)
        @dataclass
        class DC5(Mixin1, Mixin2, Mixin3, a=100):
            ...
        assert astuple(DC5.__settings__) == (100, 2, 3)
        with pytest.raises(TypeError, match="unknown settings field 'a' for DC6"):
            @dataclass
            class DC6(Mixin1, Mixin2, Mixin3, a=100):
                __settings_type__ = Settings2
        @dataclass
        class DC7(Mixin1, Mixin2, Mixin3, b=100):
            __settings_type__ = Settings2
        assert astuple(DC7.__settings__) == (100, 3)
        # custom settings type that accommodates all the base classes' fields
        @dataclass
        class Settings5(DataclassMixinSettings):
            a: int = 1
            b: int = 2
            c: int = 3
            d: int = 4
        @dataclass
        class DC8(Mixin1, Mixin2, Mixin3):
            __settings_type__ = Settings5
        assert DC8.__settings__ == Settings5(1, 2, 3, 4)
        @dataclass
        class DC9(Mixin1, Mixin2, Mixin3, b=100):
            __settings_type__ = Settings5
        assert DC9.__settings__ == Settings5(1, 100, 3, 4)
        @dataclass
        class DC10(Mixin1, Mixin2, Mixin3, b=50, d=100):
            __settings_type__ = Settings5
        assert DC10.__settings__ == Settings5(1, 50, 3, 100)
        with pytest.raises(TypeError, match="error merging base class settings for DC11: duplicate field name 'c'"):
            @dataclass
            class DC11(Mixin2, Mixin4):
                ...

    def test_replace(self):
        """Tests the `_replace` method."""
        @dataclass
        class DC12(DataclassMixin):
            a: ClassVar[int] = 1
            b: int
        obj = DC12(1)
        assert obj._replace(b=2) == DC12(2)
        # no type-checking occurs
        assert obj._replace(b='b') == DC12('b')
        # replace a non-field
        with pytest.raises(TypeError, match="'c' is not a valid field for DC12"):
            _ = obj._replace(c=3)
        # replace a ClassVar field
        with pytest.raises(TypeError, match="'a' is not a valid field for DC12"):
            _ = obj._replace(a=3)
