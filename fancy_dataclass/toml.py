from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import Field, dataclass
from io import IOBase, StringIO, TextIOBase, TextIOWrapper
from typing import IO, Any, Optional

import tomlkit as tk
import tomlkit.items
import tomlkit.toml_document
from typing_extensions import Self, override

from fancy_dataclass.dict import AnyDict, DictDataclassFieldSettings, DictDataclassSettings
from fancy_dataclass.serialize import (
    DictFileSerializableDataclass,
    TextFileSerializable,
    from_dict_value_basic,
    to_dict_value_basic,
)
from fancy_dataclass.settings import MixinSettings
from fancy_dataclass.utils import AnyIO, dataclass_field_type, issubclass_safe


####################
# HELPER FUNCTIONS #
####################

def _dict_to_toml_table(obj: AnyDict) -> tomlkit.items.Table:
    # to preserve comments, must convert value from TOMLDocument to Table
    tbl = tk.table()
    pair_iter = obj.body if isinstance(obj, tk.TOMLDocument) else obj.items()
    for pair in pair_iter:
        tbl.add(*pair)  # pyrefly: ignore[no-matching-overload]
    return tbl

def _none_value_to_comment(key: str) -> tomlkit.items.Comment:
    return tk.comment(f'{key} = ')

def _make_toml_element(obj: Any) -> Any:
    if isinstance(obj, dict):
        tbl  = tk.table()
        for (key, val) in obj.items():
            if val is None:
                tbl.add(_none_value_to_comment(key))
                continue
            tbl.add(key, _make_toml_element(val))
        return tbl
    if isinstance(obj, (tuple, list)):
        return [_make_toml_element(elt) for elt in obj]
    return obj

def _add_comments_to_doc(comments: Iterable[tomlkit.items.Comment], doc: tk.TOMLDocument) -> None:
    for comment in comments:
        doc.add(comment)


##########
# MIXINS #
##########

@dataclass(kw_only=True)
class TOMLDataclassSettings(DictDataclassSettings):
    """Class-level settings for the [`TOMLDataclass`][fancy_dataclass.toml.TOMLDataclass] mixin.

    In addition to the settings inherited from [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings],
    the following options may be set:

    - `comment`: string that will be displayed as a top-level comment in the serialized TOML
    - `doc_as_comment`: if `True`, use the class's docstring as a top-level comment (this is overridden if `comment`
    is set)"""

    comment: Optional[str] = None
    doc_as_comment: bool = False

    @override
    def __post_init__(self) -> None:
        super().__post_init__()
        # can use comment or doc_as_comment to specify top-level comment, but not both
        if (self.comment is not None) and self.doc_as_comment:
            raise ValueError('can set comment to a string or doc_as_comment=True, but not both')


class TOMLSerializable(TextFileSerializable):
    """Mixin class enabling conversion of an object to/from TOML."""

    @abstractmethod
    def to_toml(self, fp: IOBase, **kwargs: Any) -> None:
        """Writes the object as TOML to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""

    def to_toml_string(self, **kwargs: Any) -> str:
        """Converts the object into a TOML string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a TOML string"""
        with StringIO() as stream:
            self.to_toml(stream, **kwargs)
            return stream.getvalue()

    @classmethod
    @abstractmethod
    def from_toml(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Constructs an object from a TOML file-like object (text or binary).

        Args:
            fp: A readable file-like object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""

    @classmethod
    def from_toml_string(cls, s: str, **kwargs: Any) -> Self:
        """Constructs an object from a TOML string.

        Args:
            s: TOML string
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        with StringIO(s) as sio:
            return cls.from_toml(sio, **kwargs)


