# TODO

## v0.2.0

- Documentation
  - 1-2 sentence intro for each subpage
- PyPI

## v0.3.0

- ConfigDataclass
  - Handle nesting properly (updating nested ConfigDataclass should update the parent)
  - Load from JSON/TOML
    - Options:
      1. Inherit from JSONDataclass/TOMLDataclass (superfluous)?
      2. Method to load from either, which calls `from_dict` on a proxy class then `coerce_to_dataclass`?
    - Infer file type from extension
- TOMLDataclass
  - `tomlkit` maintains parsed structure (incl. whitespace & comments)
  - Let ConfigDataclass parse TOML
- Basic usage examples in docs

## v0.3.1

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
  - Host on GH Pages or Readthedocs
- Github Actions for automated testing
  - Configure as much as possible via `hatch`
    - `ruff`, `mypy`, `pytest`, `radon`
    - Multiple versions of Python
  - Coverage badge

## Future

- `TabularDataclass`? CSV/TSV/parquet/feather
  - Make `SQLDataclass` inherit from it
- Support subparsers in `ArgparseDataclass`
- Field metadata
  - Be strict about unknown field metadata keys? (Maybe issue warning?)
    - Might be annoying if people want to store extra metadata.
  - PEP 712 (`converter` argument for dataclass fields)
  - Allow `Annotated` as an alternative to `field.metadata`
    - Esp. with `Doc`: this could auto-populate JSON schema, argparse description
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
