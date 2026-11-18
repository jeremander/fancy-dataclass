from dataclasses import dataclass, field, fields
from typing import Annotated, ClassVar

import annotated_doc
import pytest
from typing_extensions import Doc, Self

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import DocFieldSettings, FieldSettings, MixinSettings
from fancy_dataclass.utils import FieldTypeValidationError


def test_field_settings() -> None:
    """Tests the FieldSettings class."""
    fld_empty = field()
    fld_pos = field(metadata={'positive': True})
    fld_wrong_type = field(metadata={'positive': 1})
    class MyFieldSettings1(FieldSettings):
        pass
    with pytest.raises(TypeError, match='MyFieldSettings1 is not a dataclass'):
        _ = MyFieldSettings1.from_field(fld_pos)
    MyFieldSettings1 = dataclass(MyFieldSettings1)  # type: ignore[misc]
    # extra metadata is ignored
    assert MyFieldSettings1.from_field(fld_pos) == MyFieldSettings1()
    @dataclass
    class MyFieldSettings2(FieldSettings):
        positive: bool
    assert MyFieldSettings2.from_field(fld_pos) == MyFieldSettings2(True)
    with pytest.raises(TypeError, match="missing 1 required positional argument: 'positive'"):
        _ = MyFieldSettings2.from_field(fld_empty)
    with pytest.raises(
        TypeError,
        match="field 'positive' of .*MyFieldSettings2: value 1 does not match expected type bool",
    ):
        _ = MyFieldSettings2.from_field(fld_wrong_type)
    @dataclass
    class MyFieldSettings3(FieldSettings):
        positive: bool = False
    assert MyFieldSettings3.from_field(fld_pos) == MyFieldSettings3(True)
    assert MyFieldSettings3.from_field(fld_empty) == MyFieldSettings3(False)


@dataclass
class MySettingsOpt(MixinSettings):
    enhanced: bool = False

@dataclass
class MySettingsReq(MixinSettings):
    enhanced: bool


