🚧 **Under construction** 🚧

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

Convert to/from JSON.

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
