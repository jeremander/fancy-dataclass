from dataclasses import Field, dataclass, fields, is_dataclass
from typing import Any, Optional

import annotated_doc
import typing_extensions
from typing_extensions import Self, override

from fancy_dataclass.utils import (
    _validate_dataclass_field,
    check_dataclass,
    get_annotated_elements,
)


_DOC_TYPES = (typing_extensions.Doc, annotated_doc.Doc)


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
        return cls(**{key: val for (key, val) in fld.metadata.items() if key in cls.__dataclass_fields__})  # type: ignore[return-value]


@dataclass(kw_only=True)
class DocFieldSettings(FieldSettings):
    """Settings to expose a "doc" attribute of a field.

    By default the "doc" field will be extracted from the field metadata, but as a fallback it will look for a
    [PEP 727](https://peps.python.org/pep-0727/) `Doc`-annotated field type. `Doc` can come from either the
    `typing_extensions` or `annotated_doc` library.

    If multiple `Doc` elements occur within an `Annotated` type, chooses the last one.

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
            match get_annotated_elements(tp):
                case (_, elements):
                    if (doc := next((arg for arg in elements[::-1] if isinstance(arg, _DOC_TYPES)), None)):
                        settings.doc = doc.documentation
                case _:
                    pass
        return settings
