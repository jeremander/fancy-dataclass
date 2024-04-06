# Basics

🤵🏻‍♂️ ***Fancy Dataclass***: A library to spiff up your dataclasses with extra features.

## Introduction

Python 3.7 introduced the wonderful `dataclasses` module which lets you write "statically typed" classes using the type hinting mechanism.

By inspecting dataclasses' type annotations, it is possible to endow them with special powers that help cut down on boilerplate code in a variety of domains. Applications include:

- *JSON conversion*: serialize dataclasses to JSON and vice versa
- *SQL persistence*: define a SQL table, and save/load objects from a database
- *CLI parsing*: parse command-line arguments and store their values in a dataclass, then use them to execute your main program logic
- *Subprocess calls*: generate command-line arguments to be passed to another program

`fancy_dataclass` borrows ideas from other excellent libraries such as [`marshmallow`](https://marshmallow.readthedocs.io/en/stable/), [`pydantic`](https://docs.pydantic.dev/latest), and [`argparse_dataclass`](https://github.com/mivade/argparse_dataclass), but it aims to be as lightweight as possible in terms of its dependencies and learning curve.

## How to install

```pip install fancy_dataclass```

Requires Python 3.8 or higher.

## Example

**Regular dataclass**

```python
@dataclass
class Person:
    name: str
    age: int
    height: float
    hobbies: list[str]
```

**Fancy dataclass**

```python
@dataclass
class Person(JSONDataclass):
    name: str
    age: int
    height: float
    hobbies: list[str]
```

Usage:

```python
>>> person = Person(
    name='John Doe',
    age=47,
    height=71.5,
    hobbies=['reading', 'juggling', 'cycling']
)

>>> print(person.to_json_string(indent=2))

{
  "name": "John Doe",
  "age": 47,
  "height": 71.5,
  "hobbies": [
    "reading",
    "juggling",
    "cycling"
  ]
}
```
