from collections.abc import Iterable
from dataclasses import MISSING, Field, dataclass
from typing import Any, ClassVar, Optional, TypeVar, cast

from typing_extensions import Self

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import (
    DataclassType,
    FieldTypeValidationError,
    _validate_dataclass_field,
    get_dataclass_fields,
    type_is_classvar,
)


T = TypeVar('T')


def _first_non_null(vals: Iterable[Optional[T]], *, default: T) -> T:
    """Gets the first non-None value from the given iterable, defaulting to a given value if all are None."""
    for val in vals:
        if val is not None:
            return val
    return default


@dataclass(frozen=True, kw_only=True)
class _FieldValidationFlags:
    """A pair of flags indicating whether a field should be validated for initialization and assignment."""

    _validate_init: Optional[bool]
    _validate_assign: Optional[bool]

    @property
    def validate_init(self) -> bool:
        return True if (self._validate_init is None) else self._validate_init

    @property
    def validate_assign(self) -> bool:
        return True if (self._validate_assign is None) else self._validate_assign


@dataclass(kw_only=True)
class _ValidationSettings:

    validate_init: Optional[bool] = None
    validate_assign: Optional[bool] = None
    validate: Optional[bool] = None

    @property
    def flags(self) -> _FieldValidationFlags:
        return _FieldValidationFlags(
            _validate_init=self.validate if (self.validate_init is None) else self.validate_init,
            _validate_assign=self.validate if (self.validate_assign is None) else self.validate_assign,
        )


##########
# MIXINS #
##########

@dataclass(kw_only=True)
class ValidatedDataclassSettings(MixinSettings, _ValidationSettings):
    """Class-level settings for the [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] mixin.

    Subclasses of `ValidatedDataclass` may set the following fields as keyword arguments during inheritance:

    - `validate_init`: if `True`, validate all fields upon initialization (default `True`)
    - `validate_assign`: if `True`, validate all fields upon assignment (default `True`)
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously"""


@dataclass(kw_only=True)
class ValidatedDataclassFieldSettings(FieldSettings, _ValidationSettings):
    """Settings for [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `validate_init`: if set to `True` or `False`, overrides the class-level `validate_init` flag for whether to
    validate the field upon initialization
    - `validate_assign`: if set to `True` or `False`, overrides the class-level `validate_assign` flag for whether to
    validate the field upon assignment
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously
    """


class ValidatedDataclass(DataclassMixin):
    """Mixin class for dataclasses which can validate their fields upon initialization or assignment."""

    __settings_type__: ClassVar[Optional[type[MixinSettings]]] = ValidatedDataclassSettings
    __settings__: ClassVar[Optional[MixinSettings]] = ValidatedDataclassSettings()
    __field_settings_type__ = ValidatedDataclassFieldSettings

    @classmethod
    def _validated_dataclass_settings(cls) -> ValidatedDataclassSettings:
        return cast(ValidatedDataclassSettings, cls._class_settings(base=ValidatedDataclass))

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: type[Self]) -> None:
        settings = cast(ValidatedDataclassSettings, wrapped_cls._class_settings(base=ValidatedDataclass))
        if settings.flags.validate_init:
            # validate ClassVar values and field default values at dataclass wrap time
            for fld in get_dataclass_fields(wrapped_cls, include_all=True):
                if type_is_classvar(fld.type) and hasattr(wrapped_cls, fld.name):
                    _validate_dataclass_field(wrapped_cls, fld, getattr(wrapped_cls, fld.name))
                elif (wrapped_cls._field_validation_flags(fld).validate_init) and (fld.default is not MISSING):
                    _validate_dataclass_field(wrapped_cls, fld, fld.default, is_default=True)
        # determine whether any fields should validate upon assignment
        if wrapped_cls.__dataclass_params__.frozen:  # type: ignore[attr-defined]
            validate_assign = False
        else:
            validate_assign = False
            for fld in get_dataclass_fields(wrapped_cls):
                flags = wrapped_cls._field_validation_flags(fld)
                if flags.validate_assign:
                    validate_assign = True
                    break
        if validate_assign:
            # hook __setattr__ to validate instance attributes at assignment time
            # NOTE: this will redundantly check attributes set during __post_init__ if validate_init=True as well.
            # This is somewhat difficult to avoid since there is no simple way to distinguish assignments occurring
            # during initialization.
            # NOTE: if the dataclass is frozen, `setattr` will *not* be called when initializing fields, so if
            # validation is desired, be sure to set validate_init=True.
            orig_setattr = wrapped_cls.__setattr__
            def _validated_setattr(self: object, name: str, value: Any, /) -> None:
                tp = cast(DataclassType, type(self))
                if (
                    (fld := tp.__dataclass_fields__.get(name, None))
                    and tp._field_validation_flags(fld).validate_assign  # type: ignore[attr-defined]
                ):
                    _validate_dataclass_field(tp, fld, value)
                orig_setattr(self, name, value)  # pyrefly: ignore[bad-argument-type]
            wrapped_cls.__setattr__ = _validated_setattr  # type: ignore[method-assign]

    @classmethod
    def _field_validation_flags(cls, fld: Field[Any]) -> _FieldValidationFlags:
        """Returns a _FieldValidationFlags object indicating if the value the given field should be validated for
        initialization and assignment."""
        cls_settings = cast(ValidatedDataclassSettings, cls._class_settings(base=ValidatedDataclass))
        fld_settings = cls._field_settings(fld).adapt_to(ValidatedDataclassFieldSettings)
        validate_init = _first_non_null(
            [fld_settings.flags._validate_init, cls_settings.flags._validate_init],
            default=True,
        )
        validate_assign = _first_non_null(
            [fld_settings.flags._validate_assign, cls_settings.flags._validate_assign],
            default=True,
        )
        return _FieldValidationFlags(_validate_init=validate_init, _validate_assign=validate_assign)

    def _validate_field(self, fld: Field[Any]) -> None:
        cls = type(self)
        if not hasattr(self, fld.name):
            # first check that the instance has an attribute for the field
            raise FieldTypeValidationError(cls, fld.name, fld.type, MISSING)
        _validate_dataclass_field(cls, fld, getattr(self, fld.name))

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        for fld in get_dataclass_fields(self):
            flags = self._field_validation_flags(fld)
            if flags.validate_init:
                self._validate_field(fld)
