# TODO

## v0.1.0

- typing & unit tests
  - Any
  - NamedTuple (convert to `dict`?)
  - All flags (e.g. suppress_defaults)
- toml
  - `tomlkit` maintains parsed structure (incl. whitespace & comments)
- documentation
  - Configuration
  - JSON
  - TOML
  - CLI
  - SQL
  - Subprocess
- Github Actions for automated testing (with different Python versions)
- PyPI

## Future

- Deprecate public class vars
  - Give them special prefix? Or, special Config object (like pydantic)
  - Probably best to assign a `_config` class field
  - Use `__init_subclass__` (see https://peps.python.org/pep-0487/) to provide extra config kwargs when subclassing?
- Deprecate current CLI/subprocess metadata fields; make them nested fields within metadata?
- ConfigDataclass?
- More test coverage
  - More complex examples
  - Cover more data types (dynamically generate dataclass types)
- Automatic JSON schema generation (see `pydantic`)
- Auto-wrap dataclass decorator when inheriting from DataclassMixin?
  - `__init_subclass__`
  - Downside: makes the decoration implicit
