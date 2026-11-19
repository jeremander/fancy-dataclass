from dataclasses import Field, dataclass, replace
from typing import Any, Optional

import annotated_doc
import typing_extensions
from typing_extensions import Self, override

from fancy_dataclass.settings import FieldSettings
from fancy_dataclass.utils import get_annotated_elements


_DOC_TYPES = (typing_extensions.Doc, annotated_doc.Doc)


@dataclass(frozen=True, kw_only=True)
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
                        settings = replace(settings, doc=doc.documentation)
                case _:
                    pass
        return settings
