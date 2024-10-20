from dataclasses import Field, fields
from typing import Optional, Type, TypeVar, cast

from typing_extensions import Doc, Self, _AnnotatedAlias

from fancy_dataclass.utils import _is_instance, check_dataclass, coerce_to_dataclass, dataclass_kw_only, eval_type_str


DA = TypeVar('DA', bound='DataclassAdaptable')


class DataclassAdaptable:
    """Mixin class providing the ability to convert (adapt) one dataclass type to another."""

    @classmethod
    def coerce(cls, obj: object) -> Self:
        """Constructs a `DataclassAdaptable` object from the attributes of an arbitrary object.

        Any missing attributes will be set to their default values."""
        return coerce_to_dataclass(cls, obj)

    def adapt_to(self, dest_type: Type[DA]) -> DA:
        """Converts a `DataclassAdaptable` object to another type, `dest_type`.

        By default this will attempt to coerce the fields from the original type to the new type, but subclasses may override the behavior, e.g. to allow field renaming."""
        return dest_type.coerce(self)


class MixinSettings(DataclassAdaptable):
    """Base class for settings to be associated with `fancy_dataclass` mixins.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__settings_type__` attribute consisting of a subclass of this class. The settings object will be instantiated as a `__settings__` attribute on a mixin subclass when it is defined."""


class FieldSettings(DataclassAdaptable):
    """Class storing a bundle of parameters that will be extracted from dataclass field metadata.

    Each [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin] class may store a `__field_settings_type__` attribute which is a `FieldSettings` subclass. This specifies which keys in the `field.metadata` dictionary are recognized by the mixin class. Other keys will be ignored (unless they are used by other mixin classes)."""

    def type_check(self) -> None:
        """Checks that every field on the `FieldSettings` object is the proper type.

        Raises:
            TypeError: If a field is the wrong type"""
        for fld in fields(self):  # type: ignore[arg-type]
            val = getattr(self, fld.name)
            # semi-robust type checking (could still be improved)
            if not _is_instance(val, cast(type, fld.type)):
                raise TypeError(f'expected type {fld.type} for field {fld.name!r}, got {type(val)}')

    @classmethod
    def from_field(cls, field: Field) -> Self:  # type: ignore[type-arg]
        """Constructs a `FieldSettings` object from a [`dataclasses.Field`](https://docs.python.org/3/library/dataclasses.html#dataclasses.Field)'s metadata.

        Raises:
            TypeError: If any field has the wrong type"""
        assert check_dataclass(cls)
        obj: Self = cls(**{key: val for (key, val) in field.metadata.items() if key in cls.__dataclass_fields__})  # type: ignore[assignment]
        obj.type_check()
        return obj


@dataclass_kw_only()
class DocFieldSettings(FieldSettings):
    """Settings to expose a "doc" attribute of a field.

    By default the "doc" field will be extracted from the field metadata, but as a fallback it will look for a [PEP 727](https://peps.python.org/pep-0727/) `Doc`-annotated field type.

    For example, the following are equivalent ways to specify documentation for a field:

    1. `height: float = field(metadata={'doc': 'height (in cm)'})`
    2. `height: Annotated[float, Doc('height (in cm)')]`
    """
    doc: Optional[str] = None

    @classmethod
    def from_field(cls, field: Field) -> Self:  # type: ignore[type-arg]  # noqa: D102
        settings = super().from_field(field)
        if settings.doc is None:
            if isinstance(field.type, str):
                try:
                    tp = eval_type_str(field.type)
                except NameError:
                    tp = None
            else:
                tp = field.type
            if isinstance(tp, _AnnotatedAlias):
                doc = next((arg for arg in tp.__metadata__[::-1] if isinstance(arg, Doc)), None)
                if doc:
                    settings.doc = doc.documentation
        return settings