class TestDataclassMixin:
    """Tests the DataclassMixin class."""

    def test_post_dataclass_wrap_hook(self) -> None:
        """Tests the __post_dataclass_wrap__ hook."""
        class MyMixin(DataclassMixin):
            _my_value: int
            @classmethod
            def __post_dataclass_wrap__(cls, wrapped_cls: type[Self]) -> None:
                wrapped_cls._my_value = 123
        assert not hasattr(MyMixin, '_my_value')
        # method triggers when wrapped into a dataclass
        MyMixin2 = dataclass(MyMixin)
        assert MyMixin2 is MyMixin
        assert MyMixin2.__name__ == 'MyMixin'
        assert MyMixin2._my_value == 123

    def test_settings_valid(self) -> None:
        """Tests the settings instantiation mechanism of DataclassMixin."""
        class MyMixin(DataclassMixin):
            pass
        assert MyMixin.__settings_type__ is None
        assert MyMixin.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyMixin._class_settings()
        class MyMixin(DataclassMixin):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings_type__ is MySettingsOpt
        assert MyMixin.__settings__ is None
        assert MyMixin._class_settings() == MySettingsOpt(enhanced=False)
        # base class instantiates the default settings from the type
        @dataclass
        class MyDC(MyMixin):
            pass
        assert MyDC.__settings_type__ is None
        assert MyDC.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC._class_settings()
        assert MyDC._class_settings(base=MyMixin) == MySettingsOpt(enhanced=False)
        # override default field with a kwarg
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyDC.__settings_type__ is None
        assert MyDC.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC._class_settings()
        assert MyDC._class_settings(base=MyMixin) == MySettingsOpt(enhanced=True)
        # settings propagate to subclasses
        @dataclass
        class MyDCSub(MyDC):
            pass
        assert MyDCSub.__settings_type__ is None
        assert MyDCSub.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDCSub._class_settings()
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDCSub._class_settings(base=MyDC)
        assert MyDCSub._class_settings(base=MyMixin) == MySettingsOpt(enhanced=True)
        # can set keyword argument on the base mixin class
        @dataclass
        class MyMixin(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsOpt
        assert MyMixin.__settings__ is None
        assert MyMixin._class_settings() == MySettingsOpt(enhanced=False)
        # test that subclass overrides settings
        @dataclass
        class MyDC(MyMixin, enhanced=True):
            pass
        assert MyDC.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC._class_settings()
        assert MyDC._class_settings(base=MyMixin) == MySettingsOpt(enhanced=True)
        @dataclass
        class MyDC2(MyDC, enhanced=False):
            pass
        assert MyDC2.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC2._class_settings()
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC2._class_settings(base=MyDC)
        assert MyDC2._class_settings(base=MyMixin) == MySettingsOpt(enhanced=False)
        # valid settings
        @dataclass
        class MyDC(MyMixin):
            __settings__ = MySettingsOpt(enhanced=True)
        assert MyDC.__settings__ == MySettingsOpt(enhanced=True)
        # subclasses do *not* inherit __settings__ from their parent
        class MyDCSub(MyDC):
            pass
        assert MyDCSub.__settings__ is None
        MyDCSub = dataclass(MyDCSub)
        assert MyDCSub.__settings__ is None
        # can set required keyword arg on the base class
        @dataclass
        class MyMixinReq(DataclassMixin, enhanced=False):
            __settings_type__ = MySettingsReq
        @dataclass
        class MyDC(MyMixinReq):
            pass
        assert MyDC.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC._class_settings()
        assert MyDC._class_settings(base=MyMixinReq) == MySettingsReq(enhanced=False)
        # explicitly set __settings__ attribute of child class to None
        @dataclass
        class MyMixinReq(DataclassMixin):
            __settings_type__ = MySettingsReq
            __settings__ = MySettingsReq(enhanced=False)
        @dataclass
        class MyDC(MyMixinReq):
            __settings__ = None
        assert MyDC.__settings__ is None
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = MyDC._class_settings()
        assert MyDC._class_settings(base=MyMixinReq) == MySettingsReq(enhanced=False)

    def test_settings_invalid(self) -> None:
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
        # set __settings__ attribute to invalid type
        with pytest.raises(TypeError, match='invalid __settings__ type int for MyDC3'):
            @dataclass
            class MyDC3(MyMixin):
                __settings__ = 1  # type: ignore[assignment]
        # set settings to a regular class
        class NonDCSettings:
            pass
        with pytest.raises(TypeError, match='NonDCSettings is not a dataclass'):
            @dataclass
            class MyDC4(MyMixin):
                __settings_type__ = NonDCSettings  # type: ignore[assignment]
        # set settings to a non-dataclass subclass of MixinSettings
        class NonDCSettings(MixinSettings):
            pass
        with pytest.raises(TypeError, match='NonDCSettings is not a dataclass'):
            @dataclass
            class MyDC5(MyMixin):
                __settings_type__ = NonDCSettings  # type: ignore[assignment]
        # __settings__ attribute conflicts with inheritance kwargs
        with pytest.raises(TypeError, match="redundant specification of field 'enhanced' for MyDC6"):
            @dataclass
            class MyDC6(MyMixinReq, enhanced=False):
                __settings__ = MySettingsReq(enhanced=True)

    def test_reconcile_class_settings(self) -> None:
        """Tests reconciliation of class settings when subclassing multiple DataclassMixins."""
        @dataclass
        class Settings1(MixinSettings):
            a: int = 1
        class Mixin1(DataclassMixin):
            __settings_type__ = Settings1
        @dataclass
        class Settings2(MixinSettings):
            b: int = 2
            c: int = 3
        class Mixin2(DataclassMixin):
            __settings_type__ = Settings2
        @dataclass
        class Settings3(MixinSettings):
            pass
        class Mixin3(DataclassMixin):
            __settings_type__ = Settings3
        @dataclass
        class Settings4(MixinSettings):
            c: int = 4
            d: int = 5
        class Mixin4(DataclassMixin):
            __settings_type__ = Settings4
        @dataclass
        class DC1(Mixin1):
            ...
        assert DC1.__settings_type__ is None
        assert DC1.__settings__ is None
        assert DC1._class_settings(base=Mixin1) == Settings1()
        @dataclass
        class DC2(Mixin1, Mixin2, Mixin3):
            ...
        assert DC2.__settings_type__ is None
        assert DC2.__settings__ is None
        assert DC2._class_settings(base=Mixin1) == Settings1()
        assert DC2._class_settings(base=Mixin2) == Settings2()
        assert DC2._class_settings(base=Mixin3) == Settings3()
        @dataclass
        class DC3(Mixin1, Mixin2, Mixin3):
            __settings_type__ = None
        assert DC3.__settings_type__ is None
        assert DC3.__settings__ is None
        assert DC3._class_settings(base=Mixin1) == Settings1()
        assert DC3._class_settings(base=Mixin2) == Settings2()
        assert DC3._class_settings(base=Mixin3) == Settings3()
        @dataclass
        class DC4(Mixin1, Mixin2, Mixin3):
            __settings_type__ = Settings2
        assert DC4.__settings_type__ is Settings2
        assert DC4.__settings__ is None
        assert DC4._class_settings(base=Mixin1) == Settings1()
        assert DC4._class_settings(base=Mixin2) == Settings2()
        assert DC4._class_settings(base=Mixin3) == Settings3()
        assert DC4._class_settings() == Settings2()
        @dataclass
        class DC5(Mixin1, Mixin2, Mixin3, a=100):
            ...
        assert DC5.__settings_type__ is None
        assert DC5.__settings__ is None
        assert DC5._class_settings(base=Mixin1) == Settings1(a=100)
        assert DC5._class_settings(base=Mixin2) == Settings2()
        assert DC5._class_settings(base=Mixin3) == Settings3()
        with pytest.raises(TypeError, match='could not get class settings'):
            _ = DC5._class_settings()
        @dataclass
        class DC6(Mixin1, Mixin2, Mixin3, a=100):
            __settings_type__ = Settings2
        assert DC6.__settings_type__ is Settings2
        assert DC6.__settings__ is None
        assert DC6._class_settings(base=Mixin1) == Settings1(a=100)
        assert DC6._class_settings(base=Mixin2) == Settings2()
        assert DC6._class_settings(base=Mixin3) == Settings3()
        assert DC6._class_settings() == Settings2()
        @dataclass
        class DC7(Mixin1, Mixin2, Mixin3, b=100):
            __settings_type__ = Settings2
        assert DC7.__settings_type__ is Settings2
        assert DC7.__settings__ is None
        assert DC7._class_settings(base=Mixin1) == Settings1()
        assert DC7._class_settings(base=Mixin2) == Settings2(b=100)
        assert DC7._class_settings(base=Mixin3) == Settings3()
        assert DC7._class_settings() == Settings2(b=100)
        # settings classes for bases have a conflicting field
        with pytest.raises(TypeError, match="error reconciling base class settings for DC8: duplicate field name 'c'"):
            @dataclass
            class DC8(Mixin2, Mixin4):
                ...
        # custom settings type with a conflicting field
        with pytest.raises(TypeError, match="error reconciling base class settings for DC9: duplicate field name 'c'"):
            @dataclass
            class DC9(Mixin2):
                __settings_type__ = Settings4

    def test_replace(self) -> None:
        """Tests the `_replace` method."""
        @dataclass
        class DC12(DataclassMixin):
            a: ClassVar[int] = 1
            b: int
        obj = DC12(1)
        assert obj._replace(b=2) == DC12(2)
        # no type-checking occurs
        assert obj._replace(b='b') == DC12('b')  # type: ignore[arg-type]
        # replace a non-field
        with pytest.raises(TypeError, match="'c' is not a valid field for DC12"):
            _ = obj._replace(c=3)
        # replace a ClassVar field
        with pytest.raises(TypeError, match="'a' is not a valid field for DC12"):
            _ = obj._replace(a=3)

    def test_doc_settings(self) -> None:
        """Tests DocFieldSettings."""
        @dataclass
        class DocMixin(DataclassMixin):
            __field_settings_type__ = DocFieldSettings
        @dataclass
        class DC1(DocMixin):
            a: int = 1  # no doc
            b: int = field(default=2, metadata={'doc': 'b'})  # metadata doc field
            c: Annotated[int, Doc('c')] = 3  # Annotated Doc field
            d: Annotated[int, 'd'] = 4  # string not wrapped in a Doc
            e: Annotated[int, Doc('bad'), Doc('e')] = 5  # multiple Docs (per PEP 727, use the last one)
            f: Annotated[int, Doc(6)] = 6  # non-string Doc (currently permitted)
            g: Annotated[int, Doc('g1')] = field(
                default=7,
                metadata={'doc': 'g2'},
            )  # both Doc and metadata (latter takes precedence)
            # stringized annotations:
            # avoid evaluating them since that would occur at import time
            h: "Annotated[int, Doc('h')]" = 8
            # stringized annotation, fully qualified
            i: "typing_extensions.Annotated[int, typing_extensions.Doc('i')]" = 9  # type: ignore[name-defined]  # noqa: F821
            # this is OK since the Annotated part is not stringized
            j: Annotated['int', Doc('j')] = 10
            k: Annotated[int, annotated_doc.Doc('k')] = 11
            l: Annotated[int, Doc('bad'), annotated_doc.Doc('l')] = 12  # noqa: E741
        docs = {}
        for fld in fields(DC1):
            fld_settings = DC1._field_settings(fld)
            assert isinstance(fld_settings, DocFieldSettings)
            docs[fld.name] = fld_settings.doc
        assert docs == {
            'a': None,
            'b': 'b',
            'c': 'c',
            'd': None,
            'e': 'e',
            'f': 6,
            'g': 'g2',
            'h': None,
            'i': None,
            'j': 'j',
            'k': 'k',
            'l': 'l',
        }
        # try to convert a field with unknown type to DocFieldSettings
        @dataclass
        class DC2:
            x: 'fake-type'  # type: ignore  # noqa: F821
        fld = fields(DC2)[0]
        settings = DocFieldSettings.from_field(fld)
        assert settings == DocFieldSettings(doc=None)
        @dataclass
        class DC3(DocMixin):
            x: 'fake-type'  # type: ignore  # noqa: F821
        assert DC3._field_settings(fields(DC3)[0]) == DocFieldSettings(doc=None)

    def test_invalid_settings_fields(self) -> None:
        """Tests field validation of MixinSettings and FieldSettings."""
        @dataclass
        class MyMixinSettings(MixinSettings):
            x: int
        @dataclass
        class MyFieldSettings(FieldSettings):
            x: int
        for cls in [MyMixinSettings, MyFieldSettings]:
            with pytest.raises(
                FieldTypeValidationError,
                match=f"field 'x' of .*{cls.__name__}: value '1' does not match expected type int",
            ):
                _ = cls('1')  # type: ignore[arg-type]
