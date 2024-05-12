from dataclasses import MISSING, dataclass, fields
from datetime import datetime
from typing import Any, Callable, ClassVar, Dict, Optional, Type, TypeVar, Union, get_args, get_origin

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, Numeric, PickleType, String, Table
import sqlalchemy.orm
from typing_extensions import TypeAlias

from fancy_dataclass.mixin import DataclassMixin, FieldSettings
from fancy_dataclass.utils import safe_dict_update


T = TypeVar('T')
Reg: TypeAlias = sqlalchemy.orm.decl_api.registry

# default sqlalchemy registry
DEFAULT_REGISTRY = sqlalchemy.orm.registry()


def get_column_type(tp: type) -> type:
    """Converts from a Python type to a corresponding sqlalchemy column type.

    Args:
        tp: A Python type

    Returns:
        Corresponding sqlalchemy column type"""
    if issubclass(tp, str):
        return String
    if issubclass(tp, bool):
        return Boolean
    if issubclass(tp, int):
        return Integer
    if issubclass(tp, float):
        return Numeric
    if issubclass(tp, bytes):
        return LargeBinary
    if issubclass(tp, datetime):
        return DateTime
    return PickleType


@dataclass
class SQLDataclassFieldSettings(FieldSettings):
    """Settings for [`SQLDataclass`][fancy_dataclass.sql.SQLDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `sql`: if `True`, include this field as a table column (default `True`)
    - `column`: dict of keyword arguments passed to the [`Column`](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Column) constructor"""
    sql: bool = True
    column: Optional[Dict[str, Any]] = None


class SQLDataclass(DataclassMixin):
    """A dataclass backed by a SQL table using the [sqlalchemy](https://www.sqlalchemy.org) ORM.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`. See [`SQLDataclassFieldSettings`][fancy_dataclass.sql.SQLDataclassFieldSettings] for the full list of settings.

    All dataclass fields will correspond to SQL columns unless their metadata is marked with `sql=False`.

    Each field may also contain a `"column"` entry in its `metadata` dict. This will provide optional keyword arguments to be passed to sqlalchemy's [`Column`](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Column) constructor.

    Some types are invalid for SQL columns; if such a type occurs, a `TypeError` will be raised."""

    __field_settings_type__ = SQLDataclassFieldSettings
    __table__: ClassVar[Table]

    @classmethod
    def get_columns(cls) -> Dict[str, Column[Any]]:
        """Gets a mapping from the class's field names to sqlalchemy `Column` objects.

        Returns:
            Dict from column names to `Column` objects"""
        cols = {}
        for fld in fields(cls):  # type: ignore[arg-type]
            settings = cls._field_settings(fld).adapt_to(SQLDataclassFieldSettings)
            nullable = False
            if not settings.sql:  # skip fields whose 'sql' setting is False
                continue
            tp = fld.type
            origin = get_origin(tp)
            if origin:  # compound type
                if origin is Union:  # use the first type of a Union (also handles Optional)
                    # column should be nullable by default if the type is optional
                    tp_args = get_args(tp)
                    nullable |= (type(None) in tp_args)
                    tp = tp_args[0]
                else:  # some other compound type
                    tp = origin
            if issubclass(tp, SQLDataclass):  # nested SQLDataclass
                cols.update(tp.get_columns())
            else:
                # TODO: making columns non-nullable seems to break things for nested SQLDataclasses
                # column_kwargs = {'nullable' : nullable}
                column_kwargs = {}
                if fld.default is not MISSING:
                    column_kwargs['default'] = fld.default
                elif fld.default_factory is not MISSING:
                    column_kwargs['default'] = fld.default_factory
                # get additional keyword arguments from 'column' section of metadata, if present
                column_kwargs.update(settings.column or {})
                cols[fld.name] = Column(fld.name, get_column_type(tp), **column_kwargs)
        return cols


def register(reg: Reg = DEFAULT_REGISTRY, extra_cols: Optional[Dict[str, Column[Any]]] = None) -> Callable[[Type[SQLDataclass]], Type[SQLDataclass]]:
    """Decorator that registers a sqlalchemy table for a [`SQLDataclass`][fancy_dataclass.sql.SQLDataclass].

    Args:
        reg: sqlalchemy registry for mapping the class to a SQL table
        extra_cols: Additional columns (beyond the dataclass fields) to be stored in the table

    Returns:
        A decorator mapping a `SQLDataclass` type to a registered sqlalchemy table"""
    def _orm_table(cls: Type[SQLDataclass]) -> Type[SQLDataclass]:
        cls = dataclass(cls)
        cols: Dict[str, Column[Any]] = {}
        safe_dict_update(cols, cls.get_columns())
        if extra_cols:
            safe_dict_update(cols, extra_cols)
        primary_key = next((name for (name, col) in cols.items() if col.primary_key), None)
        if primary_key is None:
            if '_id' in cols:
                raise ValueError(f'no primary key found for {cls.__name__!r}')
            # add an auto-incrementing primary key with '_id' column
            cols = {'_id': Column('_id', Integer, primary_key=True, autoincrement=True), **cols}
        else:  # ensure primary key is the first column
            col = cols.pop(primary_key)
            cols = {primary_key: col, **cols}
        cls.__table__ = Table(cls.__name__, reg.metadata, *cols.values())
        return reg.mapped(cls)
    return _orm_table
