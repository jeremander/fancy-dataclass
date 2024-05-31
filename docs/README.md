[![PyPI - Version](https://img.shields.io/pypi/v/fancy-dataclass)](https://pypi.org/project/fancy-dataclass/)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/jeremander/fancy-dataclass/workflow.yml)
![Coverage Status](https://github.com/jeremander/fancy-dataclass/raw/coverage-badge/coverage-badge.svg)
[![Read the Docs](https://img.shields.io/readthedocs/fancy-dataclass)](https://fancy-dataclass.readthedocs.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/jeremander/fancy-dataclass/raw/main/docs/LICENSE.txt)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

# Basics

🤵🏻‍♂️ ***Fancy Dataclass***: A library to spiff up your dataclasses with extra features.

## Introduction

Python 3.7 introduced the `dataclasses` module which lets you write "statically typed" classes using the type hinting mechanism.

By inspecting dataclasses' type annotations, it is possible to endow them with special powers that help cut down on boilerplate code in a wide variety of domains, such as:

- *JSON/TOML conversion*: convert dataclasses to JSON/TOML files and vice versa
- *Configuration management*: store global configurations and use them anywhere in your program
- *SQL persistence*: define SQL tables, and save/load objects from a database
- *CLI parsing*: parse command-line arguments and store their values in a dataclass, then use them to execute your main program logic
- *Subprocess calls*: generate command-line arguments to be passed to another program

`fancy_dataclass` borrows ideas from other excellent libraries such as [`marshmallow`](https://marshmallow.readthedocs.io/en/stable/), [`pydantic`](https://docs.pydantic.dev/latest), and [`argparse_dataclass`](https://github.com/mivade/argparse_dataclass), while aiming to be as lightweight as possible in terms of its dependencies and learning curve.

## How to install

```pip install fancy-dataclass```

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

## Documentation

Read the official documentation [here](https://fancy-dataclass.readthedocs.io).

The documentation is made with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material) and is hosted by [Read the Docs](https://readthedocs.com).

View the Changelog [here](CHANGELOG.md).

## License

This library is distributed under the terms of the [MIT](LICENSE.txt) license.
