from dataclasses import Field, dataclass, fields, is_dataclass
from typing import Any, Optional, TypeVar, get_args

from typing_extensions import Doc, Self, _AnnotatedAlias, override

from fancy_dataclass.utils import check_dataclass, coerce_to_dataclass, validate_dataclass_field


DA = TypeVar('DA', bound='DataclassAdaptable')


class DataclassAdaptable:
    """Mixin class providing the ability to convert (adapt) one dataclass type to another."""

    @classmethod
    def coerce(cls, obj: object) -> Self:
        """Constructs a `DataclassAdaptable` object from the attributes of an arbitrary object.

        Any missing attributes will be set to their default values."""
        return coerce_to_dataclass(cls, obj)

    def adapt_to(self, dest_type: type[DA]) -> DA:
        """Converts a `DataclassAdaptable` object to another type, `dest_type`.

        By default this will attempt to coerce the fields from the original type to the new type, but subclasses may
        override the behavior, e.g. to allow field renaming."""
        return dest_type.coerce(self)


class _DataclassFieldValidate:
    """Mixin class for a dataclass which, in __post_init__, performs runtime type-checking on all field values."""

    def __post_init__(self) -> None:
        assert is_dataclass(self)
        for fld in fields(self):
            validate_dataclass_field(type(self), fld, getattr(self, fld.name))


class MixinSettings(DataclassAdaptable, _DataclassFieldValidate):
    """Base class for settings to be associated with `fancy_dataclass` mixins.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__settings_type__` attribute
    consisting of a subclass of this class.
    The settings object will be instantiated as a `__settings__` attribute on a mixin subclass when it is defined."""


class FieldSettings(DataclassAdaptable, _DataclassFieldValidate):
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
        return cls(**{key: val for (key, val) in fld.metadata.items() if key in cls.__dataclass_fields__})  # type: ignore[assignment]


@dataclass(kw_only=True)
class DocFieldSettings(FieldSettings):
    """Settings to expose a "doc" attribute of a field.

    By default the "doc" field will be extracted from the field metadata, but as a fallback it will look for a
    [PEP 727](https://peps.python.org/pep-0727/) `Doc`-annotated field type.

    For example, the following are equivalent ways to specify documentation for a field:

    1. `height: float = field(metadata={'doc': 'height (in cm)'})`
    2. `height: Annotated[float, Doc('height (in cm)')]`
    """

    doc: Optional[str] = None

    @classmethod
    @override
    def from_field(cls, fld: Field[Any]) -> Self:
        settings = super().from_field(fld)
        if settings.doc is None:
            tp = None if isinstance(fld.type, str) else fld.type
            if isinstance(tp, _AnnotatedAlias):
                doc = next((arg for arg in get_args(tp)[::-1] if isinstance(arg, Doc)), None)
                if doc:
                    settings.doc = doc.documentation
        return settings
