from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import pickle
from typing import Any
import warnings

import numpy as np
import pytest
from sqlalchemy import JSON, Column, DateTime, Engine, Integer, Numeric, PickleType, String, create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from fancy_dataclass.sql import DEFAULT_REGISTRY, SQLDataclass, register


@dataclass
class Obj:
    pass

@dataclass
class _Example(SQLDataclass):
    a: int
    b: float
    c: str
    d: datetime
    e: np.ndarray
    f: dict[str, int]
    g: Obj

@register()
class Example(_Example):
    ...

@register(extra_cols={'h': Column('h', Integer, primary_key=True), 'i': Column('i', String())})
class ExampleWithExtra(_Example):
    ...

@register()
class MetaFields(SQLDataclass):
    a: int = field(metadata={'sql_type': Integer})
    b: str = field(metadata={'sql_type': String})
    c: dict[str, Any] = field(metadata={'sql_type': JSON})

@register()  # NOTE: register wraps the class into a dataclass
class Container(SQLDataclass):
    example: Example
    tag: str = 'tag'


@pytest.fixture
def sqlite_engine(tmpdir: Path) -> Iterator[Engine]:
    path = f'sqlite:///{tmpdir}/test.sqlite'
    engine = create_engine(path)
    yield engine
    engine.dispose()  # explicitly close pooled connections

@pytest.fixture
def session(sqlite_engine: Engine) -> Iterator[Session]:
    DEFAULT_REGISTRY.metadata.create_all(sqlite_engine)
    SessionLocal = sessionmaker(bind=sqlite_engine)
    sess = SessionLocal()
    try:
        yield sess
    finally:
        sess.close()

example_cols = [
    ('_id', Integer),
    ('a', Integer),
    ('b', Numeric),
    ('c', String),
    ('d', DateTime),
    ('e', PickleType),
    ('f', PickleType),
    ('g', PickleType)
]

@pytest.mark.parametrize(['cls', 'columns'], [
    (Example, example_cols),
    (ExampleWithExtra, [('h', Integer)] + example_cols[1:] + [('i', String)]),
    (Container, example_cols + [('tag', String)]),
    (MetaFields, [('_id', Integer), ('a', Integer), ('b', String), ('c', JSON)]),
])
def test_schema(cls: type, columns: list[tuple[str, type]]) -> None:
    """Tests the column types of various SQLDataclasses."""
    actual_columns = [(col.name, col.type) for col in cls.__table__.columns]
    assert len(actual_columns) == len(columns)
    for ((name1, tp1), (name2, tp2)) in zip(actual_columns, columns):
        assert name1 == name2
        assert isinstance(tp1, tp2)

def _test_sql_convert(obj: Any, session: Session) -> None:
    session.add(obj)
    session.commit()
    with warnings.catch_warnings():
        # sqlalchemy may warn about floating-point error; just ignore this
        warnings.simplefilter('ignore')
        obj2 = session.query(type(obj)).one()
    assert obj == obj2
    assert set(obj.get_columns()).issubset({col.name for col in obj.__table__.columns})

def test_example(sqlite_engine: Engine, session: Session) -> None:
    """Tests a SQLDataclass with various fields."""
    ex = Example(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    _test_sql_convert(ex, session)
    with sqlite_engine.connect() as conn:
        tup = next(iter(conn.execute(text('SELECT * FROM Example'))))
        assert len(tup) == 8
        assert tup[0] == 1
        assert tup[1:4] == (3, 4.7, 'abc')
        obj = pickle.loads(tup[-1])
        assert obj == ex.g
        with pytest.raises(StopIteration):  # nonexistent table
            _ = next(iter(conn.execute(text('SELECT * FROM ExampleWithExtra'))))

def test_example_with_extra(sqlite_engine: Engine, session: Session) -> None:
    """Tests a SQLDataclass with extra columns defined in the `register` decorator."""
    ex = ExampleWithExtra(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    _test_sql_convert(ex, session)
    with sqlite_engine.connect() as conn:
        tup = next(iter(conn.execute(text('SELECT * FROM ExampleWithExtra'))))
        assert len(tup) == 9
        assert tup[0] == 1
        assert tup[1:4] == (3, 4.7, 'abc')
        assert tup[-1] is None

def test_container(session: Session) -> None:
    """Tests a container SQLDataclass which wraps another."""
    ex = Example(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    container = Container(ex)
    _test_sql_convert(container, session)

def test_meta_fields(sqlite_engine: Engine, session: Session) -> None:
    """Tests a SQLDataclass with SQL types specified in the field metadata."""
    obj = MetaFields(1, 'a', {'key': [0, 'val', {}]})
    _test_sql_convert(obj, session)
    with sqlite_engine.connect() as conn:
        rows = list(conn.execute(text('SELECT * FROM MetaFields')))
    assert rows == [(1, 1, 'a', '{"key": [0, "val", {}]}')]
    objs = session.execute(select(MetaFields)).scalars().all()
    assert objs == [obj]
