# TODO

## v0.2.0

- Standardize field settings
  - Too complicated to nest within field metadata
  - Class should declare what fields it recognizes
    - If base classes share a field of the same name, raise a `TypeError` upon type construction
    - `DictDataclass` allows per-field `suppress` and `suppress_default`: canonize these
    - Be strict about unrecognized metadata?
  - `SubprocessDataclass`: instead of `subprocess_exclude`, make `args` `None` or something?
  - Unit tests
    - Test no pre-made mixins have any field metadata overlap
- Don't have SQLDataclass inherit from DictDataclass?
- Docs
  - "Under construction" placeholders
  - CHANGELOG

## v0.3.0

- ConfigDataclass
  - Handle nesting properly (updating nested ConfigDataclass should update the parent)
- TOMLDataclass
  - `tomlkit` maintains parsed structure (incl. whitespace & comments)
  - Let ConfigDataclass parse TOML

## v0.3.1

- documentation
  - Dataclass mixins/settings
    - For now, `dataclass` decorator is required
    - Note purpose of `nested=False` (good for tabular data like CSV/SQL)
  - JSON
  - TOML
  - CLI
  - SQL
  - Subprocess
  - Config
  - Defining new mixins (what dunders need to be set)
    - Top-level settings, field-level settings, collisions
- Github Actions for automated testing (with different Python versions)
  - Coverage badge

## Future

- Allow `Annotated` as an alternative to `field.metadata`
  - Esp. with `Doc`: this could auto-populate JSON schema, argparse description
- `TabularDataclass`? CSV/TSV/parquet/feather
  - Make `SQLDataclass` inherit from it
- Field metadata
  - Be strict about unknown field metadata keys? (Maybe issue warning?)
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
- More test coverage
  - More complex examples
  - Cover more data types (dynamically generate dataclass types)
- Performance benchmarks
  - `pydantic` might have some? Obviously won't beat those.
  - Identify bottlenecks and focus on those.
  - Memory usage & speed
  - Use __slots__? (can set this in dataclass options: does it break other things?)
- Auto-wrap dataclass decorator when inheriting from DataclassMixin?
  - `__init_subclass__`
  - Downside: makes the decoration implicit
