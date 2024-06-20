from dataclasses import Field
from io import IOBase
from typing import IO, Any

import tomlkit as tk
from typing_extensions import Self

from fancy_dataclass.dict import AnyDict, DictDataclassFieldSettings
from fancy_dataclass.serialize import DictFileSerializableDataclass, TextFileSerializable, from_dict_value_basic, to_dict_value_basic
from fancy_dataclass.utils import AnyIO


class NoneProxy(tk.items.Item):
    """Sentinel class taking the place of None when constructing tomlkit documents.
    These will be removed before serialization."""

    def __init__(self) -> None:  # noqa: D107
        super().__init__(tk.items.Trivia())

    def __eq__(self, other: Any) -> bool:
        return other is None


class TOMLSerializable(TextFileSerializable):
    """Mixin class enabling conversion of an object to/from TOML."""

    def to_toml(self, fp: IOBase, **kwargs: Any) -> None:
        """Writes the object as TOML to a file-like object (text or binary).
        If binary, applies UTF-8 encoding.

        Args:
            fp: A writable file-like object
            kwargs: Keyword arguments"""
        return TOMLDataclass._to_file(self, fp, **kwargs)  # type: ignore[arg-type]

    def to_toml_string(self, **kwargs: Any) -> str:
        """Converts the object into a TOML string.

        Args:
            kwargs: Keyword arguments

        Returns:
            Object rendered as a TOML string"""
        return TOMLDataclass._to_string(self, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_toml(cls, fp: AnyIO, **kwargs: Any) -> Self:
        """Constructs an object from a TOML file-like object (text or binary).

        Args:
            fp: A readable file-like object
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_file(fp, **kwargs)

    @classmethod
    def from_toml_string(cls, s: str, **kwargs: Any) -> Self:
        """Constructs an object from a TOML string.

        Args:
            s: TOML string
            kwargs: Keyword arguments

        Returns:
            Converted object of this class"""
        return cls._from_string(s, **kwargs)


class TOMLDataclass(DictFileSerializableDataclass, TOMLSerializable, suppress_defaults=False, store_type='off'):  # type: ignore[misc]
    """Dataclass mixin enabling default serialization of dataclass objects to and from TOML."""

    @classmethod
    def _dict_to_text_file(cls, d: AnyDict, fp: IO[str], **kwargs: Any) -> None:
        def _get_body(obj: Any) -> Any:
            return obj.body if hasattr(obj, 'body') else obj.value.body
        def _fix_element(obj: Any) -> Any:
            if isinstance(obj, dict):
                tbl = tk.document() if isinstance(obj, tk.toml_document.TOMLDocument) else tk.table()
                container = _get_body(obj)
                for (i, (key, val)) in enumerate(container):
                    if not isinstance(val, NoneProxy):  # suppress None
                        tbl.add(key, _fix_element(val))  # type: ignore[attr-defined]
                        if (i > 0) and isinstance(val, dict) and isinstance(container[i - 1][1], tk.items.Comment):
                            # move newline above comment preceding a table
                            body = _get_body(tbl)
                            comment = body[-2][1]
                            val = body[-1][1]
                            comment.trivia.indent = val.trivia.indent
                            val.trivia.indent = ''
                return tbl
            if isinstance(obj, (tuple, list)):
                return [_fix_element(elt) for elt in obj]
            return obj
        d = _fix_element(d)
        tk.dump(d, fp, **kwargs)

    @classmethod
    def _text_file_to_dict(cls, fp: IO[str], **kwargs: Any) -> AnyDict:
        return tk.load(fp)

    @classmethod
    def _to_dict_value_basic(cls, val: Any) -> Any:
        return to_dict_value_basic(val)

    def _to_dict(self, full: bool) -> AnyDict:
        d = super()._to_dict(full)
        def _is_nested(val: Any) -> bool:
            return isinstance(val, (dict, list, tuple))
        d = dict(sorted(d.items(), key=lambda pair: _is_nested(pair[1])))
        doc = tk.document()
        # TODO: top-level string (from class settings)
        for (key, val) in d.items():
            if (fld := self.__dataclass_fields__.get(key)):  # type: ignore[attr-defined]
            # if (val is not None) and (fld := self.__dataclass_fields__.get(key)):  # type: ignore[attr-defined]
                # TODO: handle None values (comment with empty RHS)
                settings = self._field_settings(fld).adapt_to(DictDataclassFieldSettings)
                if settings.doc is not None:
                    comment = tk.comment(str(settings.doc))
                    doc.add(comment)
                val = NoneProxy() if (val is None) else val
                # val_is_none = val is None
                # val = '' if val_is_none else val
                doc.add(key, val)
                # doc.append(key, val)
                # elt = doc.body[-1][1]
                # if has_doc and isinstance(tbl := doc.body[-1][1], dict):
                #     comment.trivia.indent = tbl.trivia.indent
                #     tbl.trivia.indent = ''
                # if val_is_none:
                #     elt._is_none = True  # type: ignore[attr-defined]
        return doc

    @classmethod
    def _from_dict_value(cls, tp: type, val: Any, strict: bool = False) -> Any:
        if isinstance(val, NoneProxy):
            return None
        return super()._from_dict_value(tp, val, strict=strict)

    @classmethod
    def _from_dict_value_basic(cls, tp: type, val: Any) -> Any:
        return super()._from_dict_value_basic(tp, from_dict_value_basic(tp, val))

    @classmethod
    def _get_missing_value(cls, fld: Field) -> Any:  # type: ignore[type-arg]
        # replace any missing required fields with a default of None
        return None
