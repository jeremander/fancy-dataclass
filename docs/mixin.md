<!-- markdownlint-disable MD046 MD052 -->

`fancy_dataclass` makes use of *mixin* classes to extend ordinary dataclasses with custom features.

Mixin classes inherit from a base class called [`DataclassMixin`][fancy_dataclass.mixin.DataclassMixin]. A class may inherit from multiple mixin classes. Below is a list of pre-defined mixin classes which can be imported.

- [CLI Parsing](cli.md)
    - `ArgparseDataclass`
    - `CLIDataclass`
- [Configurations](config.md)
    - `ConfigDataclass`
- Serialization
    - `DictDataclass`
    - [`JSONDataclass`](json.md)
    - [`TOMLDataclass`](toml.md)
- [SQL Persistence](sql.md)
    - `SQLDataclass`
- [Subprocess Calls](subprocess.md)
    - `SubprocessDataclass`
- [Version Management](versioned.md)
    - `VersionedDataclass`

!!! note

    When inheriting from dataclass mixins, it is still required to use the `@dataclass` [decorator](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass) on the class itself:

    ```python
    from dataclasses import dataclass
    from fancy_dataclass import JSONDataclass

    class Foo(JSONDataclass):  # BAD
        ...

    @dataclass
    class Bar(JSONDataclass):  # GOOD
        ...
    ```

Mixin classes have two kinds of settings: *class settings* and *field settings*. Class settings govern the behavior of the class itself, while field settings control individual dataclass fields.

## Class Settings

Each mixin class has an associated class settings type, which can be accessed via the `__settings_type__` attribute on the class. It also has a default setting, accessed via the `__settings__` attribute.

For example:

```python
from fancy_dataclass import JSONDataclass

JSONDataclass.__settings__
# DictDataclassSettings(suppress_defaults=True, suppress_none=False, store_type='auto', flatten=False, allow_extra_fields=True, validate=True)
```

To override the default settings on a custom subclass, you can either set the `__settings__` attribute explicitly, or (more easily) pass extra keywords when inheriting from the mixin, e.g.

```python
class MyDataclass(JSONDataclass, suppress_defaults=False):
    ...

MyDataclass.__settings__
# DictDataclassSettings(suppress_defaults=False, suppress_none=False, store_type='auto', flatten=False, allow_extra_fields=True, validate=True)
```

Things are a little more awkward when inheriting from *multiple* mixin classes. In that case, the settings type is a sort of "fusion" of the parent classes' settings types, but you can still set attributes for any of the parent settings in the same way as above.

## Field Settings

Whereas class settings affect the behavior of the whole class, field settings are attached to each individual dataclass field. The field settings type associated with a mixin class can be found in the `__field_settings__` attribute. To override the default settings for a field, simply specify them as part of the `metadata` of the `field` constructor for that field. For example:

```python
class Circle(JSONDataclass):
    radius: float = field(
        default=1.0,
        metadata={'suppress_default': True},
    )
```

This will cause the `radius` field to be suppressed when serializing a `Circle` to JSON when its value equals the default.
