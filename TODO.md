# TODO

## v0.1.0

- Settings
  - `__init_subclass__` on `DataclassMixin` to grab kwargs and store them in one big dict
  - Subclasses can define their own settings dataclass and extract them from the settings dict
- Change `to_dict_full` to a kwarg of `to_dict`
- Unit tests
  - Test all flags (e.g. suppress_defaults, store_type, qualified_type)
  - Test multiple inheritance (all the classes?)
    - What happens to the class settings?
- toml
  - `tomlkit` maintains parsed structure (incl. whitespace & comments)
- documentation
  - Dataclass settings
    - For now, `dataclass` decorator is required
  - JSON
  - TOML
  - CLI
  - SQL
  - Subprocess
  - Config
- Github Actions for automated testing (with different Python versions)
  - Coverage badge
- PyPI
- Forbid inheritance from `JSONDataclass`?
  - Tell user they should subclass `JSONBaseDataclass` or pass `store_type=True`

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
- Performance benchmarks
  - `pydantic` might have some? Obviously won't beat those.
  - Identify bottlenecks and focus on those.
- Auto-wrap dataclass decorator when inheriting from DataclassMixin?
  - `__init_subclass__`
  - Downside: makes the decoration implicit
