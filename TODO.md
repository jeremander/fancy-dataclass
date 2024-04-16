# TODO

## v0.3.1

- Github Actions for automated testing
  - Badges (shields.io)
    - Coverage
  - Auto-publish when new tag is pushed (see: https://pypi.org/manage/project/fancy-dataclass/settings/publishing/)
      - Require tag to match version?
      - Do "hatch version" and check if it's a prefix of "git describe --tags" or matches "git describe --tags --abbrev=0"
  - PyPI Links
    - Changelog
- Release
  - CHANGELOG update
    - pre-push hook to ensure it contains an entry for the latest tag
  - Tag new version

## v0.4.0

- `DictConfig` subclass of `Config` (unstructured configs loaded from JSON/TOML)

## v0.4.1

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
    - Top-level settings, field-level settings, collisions

## Future

- `FileSerializable`
  - Add `save` and `load` convenience methods?
- `TabularDataclass`? CSV/TSV/parquet/feather
  - Make `SQLDataclass` inherit from it
  - Convert to/from `pandas` `Series` and `DataFrame`?
- `TOMLDataclass`
  - Require subclass to set `qualified_type=True`, like `JSONDataclass`?
  - Preserve document structure via `tomlkit`
    - NOTE: the parsed values themselves have a `_trivia` attribute storing various formatting info
    - Use field metadata (`help`?) as comment prior to the field
  - For `None`, serialize as commented field?
- `ArgparseDataclass`
  - Support subparsers
  - Test subparsers, groups, mutually exclusive groups
- Field metadata
  - Be strict about unknown field metadata keys? (Maybe issue warning?)
    - Might be annoying if people want to store extra metadata.
  - PEP 712 (`converter` argument for dataclass fields)
  - Allow `Annotated` as an alternative to `field.metadata`
    - Esp. with `Doc`: this could auto-populate JSON schema, argparse description
- Tiered configs?
- Improve `mkdocs` documentation
  - Auto-generate per-field descriptions via PEP 727?
  - Auto-generate dataclass field docs?
- Automatic JSON schema generation (see `pydantic`)
  - Borrow/use: https://github.com/Peter554/dc_schema/tree/master?tab=MIT-1-ov-file#readme
    - Attribution?
- Versioning (`version` ClassVar, with suppress=False)
  - `@version` decorator (with required integer argument)
    - Allows you to define multiple classes with the same name; stores distinct `version` `ClassVar` attributes and registers them with the same name
    - `from_dict` looks up the version number in the registry; if only newer exists:
      - If `strict=True`, raises an error; otherwise, attempts to coerce and issues a warning
    - Error if duplicate versions are set
  - Migration
- `CallableDataclass`
  - ABC providing `__call__` method on variadic positional args
  - `callable_dataclass` decorator wrapping a function into a `CallableDataclass` subclass where `kwargs` are parameters
    - To make class name explicit, would probably need to call it directly, e.g. `MyType = callable_dataclass(my_func)`
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
