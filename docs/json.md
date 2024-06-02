<!-- markdownlint-disable MD046 MD052 -->

The [`JSONDataclass`][fancy_dataclass.json.JSONDataclass] mixin provides automatic conversion to and from [JSON](https://en.wikipedia.org/wiki/JSON).

- [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] / [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] convert to and from a Python dict.
- [`to_json`][fancy_dataclass.json.JSONSerializable.to_json] / [`from_json`][fancy_dataclass.json.JSONSerializable.from_json] convert to and from a JSON file-like object.
- [`save`][fancy_dataclass.serialize.FileSerializable.save] / [`load`][fancy_dataclass.serialize.FileSerializable.load] convert to and from a JSON file-like object or path.
- [`to_json_string`][fancy_dataclass.json.JSONSerializable.to_json_string] / [`from_json_string`][fancy_dataclass.json.JSONSerializable.from_json_string] convert to and from a JSON string.

## Usage Example

Define a `JSONDataclass`.

```python
from dataclasses import dataclass
from typing import Optional

from fancy_dataclass import JSONDataclass


@dataclass
class Person(JSONDataclass):
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

Convert to/from a JSON string.

```python
>>> person = Person(
    name='John Doe',
    age=47,
    height=71.5,
    hobbies=['reading', 'juggling', 'cycling']
)

>>> json_string = person.to_json_string(indent=2)

>>> print(json_string)
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

>>> new_person = Person.from_json_string(json_string)
>>> person == new_person
True
```

## Details

`JSONDataclass` inherits from [`DictDataclass`][fancy_dataclass.dict.DictDataclass], which can be used to convert dataclasses to/from Python dicts via [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] and [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict]. You may use `DictDataclass` if you do not need to interact with JSON serialized data.

### Class and Field Settings

You may customize the behavior of a `JSONDataclass` subclass by passing keyword arguments upon inheritance (see [mixin class settings](mixin.md#class-settings)). See [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings] for the full list of settings. For field-specific settings, see [`DictDataclassFieldSettings`][fancy_dataclass.dict.DictDataclassFieldSettings].

#### Suppressing Defaults

One setting, `suppress_defaults`, is set to `True` by default. This will suppress fields in an output `dict` or JSON whose values match the class's default value. While this is often helpful to keep the output smaller in size, it is sometimes better to be explicit. To override this behavior, you can set `suppress_defaults=False`.

```python
@dataclass
class A(JSONDataclass):
    x: int = 5

@dataclass
class B(JSONDataclass, suppress_defaults=False):
    x: int = 5

print(A().to_json_string())
{}

print(B().to_json_string())
{"x": 5}
```

You can be more fine-grained about handling the output behavior of specific fields by setting flags in their [field settings](mixin.md#field-settings):

- Setting `suppress_default` to `False` or `True` will override the class setting at the field level.
- Setting `suppress` to `False` or `True` will force inclusion or exclusion of the field regardless of `suppress_defaults` setting.

#### Including Types in Output

Two other settings of note are `store_type` and `qualified_type`. These relate to type inference when loading an object from a `dict` or JSON blob. Suppose you have a class like:

```python
@dataclass
class Circle(JSONDataclass):
    radius: float
```

Converting a `Circle` object to a JSON string:

```python3
print(Circle(3).to_json_string())
{"radius": 3}
```

This may be undesirable, since the output does not make it clear what type of thing it is. To include the type in the output, you may set `store_type=True`:

```python
@dataclass
class Circle(JSONDataclass, store_type=True):
    radius: float

print(Circle(3).to_json_string())
{"type": "Circle", "radius": 3}
```

`qualified_type` is like `store_type`, except it stores the fully qualified type name instead:

```python
@dataclass
class Circle(JSONDataclass, qualified_type=True):
    radius: float

print(Circle(3).to_json_string())
{"type": "my_module.Circle", "radius": 3}
```

(Here, `my_module` is the name of the module in which `Circle` is defined.)

Setting `qualified_type=True` is particularly useful when dealing with inheritance hierarchies. For example, if you try:

```python

@dataclass
class Shape(JSONDataclass):
    ...

@dataclass
class Circle(Shape):
    radius: float
```

This will raise the following error: `TypeError: when subclassing a JSONDataclass, you must set qualified_type=True or subclass JSONBaseDataclass instead`. This is saying that when you subclass `JSONDataclass`, you _must_ explicitly ensure the types are included in the output, or else it will result in type ambiguity when converting back from JSON. An alternative to `qualified_type=True` is subclassing `JSONBaseDataclass` instead of `JSONDataclass`.

Let's see why this is useful:

```python
@dataclass
class Shape(JSONBaseDataclass):
    ...

@dataclass
class Circle(Shape):
    radius: float

@dataclass
class Rectangle(Shape):
    length: float
    width: float
```

Now you can use the base class, `Shape`, to convert from different subtypes:

```python
shape_dicts = [{"type": "Circle", "radius": 3}, {"type": "Rectangle", "length": 3, "width": 5}]
shapes = [Shape.from_dict(d) for d in shape_dicts]

print(shapes)
[Circle(radius=3.0), Rectangle(length=3.0, width=5.0)]
```

### Additional Customization

To customize the JSON output format, you may pass keyword arguments to `to_json` or `to_json_string`; these will get passed along to `json.dump`. For example, `ensure_ascii=False` will allow non-ASCII output, and `indent=4` will indent the JSON with 4 spaces.

!!! note

    `JSONDataclass` is configured to use the default JSON settings provided by Python's standard [`json`](https://docs.python.org/3/library/json.html) library. This allows out-of-range float values like `nan` and `inf` to be represented as `NaN` and `Infinity`, which are not strictly part of the JSON standard. To disallow these values, you can pass `allow_nan=False` when calling `to_json` or `to_json_string`, which will raise a `ValueError` if such values occur.

To customize JSON encoding itself, a subclass of `JSONDataclass` may override the [`json_encoder`][fancy_dataclass.json.JSONSerializable.json_encoder] method. This should return a [`json.JSONEncoder`](https://docs.python.org/3/library/json.html#json.JSONEncoder) subclass.

You can also customize how JSON keys are decoded. For example, you may want to translate an integer key in a JSON file like `"1"` to the integer `1`. To accomplish this, override the [`json_key_decoder`][fancy_dataclass.json.JSONSerializable.json_key_decoder] method.

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
