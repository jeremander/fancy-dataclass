<!-- markdownlint-disable MD034 -->

# TODO

## v0.13.0

- Documentation
  - CLI
  - SQL
    - Primary key (default `_id`)
    - Relationships

## Future

- General-purpose validator mixin? `ValidatedDataclass`?
  - Does type-checking post-init, with ability to supply custom validation functions
  - Have most other mixins inherit from this?
  - Interaction with `validate=True` in `DictDataclass`?
    - Simplest would be to deprecate/remove *all* validation features from here.
    - Alternatively could keep this flag, and have the class inherit from `ValidatedDataclass` if it's set.
  - Configs
    - Flag to validate when setting field value (default `False`)
    - Collection checking mode (`O1`, `Ologn`, `On`)
    - PEP 484 tower
    - Whether to decorate all methods with arg & return type-checking (default `False`)
- Field metadata
  - Field converters
    - https://github.com/jeremander/fancy-dataclass/issues/2
  - PEP 712 (`converter` argument for dataclass fields), was rejected
  - Can implement it by hooking `__post_init__` with `__init_subclass__`, using `object.__setattr__` to set fields to converted values (even for frozen dataclass)
  - Allow `Annotated` as an alternative to `field.metadata`
    - Already supporting this with `Doc` for some things like `argparse` help, but could somehow encompass all metadata?
- `alias` metadata field for dict conversion
  - Should this be bidirectional? Or separate fields for each direction? [pydantic](https://docs.pydantic.dev/latest/concepts/alias/) provides both.
  - https://github.com/jeremander/fancy-dataclass/issues/5
  - Simple approach would be to allow the value to be a list and have the first alias be "primary" (the one used for serialization), and have them be in descending priority order for consumption.
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
- `BinaryDataclass`?
- Tiered configs?
- Improve `mkdocs` documentation
  - Auto-generate per-field descriptions via PEP 727?
  - Auto-generate dataclass field docs?
- Automatic JSON schema generation (see `pydantic`)
  - Borrow/use: https://github.com/Peter554/dc_schema/tree/master?tab=MIT-1-ov-file#readme
    - Attribution?
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
