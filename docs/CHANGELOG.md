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

[unreleased]: https://github.com/jeremander/fancy-dataclass/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.3
[0.4.2]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.4.2
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
