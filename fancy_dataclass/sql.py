from dataclasses import MISSING, dataclass, fields
from datetime import datetime
from typing import Any, Callable, ClassVar, Dict, Optional, Type, TypeVar, Union

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, Numeric, PickleType, String, Table
import sqlalchemy.orm
from typing_extensions import TypeAlias

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.utils import safe_dict_update


T = TypeVar('T')
Reg: TypeAlias = sqlalchemy.orm.decl_api.registry  # type: ignore

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
    elif issubclass(tp, bool):
        return Boolean
    elif issubclass(tp, int):
        return Integer
    elif issubclass(tp, float):
        return Numeric
    elif issubclass(tp, bytes):
        return LargeBinary
    elif issubclass(tp, datetime):
        return DateTime
    else:
        return PickleType


class SQLDataclass(DictDataclass):
    """A dataclass backed by a SQL table using the [sqlalchemy](https://www.sqlalchemy.org) ORM.

    All dataclass fields will correspond to SQL fields unless their metadata is marked with `sql=False`.

    A dataclass field may contain a `"column"` entry in its `metadata` dict. This will provide optional keyword arguments to be passed to sqlalchemy's `Column` constructor.

    Some types are invalid for SQL fields; if such a type occurs, a `TypeError` will be raised."""

    __table__: ClassVar[Table]

    @classmethod
    def get_columns(cls) -> Dict[str, Column[Any]]:
        """Gets a mapping from the class's column names to sqlalchemy `Column` objects.

        Returns:
            Dict from column names to `Column` objects"""
        cols = {}
        for field in fields(cls):  # type: ignore[arg-type]
            nullable = False
            if (not field.metadata.get('sql', True)):
                # skip fields whose metadata's 'sql' field is False
                continue
            tp = field.type
            origin = getattr(tp, '__origin__', None)
            if origin:  # compound type
                if (origin is Union):  # use the first type of a Union (also handles Optional)
                    # column should be nullable by default if the type is optional
                    nullable |= (type(None) in tp.__args__)
                    tp = tp.__args__[0]
                else:  # some other compound type
                    tp = origin
            if issubclass(tp, SQLDataclass):  # nested SQLDataclass
                cols.update(tp.get_columns())
            else:
                # TODO: making columns non-nullable seems to break things for nested SQLDataclasses
                # column_kwargs = {'nullable' : nullable}
                column_kwargs = {}
                if (field.default is not MISSING):
                    column_kwargs['default'] = field.default
                elif (field.default_factory is not MISSING):  # type: ignore
                    column_kwargs['default'] = field.default_factory  # type: ignore
                # get additional keyword arguments from 'column' section of metadata, if present
                column_kwargs.update(field.metadata.get('column', {}))
                cols[field.name] = Column(field.name, get_column_type(tp), **column_kwargs)
        return cols


def register(reg: Reg = DEFAULT_REGISTRY, extra_cols: Optional[Dict[str, Column[Any]]] = None) -> Callable[[Type[SQLDataclass]], Type[SQLDataclass]]:
    """Decorator that registers a sqlalchemy table for a [`SQLDataclass`][fancy_dataclass.sql.SQLDataclass].

    Args:
        reg: sqlalchemy registry for mapping the class to a SQL table
        extra_cols: Additional columns (beyond the dataclass fields) to be stored in the table

    Returns:
        A new `dataclass` type mapped to a registered sqlalchemy table"""
    def _orm_table(cls: Type[SQLDataclass]) -> Type[SQLDataclass]:
        cls = dataclass(cls)
        cols = {} if (extra_cols is None) else dict(extra_cols)
        safe_dict_update(cols, cls.get_columns())
        has_primary_key = any(fld.primary_key for fld in cols.values())
        if (not has_primary_key):
            if ('_id' in cols):
                raise ValueError(f'no primary key found for {cls.__name__!r}')
            # add an auto-incrementing primary key with '_id' column
            cols = {'_id' : Column('_id', Integer, primary_key = True, autoincrement = True), **cols}
        cls.__table__ = Table(cls.__name__, reg.metadata, *cols.values())
        return reg.mapped(cls)
    return _orm_table
