<!-- markdownlint-disable MD052 -->

The [`JSONDataclass`][fancy_dataclass.json.JSONDataclass] mixin provides automatic conversion to and from [JSON](https://en.wikipedia.org/wiki/JSON).

- [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] / [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] convert to and from Python dicts.
- [`to_json`][fancy_dataclass.json.JSONSerializable.to_json] / [`from_json`][fancy_dataclass.json.JSONSerializable.from_json] convert to and from JSON file-like objects.
- [`to_json_string`][fancy_dataclass.json.JSONSerializable.to_json_string] / [`from_json_string`][fancy_dataclass.json.JSONSerializable.from_json_string] convert to and from JSON strings.

## Usage Example

Define a `JSONDataclass`.

```python
from dataclasses import dataclass
from typing import Optional

from fancy_dataclass.json import JSONDataclass


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

🚧 **Under construction** 🚧

<!--
- Inherits from `DictDataclass`
- Suppressing defaults
- Other settings (`store_type`, `qualified_type`)
- `JSONBaseDataclass` providing `qualified_type=True`
- kwargs get passed to `json.dump`
- `strict` argument in `from_dict`
- Override `_json_encoder`, `_json_key_decoder`
-->

### Notes

- `JSONDataclass` is configured to use the default JSON settings provided by Python's standard [`json`](https://docs.python.org/3/library/json.html) library. This allows out-of-range float values like `nan` and `inf` to be represented as `NaN` and `Infinity`, which are not strictly part of the JSON standard. To disallow these values, you can pass `allow_nan=False` when calling `to_json` or `to_json_string`, which will raise a `ValueError` if such values occur.

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
