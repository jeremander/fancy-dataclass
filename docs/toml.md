<!-- markdownlint-disable MD052 -->

The [`TOMLDataclass`][fancy_dataclass.toml.TOMLDataclass] mixin provides automatic conversion to and from [TOML](https://en.wikipedia.org/wiki/TOML). This uses the [`tomlkit`](https://tomlkit.readthedocs.io) library under the hood.

- [`to_dict`][fancy_dataclass.dict.DictDataclass.to_dict] / [`from_dict`][fancy_dataclass.dict.DictDataclass.from_dict] convert to and from Python dicts.
- [`to_toml`][fancy_dataclass.toml.TOMLSerializable.to_toml] / [`from_toml`][fancy_dataclass.toml.TOMLSerializable.from_toml] convert to and from TOML file-like objects.
- [`save`][fancy_dataclass.serialize.FileSerializable.save] / [`load`][fancy_dataclass.serialize.FileSerializable.load] convert to and from a TOML file-like object or path.
- [`to_toml_string`][fancy_dataclass.toml.TOMLSerializable.to_toml_string] / [`from_toml_string`][fancy_dataclass.toml.TOMLSerializable.from_toml_string] convert to and from TOML strings.

## Usage Example

Define a `TOMLDataclass`.

```python
from dataclasses import dataclass

from fancy_dataclass.toml import TOMLDataclass


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

🚧 **Under construction** 🚧

<!--
- TOML is more of a config format than a storage format
- Unlike JSONDataclass, defaults are not suppressed by default, but can set `suppress_defaults=True`
 -->

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
