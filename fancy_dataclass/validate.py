from dataclasses import Field, dataclass
from typing import Any, ClassVar, Optional

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import (
    TypeLike,
    conforms_to,
    dataclass_field_type,
    fully_qualified_class_name,
    get_dataclass_fields,
)


@dataclass(kw_only=True)
class ValidatedDataclassSettings(MixinSettings):
    """Class-level settings for the [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] mixin.

    Subclasses of `ValidatedDataclass` may set the following fields as keyword arguments during inheritance:

    - `validate_init`: if `True`, validate all fields upon initialization
    - `validate_assign`: if `True`, validate all fields upon assignment"""

    validate_init: bool = True
    validate_assign: bool = False


@dataclass(kw_only=True)
class ValidatedDataclassFieldSettings(FieldSettings):
    """Settings for [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `validate_init`: if set to `True` or `False`, overrides the class-level `validate_init` flag for whether to
    validate the field upon initialization
    - `validate_assign`: if set to `True` or `False`, overrides the class-level `validate_assign` flag for whether to
    validate the field upon assignment
    """

    validate_init: Optional[bool] = None
    validate_assign: Optional[bool] = None


@dataclass(kw_only=True)
class _FieldValidationFlags:
    """A pair of flags indicating whether a field should be validated for initialization and assignment."""

    validate_init: bool
    validate_assign: bool


def _get_type_name(tp: TypeLike) -> str:
    """Renders a type-like object as a human-readable string."""
    if isinstance(tp, type):
        if tp.__module__ == 'builtins':
            return tp.__name__
        return fully_qualified_class_name(tp)
    return str(tp)


class ValidatedDataclass(DataclassMixin):
    """Mixin class for dataclasses which can validate their fields upon initialization or assignment."""

    __settings_type__ = ValidatedDataclassSettings
    __settings__: ClassVar[ValidatedDataclassSettings] = ValidatedDataclassSettings()
    __field_settings_type__ = ValidatedDataclassFieldSettings

    @classmethod
    def _field_validation_flags(cls, fld: Field[Any]) -> _FieldValidationFlags:
        """Returns a _FieldValidationFlags object indicating if the value the given field should be validated for
        initialization and assignment."""
        settings = cls._field_settings(fld).adapt_to(ValidatedDataclassFieldSettings)
        validate_init = cls.__settings__.validate_init if (settings.validate_init is None) else settings.validate_init
        validate_assign = (
            cls.__settings__.validate_assign if (settings.validate_assign is None) else settings.validate_assign
        )
        if validate_assign:
            raise NotImplementedError('validation on assignment is not yet implemented')
        # TODO: do not validate InitVar or init=False fields?
        return _FieldValidationFlags(validate_init=validate_init, validate_assign=validate_assign)

    # TODO: runtime-validate `ClassVar`s in __init_subclass__

    def _validate_field(self, fld: Field[Any]) -> None:
        cls = type(self)
        cls_name = fully_qualified_class_name(cls)
        if not hasattr(self, fld.name):
            raise TypeError(f'field {fld.name!r} is missing for {cls_name}')
        val = getattr(self, fld.name)
        fld_type = dataclass_field_type(cls, fld.name)  # type: ignore[arg-type]
        if not conforms_to(val, fld_type):
            val_type_str = _get_type_name(type(val))
            fld_type_str = _get_type_name(fld_type)
            raise TypeError(
                f'field {fld.name!r} of {cls_name}: value has type {val_type_str}, expected {fld_type_str}'
            )

    def __post_init__(self, **kwargs: Any) -> None:
        for fld in get_dataclass_fields(self):
            flags = self._field_validation_flags(fld)
            if flags.validate_init:
                self._validate_field(fld)
