# TODO

## v0.2.0

- Merging dataclass types
  - Helper function to implement the isomorphism directly
  - Handle
    - Union
      - Create flattened fields for all variants
    - Optional
        - Breaks round-trip fidelity:
          @dataclass
          class C:
            c: Optional['C'] = None
    - Nesting in lists/dicts
      - These are just kept nested (no flattening)
    - ClassVars
  - Have merging handle Settings specially?
    - Take union of Settings classes
  - Simplify _class_with_merged_fields
    - Avoid monkey-patching _to_nested
  - Test this extensively
    - Round-trip conversion nested->flattened->nested->flattened
- Use `typing` helper functions like `get_type_hints`, `get_args`, etc. instead of dunder methods
- Standardize field settings
  - Too complicated to nest within field metadata
  - Class should declare what fields it recognizes
    - If base classes share a field of the same name, raise a `TypeError` upon type construction
    - `DictDataclass` allows per-field `suppress` and `suppress_default`: canonize these
- `SubprocessDataclass`: instead of `subprocess_exclude`, make `args` `None` or something?
- Unit tests
  - Test all flags (e.g. suppress_defaults, store_type, qualified_type)
  - Test multiple inheritance (all the classes?)
    - What happens to the class settings?
      - Operation to dynamically merge dataclasses? Error if any fields collide.
  - Comparison with dataclasses.asdict
  - Test no pre-made mixins have any field metadata overlap
- ConfigDataclass
  - Handle nesting properly (updating nested ConfigDataclass should update the parent)
- toml
  - `tomlkit` maintains parsed structure (incl. whitespace & comments)
  - Let ConfigDataclass parse TOML
- Docs (under construction)
- PyPI

## v0.2.1

- documentation
  - Dataclass settings
    - For now, `dataclass` decorator is required
    - Note purpose of `nested=False` (good for tabular data like CSV/SQL)
  - JSON
  - TOML
  - CLI
  - SQL
  - Subprocess
  - Config
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