class TOMLDataclass(DictFileSerializableDataclass, TOMLSerializable, suppress_defaults=False, store_type='off'):
    """Dataclass mixin enabling default serialization of dataclass objects to and from TOML."""

    __settings_type__ = TOMLDataclassSettings

    @classmethod
    def _dict_to_document(cls, d: AnyDict) -> tk.TOMLDocument:
        def _is_nested(val: Any) -> bool:
            return isinstance(val, (dict, list, tuple))
        # sort so that nested sections come last
        d = dict(sorted(d.items(), key=lambda pair: _is_nested(pair[1])))
        doc = tk.document()
        if (comments := cls._top_level_comments()) is not None:
            for comment in comments:
                doc.add(tk.comment(comment) if comment.strip() else tk.nl())
            doc.add(tk.nl())
        for (key, val) in d.items():
            if not (fld := cls.__dataclass_fields__.get(key)):  # type: ignore[attr-defined]
                continue
            settings = cls._field_settings(fld).adapt_to(DictDataclassFieldSettings)
            comment_elts = [tk.comment(line) for line in (settings.doc.splitlines() if settings.doc else [])]
            if val is None:
                _add_comments_to_doc(comment_elts, doc)
                doc.add(_none_value_to_comment(key))
                continue
            tp = dataclass_field_type(cls, key)  # type: ignore[arg-type]
            if issubclass_safe(tp, TOMLDataclass):
                val = _dict_to_toml_table(tp._dict_to_document(val))  # type: ignore[attr-defined]
            else:
                val = _make_toml_element(val)
            if isinstance(val, tomlkit.items.Table) and val and comment_elts:
                if doc:
                    # move newline above comment preceding a table
                    comment_elts[0].trivia.comment = '\n' + comment_elts[0].trivia.comment
                num_subdicts = sum(isinstance(subval, dict) for subval in val.values())
                if num_subdicts <= 1:
                    # remove blank line between comment and one-section table
                    comment_elts[-1].trivia.trail = ''
            _add_comments_to_doc(comment_elts, doc)
            doc.add(key, val)
        return doc

    @classmethod
    def _dict_to_toml_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        return tk.dump(cls._dict_to_document(d), fp, **kwargs)

    @classmethod
    @override
    def _dict_to_text_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        return cls._dict_to_toml_file(d, fp, **kwargs)

    @classmethod
    @override
    def _text_file_to_dict(cls, fp: IO[str], **kwargs: Any) -> AnyDict:
        return tk.load(fp)

    @classmethod
    @override
    def _to_dict_value_basic(cls, val: Any) -> Any:
        return to_dict_value_basic(val)

    @classmethod
    def _top_level_comments(cls) -> Optional[list[str]]:
        """Returns a list of top-level comments to place before all of the fields in the TOML output."""
        assert isinstance(cls.__settings__, MixinSettings)
        settings = cls.__settings__.adapt_to(TOMLDataclassSettings)
        comment = None
        if settings.comment is not None:
            comment = settings.comment
        elif settings.doc_as_comment:
            comment = cls.__doc__
        if comment is None:
            return None
        # each line must be its own comment
        return comment.splitlines()

    @classmethod
    @override
    def _from_dict_value_basic(cls, tp: type, val: Any, validate: bool) -> Any:
        return super()._from_dict_value_basic(tp, from_dict_value_basic(tp, val), validate)

    @classmethod
    @override
    def _get_missing_value(cls, fld: Field[Any]) -> Any:
        # replace any missing required fields with a default of None
        return None

    @override
    def to_toml(self, fp: IOBase, **kwargs: Any) -> None:
        if not isinstance(fp, TextIOBase):
            fp = TextIOWrapper(fp, encoding='utf-8')  # type: ignore[type-var]
        return type(self)._dict_to_toml_file(self.to_dict(), fp, **kwargs)  # type: ignore[arg-type]

    @classmethod
    @override
    def from_toml(cls, fp: AnyIO, **kwargs: Any) -> Self:
        if not isinstance(fp, TextIOBase):
            fp = TextIOWrapper(fp, encoding='utf-8')  # type: ignore[type-var]
        return cls._from_text_file(fp, **kwargs)
