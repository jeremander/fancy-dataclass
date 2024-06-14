# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Types of changes:
    - Added
    - Changed
    - Deprecated
    - Removed
    - Fixed
    - Security
-->

## [Unreleased]

## [0.6.1]

2024-06-14

### Added

- `ArgparseDataclass`: support for `--version` option (via `version` action)
    - User may set the `version` attribute in `ArgparseDataclassSettings` during inheritance

### Fixed

- `ArgparseDataclass`: Behavior of optional subcommands
    - By default, command-line subcommand optional if the field type is `Optional` (even without a default)
    - `required` flag in field metadata overrides default behavior
    - `required` must be `True` if field is non-`Optional` without a default

## [0.6.0]

2024-06-10

### Added

- New `ArgparseDataclassSettings` fields:
    - `formatter_class`: controls help formatter class for parent parser and subcommands (can be overridden by subcommands)
    - `help_descr_brief`: subcommand help format (brief), used in subcommand help menu
        - By default, this will match the full subcommand help, but lowercased with trailing period removed.

### Changed

- (_Breaking_) `ArgparseDataclass`: `parser_class` and `parser_description` classmethods have become `ArgparseDataclassSettings` fields `parser_class` and `help_descr`.

## [0.5.0]

2024-06-02

### Added

- Explicit `required` metadata flag in `ArgparseDataclass`
- More details in web docs for `JSONDataclass`, `TOMLDataclass`

### Changed

- (_Breaking_) `JSONDataclass` methods `json_encoder` and `json_key_decoder` now public

### Fixed

- Bugs in `ArgparseDataclass`

## [0.4.5]

2024-05-30

### Changed

- `ArgparseDataclass` `subcommand` property to `subcommand_name`

### Fixed

- `ArgparseDataclass`
    - Preserve snake case for positional arguments instead of replacing `_` with `-`

- `DictDataclass`
    - Support `numpy` scalars and arrays
    - Handle string type annotations (see [PEP 563](https://peps.python.org/pep-0563/))

## [0.4.4]

2024-05-06

### Added

- Groups, mutually exclusive groups, and subparsers for `ArgparseDataclass`
    - Nested `ArgparseDataclass` can be used as subparser if `subcommand=True` is set in field metadata
    - `CLIDataclass.run` will invoke subcommand if applicable

### Fixed

- `ArgparseDataclass` boolean flag field properly handles `action="store_false"` with field default `True`
- Field `suppress=False` overrides `suppress_defaults=True`

## [0.4.3]

2024-04-30

### Added

- `fancy_dataclass.func` module with `func_dataclass` wrapper
    - Converts an ordinary function into a parametrized dataclass type
- Documentation and tests for the above

## [0.4.2]

2024-04-29

### Added

- `fancy_dataclass/docs` subfolder containing HTML documentation (accessible without Internet access)

### Changed

- Using [`gadzooks`](https://github.com/jeremander/gadzooks) repo for the following `pre-commit` hooks:
    - `build-docs`: rebuild docs if any source markdown files changed
    - `loc-summarize`: print lines of code summary
    - `check-version`: check version consistency (package, Git tag, built distribution, changelog)

## [0.4.1]

2024-04-22

### Added

- `DictConfig` class for configs stored as untyped dict
- `DataclassAdaptable` mixin to convert one dataclass to another
    - Can be used to handle field name collisions in `DataclassMixin` settings
- `save` and `load` convenience methods for `FileSerializable` (includes `JSONDataclass` and `TOMLDataclass`)

### Changed

- `Config.get_config` returns reference instead of deepcopy
- Class hierarchy of `FileSerializable`
    - Split into `TextSerializable`, `BinarySerializable`
    - `TextFileSerializable` subclasses `BinaryFileSerializable`

## [0.3.1]

2024-04-16

### Added

- Documentation: Badges in README (workflow passing, coverage, docs, etc.)
- CI:
    - More GH Actions code checks
    - Testing Python versions 3.8-3.12 via `hatch` matrix

### Changed

- Top-level `*`-imports mostly limited to mixin classes via `__all__`
- Renamed `Config.configure` context manager to `as_config`
- Renamed `SubprocessDataclass.args` method to `get_args`

### Fixed

- Support for Python 3.8, 3.9 (which lack some newer type annotation features)

## [0.3.0]

2024-04-14

### Added

- `TOMLDataclass` for saving/loading TOML via [`tomlkit`](https://tomlkit.readthedocs.io/en/latest/)
    - Support for loading TOML configurations in `ConfigDataclass`
- `FileSerializable` and `DictFileSerializableDataclass` mixins to factor out shared functionality between JSON/TOML serialization
- Documentation
    - Usage examples for `TOMLDataclass` and `ConfigDataclass`
    - Hosting on Read the Docs [here](https://fancy-dataclass.readthedocs.io/en/latest/)
- CI: Github Actions to automate building/linting/testing

## [0.2.0]

2024-04-13

### Added

- `ConfigDataclass` mixin for global configurations
- Customization of `DataclassMixin`:
    - `DataclassMixinSettings` for mixin class configuration
    - `FieldSettings` for field-specific settings
    - `__post_dataclass_wrap__` hook to customize behavior after `dataclass` decorator is applied (e.g. validating fields at definition time)
- Documentation
    - [Reference pages](README.md) via [`mkdocs-material`](https://squidfunk.github.io/mkdocs-material) and [`mkdocstrings`](https://mkdocstrings.github.io)
    - Basic usage examples for main mixin classes
    - [CHANGELOG](#changelog)
- Linting via [`ruff`](https://docs.astral.sh/ruff/)
- Unit tests
    - Over 90% code coverage, via [`pytest-cov`](https://pytest-cov.readthedocs.io/en/latest/readme.html)

### Changed

- Build via [`hatch`](https://github.com/pypa/hatch)
- Better flattened/nested dataclass conversions

### Fixed

- More robust type handling

## [0.1.0]

2022-06-06

### Added

- `DataclassMixin` class providing extra dataclass features
    - `ArgparseDataclass`: command-line argument parsing
    - `CLIDataclass`: command-line argument parsing and `main` function
    - `DictDataclass`: conversion to/from Python dict
    - `JSONDataclass`: conversion to/from JSON
    - `SQLDataclass`: SQL persistence via `sqlalchemy`
    - `SubprocessDataclass`: call out to another program via `subprocess`

[unreleased]: https://github.com/jeremander/fancy-dataclass/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.6.1
[0.6.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.6.0
[0.5.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.5.0
[0.4.5]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.5
[0.4.4]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.4
[0.4.3]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.3
[0.4.2]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.2
[0.4.1]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.1
[0.3.1]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.3.1
[0.3.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.3.0
[0.2.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.2.0
[0.1.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.1.0

<br>

<!-- hide version subsections in nav sidebar -->

<style>
    .md-sidebar--secondary li li {
        display: none;
    }
</style>
