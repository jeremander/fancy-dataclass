<!-- markdownlint-disable MD052 -->

The [`SQLDataclass`][fancy_dataclass.sql.SQLDataclass] mixin provides SQL [ORM](https://en.wikipedia.org/wiki/Object–relational_mapping) (Object-Relational Mapping) functionality to a dataclass. This uses the [SQLAlchemy](https://www.sqlalchemy.org) library under the hood.

After applying the [`register`][fancy_dataclass.sql.register] decorator to a custom dataclass, it will register a [`sqlalchemy.Table`](https://docs.sqlalchemy.org/en/20/core/metadata.html#sqlalchemy.schema.Table), after which you can use the class to perform database [CRUD](https://en.wikipedia.org/wiki/Create,_read,_update_and_delete) operations in the typical SQLAlchemy way. You can also define constraints and relationships on the tables after they are registered.

Since SQLAlchemy is backend-agnostic, you can use `SQLDataclass` with many popular SQL backends such as SQLite, MySQL, and PostgreSQL.

See the SQLAlchemy documentation on how to set up [engines](https://docs.sqlalchemy.org/en/20/core/engines.html) and [sessions](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## Usage Example

Define a `SQLDataclass` corresponding to a SQL table.

```python
from dataclasses import dataclass, field

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fancy_dataclass.sql import DEFAULT_REGISTRY, SQLDataclass, register


@register()  # register dataclass as a table
class Employee(SQLDataclass):
    first_name: str
    last_name: str
    # set _id as primary key, which will auto-increment if omitted
    _id: int = field(
        default=None,
        metadata={'column': {'primary_key':True}}
    )

# create sqlalchemy engine
engine = create_engine('sqlite:///:memory:')
# create all registered tables
DEFAULT_REGISTRY.metadata.create_all(engine)
```

Create a SQLAlchemy session and populate the table.

```python
>>> Session = sessionmaker(bind=engine)
>>> session = Session()
>>> person1 = Employee('John', 'Smith')
>>> person2 = Employee('Jane', 'Doe')
>>> session.add_all([person1, person2])
>>> session.commit()
>>> print(session.query(Employee).all())
[Employee(first_name='John', last_name='Smith', _id=1), Employee(first_name='Jane', last_name='Doe', _id=2)]
```

## Details

🚧 **Under construction** 🚧

<!-- from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create an engine
engine = create_engine('sqlite:///:memory:', echo=True)

# Create a base class for declarative class definitions
Base = declarative_base()

# Define the Employee class
class Employee(Base):
    __tablename__ = 'employees'

    employee_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50))
    department_id = Column(Integer, ForeignKey('departments.department_id'))

# Define the Department class
class Department(Base):
    __tablename__ = 'departments'

    department_id = Column(Integer, primary_key=True, autoincrement=True)
    department_name = Column(String(50))

# Create the tables
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Insert data into the tables
hr_department = Department(department_name='Human Resources')
marketing_department = Department(department_name='Marketing')
finance_department = Department(department_name='Finance')

session.add_all([hr_department, marketing_department, finance_department])
session.commit()

john_smith = Employee(name='John Smith', department_id=hr_department.department_id)
jane_doe = Employee(name='Jane Doe', department_id=marketing_department.department_id)
michael_johnson = Employee(name='Michael Johnson', department_id=finance_department.department_id)
emily_brown = Employee(name='Emily Brown', department_id=hr_department.department_id)
chris_lee = Employee(name='Chris Lee', department_id=marketing_department.department_id)

session.add_all([john_smith, jane_doe, michael_johnson, emily_brown, chris_lee])
session.commit()

# Perform a simple join and retrieve data
employees_departments_query = session.query(Employee, Department).join(Department)
for employee, department in employees_departments_query:
    print(f"{employee.name} works in {department.department_name}")

# Close the session
session.close() -->

<!-- Add relationship after the fact -->
<!-- Parent.children = relationship(Child, primaryjoin=Child.parent_id == Parent.id) -->

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
