from dataclasses import MISSING, Field, InitVar, dataclass
from typing import Any, ClassVar, Optional, cast

from typing_extensions import Self

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import (
    DataclassType,
    FieldTypeValidationError,
    get_dataclass_fields,
    type_is_classvar,
    validate_dataclass_field,
)


##########
# MIXINS #
##########

@dataclass(kw_only=True)
class ValidatedDataclassSettings(MixinSettings):
    """Class-level settings for the [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] mixin.

    Subclasses of `ValidatedDataclass` may set the following fields as keyword arguments during inheritance:

    - `validate_init`: if `True`, validate all fields upon initialization (default `True`)
    - `validate_assign`: if `True`, validate all fields upon assignment (default `False`)
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously"""

    validate_init: bool = True
    validate_assign: bool = False
    validate: InitVar[Optional[bool]]

    def __init__(  # noqa: D107
        self,
        *,
        validate_init: Optional[bool] = None,
        validate_assign: Optional[bool] = None,
        validate: Optional[bool] = None,
    ) -> None:
        if validate_init is None:
            validate_init = True if (validate is None) else validate
        if validate_assign is None:
            validate_assign = False if (validate is None) else validate
        self.validate_init = validate_init
        self.validate_assign = validate_assign


@dataclass(kw_only=True)
class ValidatedDataclassFieldSettings(FieldSettings):
    """Settings for [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `validate_init`: if set to `True` or `False`, overrides the class-level `validate_init` flag for whether to
    validate the field upon initialization
    - `validate_assign`: if set to `True` or `False`, overrides the class-level `validate_assign` flag for whether to
    validate the field upon assignment
    - `validate`: convenience flag to set both `validate_init` and `validate_assign` simultaneously
    """

    validate_init: Optional[bool] = None
    validate_assign: Optional[bool] = None
    validate: InitVar[Optional[bool]] = None

    def __post_init__(self, validate: Optional[bool]) -> None:
        if validate is not None:
            if self.validate_init is None:
                self.validate_init = validate
            if self.validate_assign is None:
                self.validate_assign = validate


@dataclass(kw_only=True)
class _FieldValidationFlags:
    """A pair of flags indicating whether a field should be validated for initialization and assignment."""

    validate_init: bool
    validate_assign: bool


class ValidatedDataclass(DataclassMixin):
    """Mixin class for dataclasses which can validate their fields upon initialization or assignment."""

    __settings_type__ = ValidatedDataclassSettings
    __settings__: ClassVar[ValidatedDataclassSettings] = ValidatedDataclassSettings()
    __field_settings_type__ = ValidatedDataclassFieldSettings

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: type[Self]) -> None:
        if wrapped_cls.__settings__.validate_init:
            # validate ClassVar values and field default values at dataclass wrap time
            for fld in get_dataclass_fields(wrapped_cls, include_all=True):
                if type_is_classvar(fld.type) and hasattr(wrapped_cls, fld.name):
                    validate_dataclass_field(wrapped_cls, fld, getattr(wrapped_cls, fld.name))
                elif (wrapped_cls._field_validation_flags(fld).validate_init) and (fld.default is not MISSING):
                    validate_dataclass_field(wrapped_cls, fld, fld.default, is_default=True)
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
            def _validated_setattr(self: object, name: str, value: Any, /) -> None:
                tp = cast(DataclassType, type(self))
                if (
                    (fld := tp.__dataclass_fields__.get(name, None))
                    and tp._field_validation_flags(fld).validate_assign  # type: ignore[attr-defined]
                ):
                    validate_dataclass_field(tp, fld, value)
                super(type(self), self).__setattr__(name, value)  # type: ignore[misc]
            wrapped_cls.__setattr__ = _validated_setattr  # type: ignore[method-assign]

    @classmethod
    def _field_validation_flags(cls, fld: Field[Any]) -> _FieldValidationFlags:
        """Returns a _FieldValidationFlags object indicating if the value the given field should be validated for
        initialization and assignment."""
        settings = cls._field_settings(fld).adapt_to(ValidatedDataclassFieldSettings)
        validate_init = cls.__settings__.validate_init if (settings.validate_init is None) else settings.validate_init
        validate_assign = (
            cls.__settings__.validate_assign if (settings.validate_assign is None) else settings.validate_assign
        )
        return _FieldValidationFlags(validate_init=validate_init, validate_assign=validate_assign)

    def _validate_field(self, fld: Field[Any]) -> None:
        cls = type(self)
        if not hasattr(self, fld.name):
            raise FieldTypeValidationError(cls, fld.name, fld.type, MISSING)
        validate_dataclass_field(cls, fld, getattr(self, fld.name))

    def __post_init__(self, **kwargs: Any) -> None:
        for fld in get_dataclass_fields(self):
            flags = self._field_validation_flags(fld)
            if flags.validate_init:
                self._validate_field(fld)
