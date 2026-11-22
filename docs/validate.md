<!-- markdownlint-disable MD052 -->

The [`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] mixin provides *runtime type validation* of dataclass fields. By default this will check that the type of each field value matches its declared type, raising a [`FieldTypeValidationError`][fancy_dataclass.utils.FieldTypeValidationError] otherwise.

## Usage Example

Define a `ValidatedDataclass`.

```python
from dataclasses import dataclass
from fancy_dataclass import ValidatedDataclass

@dataclass
class A(ValidatedDataclass):
    x: int

# OK
>>> obj = A(1)

# wrong type
>>> obj = A('1')
# FieldTypeValidationError: field 'x' of A: value '1' does not match expected type int
```

## Details

[`ValidatedDataclass`][fancy_dataclass.validate.ValidatedDataclass] enables runtime type-checking of dataclass fields. There are two places where validation can occur:

- Upon *initialization* (construction) of an object.
- Upon *assignment* of a value to a field.

By default, `ValidatedDataclass` will perform validation on both initialization and assignment of every field, but this can be overridden via the settings.

Note that dataclasses configured with `frozen=True` are not mutable, so fields cannot be assigned to new values after initialization at all. See the [Python docs](https://docs.python.org/3/library/dataclasses.html#frozen-instances) for details.

At present, type-checking is done using the [typeguard](https://typeguard.readthedocs.io/en/latest/) library. Be aware that this can entail a performance penalty. For example, validating container types like `list[str]` requires checking the type of all elements of a list, which can be expensive for very long lists.

### Class and Field Settings

You may customize the behavior of a `ValidatedDataclass` subclass by passing keyword arguments upon inheritance (see [mixin class settings](mixin.md#class-settings)). See [`ValidatedDataclassSettings`][fancy_dataclass.validate.ValidatedDataclassSettings] for the full list of settings. For field-specific settings, see [`ValidatedDataclassFieldSettings`][fancy_dataclass.validate.ValidatedDataclassFieldSettings].

To summarize briefly, the `validate_init` flag toggles validation for initialization, and the `validate_assign` flag toggles validation for assignment. The `validate` flag toggles both simultaneously but has lower priority than `validate_init` and `validate_assign`.

### Subclasses

While `ValidatedDataclass` can be used on its own, its functionality is provided automatically in several subclasses in `fancy_dataclass` such as [`DictDataclass`](dict.md), [`JSONDataclass`](json.md), and [`TOMLDataclass`](toml.md). See [Field Validation](dict.md#field-validation) for an example of the validation behavior for `DictDataclass`.

### Future Work

🚧 At present, we only support the default type-checking behavior provided by `typeguard`, but we have plans to eventually support custom field validation by interpreting additional per-field metadata. These could be custom callables or potentially static markers such as those in [`annotated_types`](https://github.com/annotated-types/annotated-types).

In the meantime, for a more fully-featured validation library, [`pydantic`](https://docs.pydantic.dev/latest) is an excellent choice. Over time we would like to close the gap in functionality so that `fancy_dataclass` can achieve similar customization of validation.
