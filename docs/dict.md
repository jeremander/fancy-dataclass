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

>>> print(A().to_dict())
{}

>>> print(B().to_dict())
{'x': 5}
```

#### Suppressing Null Values

You can suppress fields with null values by supplying `suppress_none=True`:

```python
@dataclass
class A(DictDataclass, suppress_none=True):
    x: Optional[int]

>>> print(A(1).to_dict())
{'x': 1}

>>> print(A(None).to_dict())
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
>>> print(Circle(3).to_dict())
{'radius': 3}
```

This may be undesirable, since the output does not make it clear what type of thing it is. To include the type in the output, you may set `store_type='name'`:

```python
@dataclass
class Circle(DictDataclass, store_type='name'):
    radius: float

>>> print(Circle(3).to_dict())
{'type': 'Circle', 'radius': 3}
```

Sometimes it is better to store the fully qualified type name instead. You can do this by setting `store_type` to `'qualname'`:

```python
@dataclass
class Circle(DictDataclass, store_type='qualname'):
    radius: float

>>> print(Circle(3).to_dict())
{'type': 'my_module.Circle', 'radius': 3}
```

Here, `my_module` is the name of the module in which `Circle` is defined.

#### Nested `DictDataclass` fields

The default behavior when nested `DictDataclass` fields are present is to recursively convert them to dicts, preserving the nesting:

```python
@dataclass
class Inner(DictDataclass):
    x: int

@dataclass
class Outer(DictDataclass):
    inner: Inner
    y: int

>>> outer = Outer(inner=Inner(x=1), y=2)
>>> print(outer.to_dict())
{'inner': {'x': 1}, 'y': 2}
```

In some cases, you may want to "flatten" or merge together the nested fields with the outer fields. To set this behavior for all nested fields, use `flatten=True` in the outer class's settings:

```python
@dataclass
class Outer(DictDataclass, flatten=True):
    inner: Inner
    y: int

>>> outer = Outer(inner=Inner(x=1), y=2)
>>> print(outer.to_dict())
{'x': 1, 'y': 2}
```

Or to specify an individual field to flatten, use the field-level setting instead:

```python
@dataclass
class Outer(DictDataclass):
    inner: Inner = field(metadata={'flatten': True})
    y: int

>>> outer = Outer(inner=Inner(x=1), y=2)
>>> print(outer.to_dict())
{'x': 1, 'y': 2}
```

#### Field Aliases

Each field is permitted to have an *alias*, which is an alternate name for the key when it is converted to a dict. To specify an alias, use the `alias` field setting:

```python
@dataclass
class Item(DictDataclass):
    my_field: int = field(metadata={'alias': 'myField'})

>>> item = Item(my_field=123)
>>> print(item.to_dict())
{'myField': 123}
>>> item2 = Item.from_dict({'myField': 123})
>>> item2 == item
True
# NOTE: the alias is the only recognized key
>>> item3 = Item.from_dict({'my_field': 123})
MissingRequiredFieldError: 'my_field' field (alias 'myField') is required
```

At this time, `alias` only supports a single alias, and this is the only dict key that is recognized by `from_dict`. In the future it is possible that multiple aliases will be supported.

Also, an error will occur immediately upon class construction if any alias conflicts with another:

```python
@dataclass
class Item(DictDataclass):
    x: int
    y: int = field(metadata={'alias': 'x'})

TypeError: duplicate field name or alias 'x'
```

#### Extra Fields

When converting to a `DictDataclass` from a dict with `from_dict`, by default, extra fields which are not specified among the dataclass fields are *ignored*:

```python
@dataclass
class A(DictDataclass):
    a: int

>>> obj = A.from_dict({'a': 1})
>>> print(obj)
A(a=1)

>>> obj = A.from_dict({'a': 1, 'b': 2})
>>> print(obj)
A(a=1)
```

To be stricter about this and forbid such extra fields, set `allow_extra_fields=False`.

```python
@dataclass
class A(DictDataclass, allow_extra_fields=False):
    a: int

>>> obj = A.from_dict({'a': 1})
>>> print(obj)
A(a=1)

>>> obj = A.from_dict({'a': 1, 'b': 2})
ValueError: unknown dict fields for A: ['b']
```

#### Field Validation

Another thing `to_dict` does by default is *runtime validation* of each dataclass field. At present, this is very rudimentary (it can be thought of as something like an `isinstance` check of each field type, though a bit more general). As an example:

```python
@dataclass
class A(DictDataclass):
    x: int

# NOTE: validation does *not* occur during normal construction
>>> obj = A('1')
# validation also does not occur when converting *to* a dict
>>> d = obj.to_dict()
>>> print(d)
{'a': '1'}
# validation does occur when converting *from* a dict
>>> obj2 = A.from_dict(d)
TypeConversionError: could not convert '1' to type 'int'
```

To disable the runtime type-checking, set `validate=False`.

```python
@dataclass
class A(DictDataclass, validate=False):
    x: int

>>> obj = A('1')
>>> d = obj.to_dict()
# now validation will be skipped
>>> obj2 = A.from_dict(d)
>>> print(obj2)
A(x='1')
```
