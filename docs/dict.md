<!-- markdownlint-disable MD046 MD052 -->

The [`DictDataclass`][fancy_dataclass.dict.DictDataclass] mixin provides automatic conversion to and from Python dictionaries.

- [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] converts to a Python dictionary.
- [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] converts from a Python dictionary.

## Usage Example

Define a `DictDataclass`.

```python
from dataclasses import dataclass
from typing import Optional

from fancy_dataclass import DictDataclass


@dataclass
class Person(DictDataclass):
    name: str
    age: int
    height: float
    hobbies: list[str]
    awards: Optional[list[str]] = None
```

Convert to/from a Python dict.

```python
>>> person = Person(
    name='John Doe',
    age=47,
    height=71.5,
    hobbies=['reading', 'juggling', 'cycling']
)

# default values are suppressed by default
>>> person.to_dict()
{'name': 'John Doe',
 'age': 47,
 'height': 71.5,
 'hobbies': ['reading', 'juggling', 'cycling']}

# include all the values
>>> person.to_dict(full=True)
{'name': 'John Doe',
 'age': 47,
 'height': 71.5,
 'hobbies': ['reading', 'juggling', 'cycling'],
 'awards': None}

>>> new_person = Person.from_dict(person.to_dict())
>>> new_person == person
True
```

## Details

[`DictDataclass`][fancy_dataclass.dict.DictDataclass] is used to convert dataclasses to/from Python dicts via [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] and [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict].

### Class and Field Settings

You may customize the behavior of a `DictDataclass` subclass by passing keyword arguments upon inheritance (see [mixin class settings](mixin.md#class-settings)). See [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings] for the full list of settings. For field-specific settings, see [`DictDataclassFieldSettings`][fancy_dataclass.dict.DictDataclassFieldSettings].

#### Suppressing Defaults

One setting, `suppress_defaults`, is set to `True` by default. This will suppress fields in an output Python dict whose values match the class's default value. While this is often helpful to keep the output smaller, it is sometimes better to be explicit. To override this behavior, you can set `suppress_defaults=False`.

```python
@dataclass
class A(DictDataclass):
    x: int = 5

@dataclass
class B(DictDataclass, suppress_defaults=False):
    x: int = 5

print(A().to_dict())
{}

print(B().to_dict())
{'x': 5}
```

#### Suppressing Null Values

You can suppress fields with null values by supplying `suppress_none=True`:

```python
@dataclass
class C(DictDataclass, suppress_none=True):
    x: Optional[int]

print(C(1).to_dict())
{'x': 1}

print(C(None).to_dict())
{}
```

You can be more fine-grained about handling the output behavior of specific fields by setting flags in their [field settings](mixin.md#field-settings):

- Setting `suppress_default` to `False` or `True` will override the class setting at the field level.
- Setting `suppress_none` to `False` or `True` will override the class setting at the field level.
- Setting `suppress` to `False` or `True` will force inclusion or exclusion of the field, regardless of `suppress_defaults` or `suppress_none` settings.

#### Including Types in Output

Another setting of note is `store_type`. This relates to type inference when loading an object from a Python dict. Suppose you have a class like:

```python
@dataclass
class Circle(DictDataclass):
    radius: float
```

Converting a `Circle` object to a Python dict:

```python
print(Circle(3).to_dict())
{'radius': 3}
```

This may be undesirable, since the output does not make it clear what type of thing it is. To include the type in the output, you may set `store_type='name'`:

```python
@dataclass
class Circle(DictDataclass, store_type='name'):
    radius: float

print(Circle(3).to_dict())
{'type': 'Circle', 'radius': 3}
```

Sometimes it is better to store the fully qualified type name instead. You can do this by setting `store_type` to `'qualname'`:

```python
@dataclass
class Circle(DictDataclass, store_type='qualname'):
    radius: float

print(Circle(3).to_dict())
{'type': 'my_module.Circle', 'radius': 3}
```

Here, `my_module` is the name of the module in which `Circle` is defined.
