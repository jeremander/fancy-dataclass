from collections.abc import Iterable
from dataclasses import MISSING, Field, dataclass
from typing import Any, ClassVar, Optional, TypeVar, cast

from typing_extensions import override

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


####################
# HELPER FUNCTIONS #
####################

def _first_non_null(vals: Iterable[Optional[T]], *, default: T) -> T:
    """Gets the first non-None value from the given iterable, defaulting to a given value if all are None."""
    for val in vals:
        if val is not None:
            return val
    return default

def _validate_dataclass_fields(cls: type['ValidatedDataclass']) -> None:
    """Validates all dataclass fields (including ClassVars) for a ValidatedDataclass subclass."""
    for fld in get_dataclass_fields(cls, include_all=True):
        if type_is_classvar(fld.type) and hasattr(cls, fld.name):
            _validate_dataclass_field(cls, fld, getattr(cls, fld.name))
        elif (cls._field_validation_flags(fld.name).validate_init) and (fld.default is not MISSING):
            _validate_dataclass_field(cls, fld, fld.default, is_default=True)

def _hook_setattr_for_assignment_validation(cls: type[DataclassMixin]) -> None:
    """Given a DataclassMixin subclass, hooks its __setattr__ to validate instance attributes at assignment time.

    NOTE: this will redundantly check attributes set during __post_init__ if validate_init=True as well.
    This is somewhat difficult to avoid since there is no simple way to distinguish assignments occurring
    during initialization.

    NOTE: if the dataclass is frozen, `setattr` will *not* be called when initializing fields, so if
    validation is desired, be sure to set validate_init=True."""
    orig_setattr = cls.__setattr__
    def _validated_setattr(self: object, name: str, value: Any, /) -> None:
        tp = cast(DataclassType, type(self))
        if (
            (fld := tp.__dataclass_fields__.get(name, None))
            and tp._field_validation_flags(fld.name).validate_assign  # type: ignore[attr-defined]
        ):
            _validate_dataclass_field(tp, fld, value)
        orig_setattr(self, name, value)  # pyrefly: ignore[bad-argument-type]
    cls.__setattr__ = _validated_setattr  # type: ignore[method-assign]


############
# SETTINGS #
############

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


@dataclass(frozen=True, kw_only=True)
class _ValidationSettings:
    """Base class for a bundle of flags indicating whether to validate fields on initialization, assignment, or both."""

    validate_init: Optional[bool] = None
    validate_assign: Optional[bool] = None
    validate: Optional[bool] = None

    @property
    def flags(self) -> _FieldValidationFlags:
        """Gets a `FieldValidationFlags` object indicating precisely when to validate fields."""
        return _FieldValidationFlags(
            _validate_init=self.validate if (self.validate_init is None) else self.validate_init,
            _validate_assign=self.validate if (self.validate_assign is None) else self.validate_assign,
        )


@dataclass(frozen=True, kw_only=True)
class ValidatedDataclassSettings(MixinSettings, _ValidationSettings):
    """Class-level settings for the [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] mixin.

    Subclasses of `ValidatedDataclass` may set the following fields as keyword arguments during inheritance:

    - `validate_init`: if `True`, validate all fields upon initialization (default `True`)
    - `validate_assign`: if `True`, validate all fields upon assignment (default `True`)
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously"""


@dataclass(frozen=True, kw_only=True)
class ValidatedDataclassFieldSettings(FieldSettings, _ValidationSettings):
    """Settings for [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `validate_init`: if set to `True` or `False`, overrides the class-level `validate_init` flag for whether to
    validate the field upon initialization
    - `validate_assign`: if set to `True` or `False`, overrides the class-level `validate_assign` flag for whether to
    validate the field upon assignment
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously
    """


##########
# MIXINS #
##########

class ValidatedDataclass(DataclassMixin):
    """Mixin class for dataclasses which can validate their fields upon initialization or assignment."""

    __settings_type__: ClassVar[Optional[type[MixinSettings]]] = ValidatedDataclassSettings
    __settings__: ClassVar[Optional[MixinSettings]] = ValidatedDataclassSettings()
    __field_settings_type__: ClassVar[Optional[type[FieldSettings]]] = ValidatedDataclassFieldSettings

    @classmethod
    def _validated_dataclass_settings(cls) -> ValidatedDataclassSettings:
        return cast(ValidatedDataclassSettings, cls._class_settings(base=ValidatedDataclass))

    @classmethod
    def _validated_dataclass_field_settings(cls, name: str) -> ValidatedDataclassFieldSettings:
        return cast(ValidatedDataclassFieldSettings, cls._field_settings(name, base=ValidatedDataclass))

    @classmethod
    @override
    def __post_dataclass_wrap__(cls) -> None:
        super().__post_dataclass_wrap__()
        settings = cast(ValidatedDataclassSettings, cls._class_settings(base=ValidatedDataclass))
        if settings.flags.validate_init:
            # validate ClassVar values and field default values at dataclass wrap time
            _validate_dataclass_fields(cls)
        # determine whether any fields should validate upon assignment
        if cls.__dataclass_params__.frozen:  # type: ignore[attr-defined]
            validate_assign = False
        else:
            validate_assign = False
            for fld in get_dataclass_fields(cls):
                flags = cls._field_validation_flags(fld.name)
                if flags.validate_assign:
                    validate_assign = True
                    break
        if validate_assign:
            _hook_setattr_for_assignment_validation(cls)

    @classmethod
    def _field_validation_flags(cls, name: str) -> _FieldValidationFlags:
        """Returns a _FieldValidationFlags object indicating if the value of the field with the given name should be
        validated for initialization and assignment."""
        cls_settings = cls._validated_dataclass_settings()
        fld_settings = cls._validated_dataclass_field_settings(name)
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
        val = getattr(self, fld.name)
        _validate_dataclass_field(cls, fld, val)

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        for fld in get_dataclass_fields(self):
            flags = self._field_validation_flags(fld.name)
            if flags.validate_init:
                self._validate_field(fld)
