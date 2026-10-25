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

`JSONDataclass` inherits from [`DictDataclass`][fancy_dataclass.dict.DictDataclass], which can be used to convert dataclasses to/from Python dicts via [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] and [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict]. You may use `DictDataclass` directly if you do not need to interact with JSON serialized data.

For details on configuring `JSONDataclass`, see the [dict conversion](dict.md) page.

### Type Labels and Inheritance

When dealing with inheritance hierarchies of `JSONDataclass` objects, it is important to [store the type name](dict.md#including-types-in-output) in the JSON output. For example, if you try:

```python

@dataclass
class Shape(JSONDataclass):
    ...

@dataclass
class Circle(Shape):
    radius: float
```

This will raise the following error: `TypeError: when subclassing a JSONDataclass, you must set store_type to a value other than 'auto', or subclass JSONBaseDataclass instead`. This is saying that when you subclass `JSONDataclass`, you _must_ explicitly override `store_type` (preferably with `'qualname'`, to prevent type ambiguity when converting back from JSON). An alternative to setting `store_type` is subclassing [`JSONBaseDataclass`][fancy_dataclass.json.JSONBaseDataclass] instead of `JSONDataclass`. This will set `store_type` to `'qualname'` automatically.

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
