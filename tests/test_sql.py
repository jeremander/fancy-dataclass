from dataclasses import dataclass
from datetime import datetime
import pickle
from typing import Dict
import warnings

import numpy as np
import pytest
from sqlalchemy import Column, DateTime, Integer, Numeric, PickleType, String, create_engine, text
from sqlalchemy.orm import sessionmaker

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
    f: Dict[str, int]
    g: Obj

@register()
class Example(_Example):
    ...

@register(extra_cols={'h': Column('h', Integer, primary_key=True), 'i': Column('i', String())})
class ExampleWithExtra(_Example):
    ...

@register()  # NOTE: register wraps the class into a dataclass
class Container(SQLDataclass):
    example: Example
    tag: str = 'tag'


@pytest.fixture
def sqlite_engine(tmpdir):
    path = f'sqlite:///{tmpdir}/test.sqlite'
    return create_engine(path)

@pytest.fixture
def session(sqlite_engine):
    DEFAULT_REGISTRY.metadata.create_all(sqlite_engine)
    return sessionmaker(bind=sqlite_engine)()

example_cols = [('_id', Integer), ('a', Integer), ('b', Numeric), ('c', String), ('d', DateTime), ('e', PickleType), ('f', PickleType), ('g', PickleType)]

@pytest.mark.parametrize(['cls', 'columns'], [
    (Example, example_cols),
    (ExampleWithExtra, [('h', Integer)] + example_cols[1:] + [('i', String)]),
    (Container, example_cols + [('tag', String)]),
])
def test_schema(cls, columns):
    actual_columns = [(col.name, col.type) for col in cls.__table__.columns]
    assert len(actual_columns) == len(columns)
    for ((name1, tp1), (name2, tp2)) in zip(actual_columns, columns):
        assert name1 == name2
        assert isinstance(tp1, tp2)

def _test_sql_convert(obj, session):
    session.add(obj)
    session.commit()
    with warnings.catch_warnings():
        # sqlalchemy may warn about floating-point error; just ignore this
        warnings.simplefilter('ignore')
        obj2 = session.query(type(obj)).one()
    assert obj == obj2
    assert set(obj.get_columns()).issubset({col.name for col in obj.__table__.columns})

def test_example(sqlite_engine, session):
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

def test_example_with_extra(sqlite_engine, session):
    ex = ExampleWithExtra(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    _test_sql_convert(ex, session)
    with sqlite_engine.connect() as conn:
        tup = next(iter(conn.execute(text('SELECT * FROM ExampleWithExtra'))))
        assert len(tup) == 9
        assert tup[0] == 1
        assert tup[1:4] == (3, 4.7, 'abc')
        assert tup[-1] is None

def test_container(session):
    ex = Example(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    container = Container(ex)
    _test_sql_convert(container, session)
