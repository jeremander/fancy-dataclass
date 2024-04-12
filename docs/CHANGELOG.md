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

<!-- ## [0.2.0] -->

## [0.1.0]

### Added

- `DataclassMixin` class providing extra dataclass features
    - `ArgparseDataclass`: command-line argument parsing
    - `CLIDataclass`: command-line argument parsing and `main` function
    - `DictDataclass`: conversion to/from Python dict
    - `JSONDataclass`: conversion to/from JSON
    - `SQLDataclass`: SQL persistence via `sqlalchemy`
    - `SubprocessDataclass`: call out to another program via `subprocess`

[unreleased]: https://github.com/jeremander/fancy-dataclass/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jeremander/fancy-dataclass/releases/tag/v0.1.0

<br>

<!-- hide version subsections in nav sidebar -->

<style>
    .md-sidebar--secondary li li {
        display: none;
    }
</style>
