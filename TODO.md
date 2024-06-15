<!-- markdownlint-disable MD034 -->

# TODO

## v0.7.0

- Support `suppress_none` in both `DictDataclassSettings` and `DictDataclassFieldSettings`
- Comments in `TOMLDataclass` serialization

## v0.8.0

- `VersionedDataclass`
  - `version` class setting (int) and `version` read-only class property
  - Should probably subclass `DictDataclass`, ensures that `version` property is stored in dict
    - Or could make it implicit, setting `version` to a `ClassVar` with `suppress` field setting `False`
  - `@version` decorator (with required integer argument)
    - Augments base type with `VersionedDataclass`
    - Allows you to define multiple classes with the same name; stores distinct `version` `ClassVar` attributes and registers them with the same name
    - Initialization looks up the version number in the registry; if only newer exists:
      - If `strict=True`, raises an error; otherwise, attempts to coerce and issues a warning
    - Error if duplicate versions are set
  - `def migrate(self, version)` method from object of one version to another
  - Singleton `VersionRegistry` object via `registry` property
    - Helper methods like `get_version`, `get_available_versions`, `has_version`
    - Avoid cyclic references (`weakref`?)
  - Deal with namespace collision? E.g. use `globals()` to ensure the latest version is the only one accessible within module's namespace, even if it is defined earlier than the others.

## v0.7.1

- documentation
  - Dataclass mixins/settings
    - For now, `dataclass` decorator is required
    - Note purpose of `flattened=True` (good for tabular data like CSV/SQL)
    - Advanced: how to handle name collisions in settings for multiple inheritance (e.g. `ArgparseDataclass`/`SubprocessDataclass`)
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

- `PromptDataclass` to prompt user for each value type
  - Be able to supply validator functions
  - Specify behavior on error (bail or loop)
  - Ctrl-C to break out one level of loop
- `TabularDataclass`? CSV/TSV/parquet/feather
  - Simplest if single class can save/load all these file types
  - Convert to/from `pandas` `Series` and `DataFrame`?
    - If so, make `pandas` an optional dependency
    - Easy to implement conversion via `dict`, if we subclass `DictDataclass`
- `TOMLDataclass`
  - Require subclass to set `qualified_type=True`, like `JSONDataclass`?
  - Preserve document structure via `tomlkit`
    - NOTE: the parsed values themselves have a `_trivia` attribute storing various formatting info
    - Use field metadata (`help`?) as comment prior to the field
  - For `None`, serialize as commented field?
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
