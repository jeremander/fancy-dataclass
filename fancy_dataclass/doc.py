from dataclasses import Field, dataclass, replace
from typing import Any, Optional, cast

import annotated_doc
import typing_extensions
from typing_extensions import Self, override

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import get_annotated_elements


_DOC_TYPES = (typing_extensions.Doc, annotated_doc.Doc)


############
# SETTINGS #
############

@dataclass(frozen=True, kw_only=True)
class DocDataclassSettings(MixinSettings):
    """Class-level settings for the [`DocDataclass`][fancy_dataclass.doc.DocDataclass] mixin.

    Subclasses of `DictDataclass` may set the `doc` option as keyword arguments during inheritance, providing a
    class-level documentation string."""

    doc: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class DocDataclassFieldSettings(FieldSettings):
    """Settings for [`DocDataclass`][fancy_dataclass.doc.DocDataclass] fields.

    Each field may define a `metadata` dict containing an optional `"doc"` entry providing a field-level documentation
    string.

    If a `"doc"` entry is not present in the field metadata, a [PEP 727](https://peps.python.org/pep-0727/)
    `Doc`-annotated field type will be searched for. `Doc` can come from either the `typing_extensions` or
    `annotated_doc` library.

    If multiple `Doc` elements occur within an `Annotated` type, the last one is selected.

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
                        settings = replace(settings, doc=doc.documentation)
                case _:
                    pass
        return settings


##########
# MIXINS #
##########

class DocDataclass(DataclassMixin):
    """Mixin class providing methods for retrieving both class and field-level documentation strings.

    A subclass may configure settings by passing a `doc` keyword argument when inheriting from `DocDataclass`.

    Each individual field may provide a `"doc"` entry in its `metadata` dict."""

    __settings_type__ = DocDataclassSettings
    __settings__ = DocDataclassSettings()
    __field_settings_type__ = DocDataclassFieldSettings

    @classmethod
    def _doc_dataclass_settings(cls) -> DocDataclassSettings:
        return cast(DocDataclassSettings, cls._class_settings(base=DocDataclass))

    @classmethod
    def _doc_dataclass_field_settings(cls, name: str) -> DocDataclassFieldSettings:
        return cast(DocDataclassFieldSettings, cls._field_settings(name, base=DocDataclass))

    @classmethod
    def get_class_doc(cls) -> Optional[str]:
        """Gets the class-level documentation string.

        This first looks for a `doc` field in the class-level
        [`DocDataclassSettings`][fancy_dataclass.doc.DocDataclassSettings]. If a string is not present there, falls
        back on the class docstring.

        Returns:
            A class-level documentation string, if one can be found, and `None` otherwise"""
        settings = cls._doc_dataclass_settings()
        if settings.doc is not None:
            return settings.doc
        return cls.__doc__

    @classmethod
    def get_field_doc(cls, name: str) -> Optional[str]:
        """Gets the field-level documentation string for the field with the given name.

        This uses the `"doc"` entry of the field-level metadata, if present, and the last PEP 727 `Doc`-annotated entry
        otherwise.

        Args:
            name: Name of the field

        Returns:
            A documentation string for the field, if one can be found, and `None` otherwise"""
        settings = cls._doc_dataclass_field_settings(name)
        return settings.doc
