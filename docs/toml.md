<!-- markdownlint-disable MD046 MD052 -->

The [`TOMLDataclass`][fancy_dataclass.toml.TOMLDataclass] mixin provides automatic conversion to and from [TOML](https://en.wikipedia.org/wiki/TOML). This uses the [`tomlkit`](https://tomlkit.readthedocs.io) library under the hood.

- [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] / [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] convert to and from Python dicts.
- [`to_toml`][fancy_dataclass.toml.TOMLSerializable.to_toml] / [`from_toml`][fancy_dataclass.toml.TOMLSerializable.from_toml] convert to and from TOML file-like objects.
- [`save`][fancy_dataclass.serialize.FileSerializable.save] / [`load`][fancy_dataclass.serialize.FileSerializable.load] convert to and from a TOML file-like object or path.
- [`to_toml_string`][fancy_dataclass.toml.TOMLSerializable.to_toml_string] / [`from_toml_string`][fancy_dataclass.toml.TOMLSerializable.from_toml_string] convert to and from TOML strings.

## Usage Example

Define a `TOMLDataclass`.

```python
from dataclasses import dataclass

from fancy_dataclass import TOMLDataclass


@dataclass
class Database(TOMLDataclass):
    server: str
    ports: list[int]
    connection_max: int = 5000
    enabled: bool = True
```

Save data to a TOML file.

```python
>>> db_config = Database(server='192.168.1.1', ports=[8001, 8001, 8002])
>>> with open('db_config.toml', 'w') as f:
        db_config.to_toml(f)
```

View the TOML file `db_config.toml`:

```toml
server = "192.168.1.1"
ports = [8001, 8001, 8002]
connection_max = 5000
enabled = true
```

Load the data from a TOML file:

```python
>>> with open('db_config.toml') as f:
        db_config = Database.from_toml(f)
>>> print(db_config)
Database(server='192.168.1.1', ports=[8001, 8001, 8002], connection_max=5000, enabled=True)
```

## Details

`TOMLDataclass` inherits from [`DictDataclass`][fancy_dataclass.dict.DictDataclass], which can be used to convert dataclasses to/from Python dicts via [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] and [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict]. You may use `DictDataclass` if you do not need to interact with TOML serialized data.

### Class and Field Settings

The class and field settings for `TOMLDataclass` are identical to those for [`JSONDataclass`](json.md#class-and-field-settings). See [`DictDataclassSettings`][fancy_dataclass.dict.DictDataclassSettings] for the list of class settings, and [`DictDataclassFieldSettings`][fancy_dataclass.dict.DictDataclassFieldSettings] for the list of field-specific settings.

TOML is intended as more of a configuration format than a data storage format. Consequently, unlike `JSONDataclass`, `TOMLDataclass` does not suppress default field values in its output by default. To opt into this behavior, you can set the class setting `suppress_defaults=True`.

#### Field Comments

Unlike JSON, the TOML format supports comments, which are lines beginning with `#`. You can use the `doc` attribute of each `TOMLDataclass` field to prepend a comment in the TOML output. For example:

```python
from dataclasses import dataclass, field

from fancy_dataclass import TOMLDataclass


@dataclass
class Rectangle(TOMLDataclass):
    width: float = field(metadata={'doc': 'width (in cm)'})
    height: float = field(metadata={'doc': 'height (in cm)'})

>>> print(Rectangle(48.5, 30).to_toml_string())
# width (in cm)
width = 48.5
# height (in cm)
height = 30
```

!!! note

    You can also use the `Annotated`/`Doc` syntax (PEP 727) to specify field comments. See [`DocFieldSettings`][fancy_dataclass.settings.DocFieldSettings].

#### Top-level Comments

You may also want to include comment lines at the top of the TOML file or section. To do this, you can set parameters for the [class-level settings][fancy_dataclass.toml.TOMLDataclassSettings] in one of the following ways:

1. Set the `comment` setting to a string.
2. Set the `doc_as_comment` flag to `True`. In this case, the class's docstring will be used as a top-level comment.

These options are mutually exclusive (an error will be thrown if `doc_as_comment=True` and `comment` is also set).

For example, suppose we modify the definition of `Rectangle` above to:

```python
@dataclass
class Rectangle(TOMLDataclass, doc_as_comment=True):
    """Rectangle: A quadrilateral with all right angles."""
    width: float = field(metadata={'doc': 'width (in cm)'})
    height: float = field(metadata={'doc': 'height (in cm)'})
```

Then the TOML output becomes:

```toml
# Rectangle: A quadrilateral with all right angles.

# width (in cm)
width = 48.5
# height (in cm)
height = 30
```
