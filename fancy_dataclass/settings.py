from dataclasses import Field, fields, is_dataclass
from typing import Any

from typing_extensions import Self

from fancy_dataclass.utils import _validate_dataclass_field, check_dataclass


class _DataclassFieldValidate:
    """Mixin class for a dataclass which, in __post_init__, performs runtime type-checking on all field values."""

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        assert is_dataclass(self)
        for fld in fields(self):
            _validate_dataclass_field(type(self), fld, getattr(self, fld.name))


class MixinSettings(_DataclassFieldValidate):
    """Base class for settings to be associated with `fancy_dataclass` mixins.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__settings_type__` attribute
    consisting of a subclass of this class.
    The settings object will be instantiated as a `__settings__` attribute on a mixin subclass when it is defined."""


class FieldSettings(_DataclassFieldValidate):
    """Class storing a bundle of parameters that will be extracted from dataclass field metadata.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__field_settings_type__` attribute
    which is a `FieldSettings` subclass.
    This specifies which keys in the `field.metadata` dictionary are recognized by the mixin class.
    Other keys will be ignored (unless they are used by other mixin classes)."""

    @classmethod
    def from_field(cls, fld: Field[Any]) -> Self:
        """Constructs a `FieldSettings` object from a
        [`dataclasses.Field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.Field)'s metadata.

        Raises:
            TypeError: If any field has the wrong type"""
        assert check_dataclass(cls)
        kwargs = {key: val for (key, val) in fld.metadata.items() if key in cls.__dataclass_fields__}
        return cls(**kwargs)  # type: ignore[return-value]
