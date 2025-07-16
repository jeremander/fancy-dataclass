<!-- markdownlint-disable MD034 -->

# TODO

## v0.10.0

- Update CHANGELOG

## v0.10.1

- Documentation
  - Dataclass mixins/settings
    - For now, `dataclass` decorator is required
    - Note purpose of `flattened=True` (good for tabular data like CSV/SQL)
    - Advanced: how to handle name collisions in settings for multiple inheritance (e.g. `ArgparseDataclass`/`SubprocessDataclass`)
    - Emphasize type conversions are only to/from dict, not general constructors (this is a difference from `pydantic`).
  - JSON
  - TOML
  - CLI
  - SQL
    - Primary key (default `_id`)
    - Relationships
  - Subprocess
  - Config
  - Defining new mixins (what dunders need to be set)
    - Top-level settings, field-level settings
    - Collisions
      - Colliding `FieldSettings` and custom adapters

## Future

- When subclassing `TOMLDataclass` and `JSONDataclass`, the `to_dict` representation includes `NoneProxy`, which cannot get JSON serialized and is not "truly" `None`.
  - Current workaround is to make `NoneProxy` JSON-serializable, but this is a hack.
- General-purpose validator mixin?
  - Does type-checking post-init, with ability to supply custom validation functions
  - Have most other mixins inherit from this?
- `from_dict` in the case where custom `__init__` doesn't line up with dataclass fields?
- `alias` metadata field for dict conversion
  - Should this be bidirectional? Or separate fields for each direction? [pydantic](https://docs.pydantic.dev/latest/concepts/alias/) provides both.
  - https://github.com/jeremander/fancy-dataclass/issues/5
- Field converters
  - https://github.com/jeremander/fancy-dataclass/issues/2
- `PromptDataclass` to prompt user for each value type
  - Be able to supply validator functions
  - Specify behavior on error (bail or loop)
  - Ctrl-C to break out one level of loop
- `TabularDataclass`? CSV/TSV/parquet/feather
  - Simplest if single class can save/load all these file types
  - Convert to/from `pandas` `Series` and `DataFrame`?
    - If so, make `pandas` an optional dependency
    - Easy to implement conversion via `dict`, if we subclass `DictDataclass`
- `VersionedDataclass`
  - Helper functions for the following (only if deemed useful):
    - `get_version`: given name and version, gets the class
    - `get_versions`: given name, gets dict from version to class
    - `has_version`:
      - could be method on `VersionedDataclass` to get a specific version
      - or a function that takes a name and version and returns a bool
    - `get_version_registry`: return the global singleton registry
- `JSON5Dataclass`?
- Field metadata
  - Be strict about unknown field metadata keys? (Maybe issue warning?)
    - Might be annoying if people want to store extra metadata.
  - PEP 712 (`converter` argument for dataclass fields)
  - Allow `Annotated` as an alternative to `field.metadata`
    - Esp. with `Doc`: this could auto-populate JSON schema, argparse description
  - `BinaryDataclass`?
- Tiered configs?
- Improve `mkdocs` documentation
  - Auto-generate per-field descriptions via PEP 727?
  - Auto-generate dataclass field docs?
- Automatic JSON schema generation (see `pydantic`)
  - Borrow/use: https://github.com/Peter554/dc_schema/tree/master?tab=MIT-1-ov-file#readme
    - Attribution?
- Validation
  - More robust type validation when `validate=True` in `DictDataclass`
  - `ValidatedDataclass` to validate at construction time?
- More test coverage
  - More complex examples
  - Cover more data types (dynamically generate dataclass types)
- Performance benchmarks
  - `pydantic` might have some? Obviously won't beat those.
  - Identify bottlenecks and focus on those.
  - Memory usage & speed
  - Use __slots__? (can set this in dataclass options: does it break other things?)
- Optional dependencies
  - Allow `tomlkit` for now, make `sql` optional
  - May be overkill unless dependencies are heavy
  - Document this
