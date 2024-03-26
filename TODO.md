# TODO

## v0.2.0

- Merging dataclass types
  - Helper function to implement the isomorphism directly
    - For merged->nested, needs to remember the partition of fields
    - Function can take recursive=True kwarg
    - Have this function handle Settings specially?
      - Take union of Settings classes
  - Simplify _class_with_merged_fields
    - Avoid monkey-patching _to_nested
  - Test this extensively
- Unit tests
  - Test all flags (e.g. suppress_defaults, store_type, qualified_type)
  - Test multiple inheritance (all the classes?)
    - What happens to the class settings?
      - Operation to dynamically merge dataclasses? Error if any fields collide.
  - Comparison with dataclasses.asdict
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

- Deprecate public class vars
  - Give them special prefix? Or, special Config object (like pydantic)
  - Probably best to assign a `_config` class field
  - Use `__init_subclass__` (see https://peps.python.org/pep-0487/) to provide extra config kwargs when subclassing?
- Deprecate current CLI/subprocess metadata fields; make them nested fields within metadata?
- Automatic JSON schema generation (see `pydantic`)
- Versioning (version ClassVar, with suppress=False)
  - Migration
- More test coverage
  - More complex examples
  - Cover more data types (dynamically generate dataclass types)
- Performance benchmarks
  - `pydantic` might have some? Obviously won't beat those.
  - Identify bottlenecks and focus on those.
- Auto-wrap dataclass decorator when inheriting from DataclassMixin?
  - `__init_subclass__`
  - Downside: makes the decoration implicit
