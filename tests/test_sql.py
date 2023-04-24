from dataclasses import dataclass
from datetime import datetime
import pickle
from typing import Dict

import numpy as np
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from fancy_dataclass.sql import DEFAULT_REGISTRY, register, SQLDataclass


@dataclass
class Obj:
    pass

@register()
@dataclass
class Example(SQLDataclass):
    a: int
    b: float
    c: str
    d: datetime
    e: np.ndarray
    f: Dict[str, int]
    g: Obj

@register()
@dataclass
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
    return sessionmaker(bind = sqlite_engine)()

def _test_sql_convert(obj, session):
    session.add(obj)
    session.commit()
    obj2 = session.query(type(obj)).one()
    assert (obj == obj2)
    assert set(obj.get_columns()).issubset({col.name for col in obj.__table__.columns})

def test_example(sqlite_engine, session):
    ex = Example(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    _test_sql_convert(ex, session)
    with sqlite_engine.connect() as conn:
        tup = next(iter(conn.execute(text('SELECT * FROM Example'))))
        obj = pickle.loads(tup[-1])
        assert (obj == ex.g)

def test_container(session):
    ex = Example(3, 4.7, 'abc', datetime.now(), np.ones(5), {'a' : 1, 'b' : 2}, Obj())
    container = Container(ex)
    _test_sql_convert(container, session)
