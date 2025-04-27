<!-- markdownlint-disable MD052 -->

The [`VersionedDataclass`][fancy_dataclass.versioned.VersionedDataclass] mixin provides a versioning mechanism for dataclass types. This ensures the following:

- A `version` attribute is set on the class, which must be an integer.
- Any two `VersionedDataclass` subclasses with the same name must have distinct versions.
- A global registry tracks the available versions of each `VersionedDataclass`. This can be used to manage different versions of "the same" class, which can be useful for things like [migrations](#migrations).

## Usage Example

Define two versions of the same dataclass:

```python
from dataclasses import dataclass
from typing import Optional

from fancy_dataclass import VersionedDataclass

@dataclass
class Person(VersionedDataclass, version=1):
    name: str
    age: int

Person_V1 = Person  # alias with explicit version in the name

# override the class definition of `Person` with version 2
# (this could also live in a different module from the first version)
@dataclass
class Person(VersionedDataclass, version=2):
    name: str
    age: int
    height: Optional[float] = None

Person_V2 = Person
```

`VersionedDataclass` inherits from [`DictDataclass`][fancy_dataclass.dict.DictDataclass], so instances can be automatically converted to/from Python dicts:

```python
>>> person = Person(name='Alice', age=28, height=63.5)
# note that the version number gets included!
>>> person.to_dict()
{'version': 2, 'name': 'Alice', 'age': 28, 'height': 63.5}
```

An alternative but equivalent way to define a `VersionedDataclass` is with the `version` decorator:

```python
from fancy_dataclass import version

@version(2)
@dataclass
class Person:
    name: str
    age: int
    height: Optional[float] = None
```

## Version Restrictions

If you try to set a version that is not an integer, or that is a duplicate of an already-existing version, you get an error:

```python
@version('1.2')
@dataclass
class Person:
    ...

TypeError: must supply an integer `version` attribute for class 'Person'
```

```python
@version(1)
@dataclass
class Person:
    ...

@version(1)
@dataclass
class Person:
    ...

TypeError: class already registered with name 'Person', version 1: __main__.Person
```

### Class and Field Settings

Since `VersionedDataclass` inherits from `DictDataclass`, it possesses all of the same class and field settings.

Additionally it has a `suppress_version` class setting (default `False`). If set to `True`, the version will be omitted from the Python dict representation. So if we defined `Person` like:

```python
@version(2, suppress_version=True)
@dataclass
class Person:
    ...
```

Then the dict representation of `Alice` would become:

```python
{'name': 'Alice', 'age': 28, 'height': 63.5}
```

However, if you plan to support multiple versions in the same data set, it is good practice to include the version field to distinguish them.

## Migrations

`VersionedDataclass` is useful for performing *migration* between different versions of the same type.

For example, suppose we have a version 1 `Person` and want to convert it to a version 2 `Person`:

```python
>>> person1 = Person_V1(name='Alice', age=28)
>>> person1
Person(name='Alice', age=28)
>>> person1.version
1
>>> person2 = person1.migrate(version=2)
>>> person2
Person(name='Alice', age=28, height=None)
>>> person2.version
2
```

Or if we have a version 2 `Person` and want to convert it to a version 1 `Person`:

```python
>>> person2 = Person_V2(name='Alice', age=28, height=63.5)
>>> person2.to_dict()
{'version': 2, 'name': 'Alice', 'age': 28, 'height': 63.5}
>>> person1 = person2.migrate(version=1)
>>> person1.to_dict()
{'version': 1, 'name': 'Alice', 'age': 28}
```

We get an error if we try to migrate to an unknown version:

```python
>>> person1 = Person_V1(name='Alice', age=28)
>>> person1.migrate(version=3)
...
ValueError: no class registered with name 'Person', version 3
```

If you omit the `version` argument, it will migrate to whatever the latest known version is:

```python
>>> person1 = Person_V1(name='Alice', age=28)
>>> person1.migrate().version
2
```

Here are the general principles for how migrations work:

- If a field is present in the source class and not in the target class, it is removed during migration.
- If a field is present in the target class and not in the source class:
    - If the field has a default value, that value is used when migrating.
    - Otherwise, an error is raised.

One pitfall here is that if you *rename* a field, there is no way to link the old and new versions together:

```python
@version(3)
@dataclass
class Person:
    name: str
    age: int
    hobbies: Optional[list[str]] = None

Person_V3 = Person

@version(4)
@dataclass
class Person:
    name: str
    age: int
    interests: Optional[list[str]] = None

Person_V4 = Person

>>> person3 = Person_V3(name='Alice', age=28, hobbies=['chess'])
>>> person3.migrate(version=4)
Person(name='Alice', age=28, interests=None)
```

Even though the intention was to rename `hobbies` to `interests`, the automatic migration did not carry over the `hobbies` from V3 since it had no way to know these two fields were linked. In the future we may introduce some mechanism for linking them.

You can override a class's `migrate` method to enable custom behavior. For instance, if we had defined `Person` version 3 like this:

```python
@version(3)
@dataclass
class Person:
    name: str
    age: int
    hobbies: Optional[list[str]] = None

    def migrate(self, version=None):
        new_person = super().migrate(version=version)
        if new_person.version == 4:
            new_person.interests = self.hobbies
        return new_person

Person_V3 = Person
```

Then the migration works like we want it to:

```python
>>> person3 = Person_V3(name='Alice', age=28, hobbies=['chess'])
>>> person3.migrate(version=4)
Person(name='Alice', age=28, interests=['chess'])
```

### Dict Conversion

When converting from a dict or JSON, there is a keyword argument, `migrate` (default `False`), which will auto-migrate if set to `True`. This example illustrates the difference in behavior from the `migrate` flag:

```python
from dataclasses import dataclass
from typing import Optional

from fancy_dataclass import JSONDataclass, version

@version(1)
@dataclass
class Person(JSONDataclass, store_type='off'):
    name: str
    age: int
    hobbies: Optional[list[str]] = None

Person_V1 = Person

@version(2)
@dataclass
class Person(JSONDataclass, store_type='off'):
    name: str
    age: int
    height: Optional[float] = None

Person_V2 = Person

>>> person2 = Person_V2(name='Alice', age=28, height=63.5)
>>> json_str = person2.to_json_string()
>>> json_str
'{"version": 2, "name": "Alice", "age": 28, "height": 63.5}
# this is version 2 since the default is to use the given version information
>>> person = Person_V1.from_json_string(json_str)
>>> person.version
2
# this is version 1 since we force migration to the calling class
>>> person = Person_V1.from_json_string(json_str, migrate=True)
>>> person.version
1
```
