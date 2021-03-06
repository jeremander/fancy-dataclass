import dataclasses
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, Numeric, PickleType, String, Table
import sqlalchemy.orm
from typing import Any, Callable, Container, Dict, Type, TypeVar, Union
from typing_extensions import TypeAlias

from fancy_dataclass._dataclass import DictDataclass

T = TypeVar('T')
ColumnMap = Dict[str, Column]
Reg: TypeAlias = sqlalchemy.orm.decl_api.registry  # type: ignore

# default sqlalchemy registry
DEFAULT_REGISTRY = sqlalchemy.orm.registry()


def safe_update(d1: Dict[str, Any], d2: Dict[str, Any]) -> None:
    """Updates the first dict with the second.
    Raises a ValueError if any keys overlap."""
    for (key, val) in d2.items():
        if (key in d1):
            raise ValueError(f'duplicate key {key!r}')
        d1[key] = val

def get_column_type(tp: type) -> type:
    """Given a Python type, returns a corresponding sqlalchemy column type."""
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
    """A dataclass backed by a SQL table using the sqlalchemy ORM.
    All dataclass fields will correspond to SQL fields unless their metadata is marked with `sql=False`.
    Some types are invalid for SQL fields; if such a type occurs, a `TypeError` will be raised."""
    @classmethod
    def get_columns(cls) -> ColumnMap:
        cols = {}
        for field in dataclasses.fields(cls):
            if (not field.metadata.get('sql', True)):
                # skip fields whose metadata's 'sql' field is False
                continue
            tp = field.type
            origin = getattr(tp, '__origin__', None)
            if origin:  # compound type
                if (origin is Union):  # use the first type of a Union (also handles Optional)
                    tp = tp.__args__[0]
                else:  # some other compound type
                    tp = origin
            if issubclass(tp, SQLDataclass):  # nested SQLDataclass
                cols.update(tp.get_columns())
            else:
                cols[field.name] = Column(field.name, get_column_type(tp))
        return cols

def register(reg: Reg = DEFAULT_REGISTRY, extra_cols: ColumnMap = {}) -> Callable[[Type[SQLDataclass]], Type[SQLDataclass]]:  # type: ignore
    """Decorator that registers a sqlalchemy table for a SQLDataclass.
        reg: sqlalchemy registry for mapping the class to the SQL table
        extra_cols: additional columns (beyond the dataclass fields) to be stored in the table"""
    def _orm_table(cls: Type[SQLDataclass]) -> Type[SQLDataclass]:
        cols = dict(extra_cols)
        safe_update(cols, cls.get_columns())
        has_primary_key = any(fld.primary_key for fld in cols.values())
        if (not has_primary_key):
            if ('_id' in cols):
                raise ValueError(f'no primary key found for {cls.__name__!r}')
            # add an auto-incrementing primary key with '_id' column
            cols = {'_id' : Column('_id', Integer, primary_key = True, autoincrement = True), **cols}
        cls.__table__ = Table(cls.__name__, reg.metadata, *cols.values())
        return reg.mapped(dataclasses.dataclass(cls))
    return _orm_table
