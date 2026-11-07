<!-- markdownlint-disable MD052 -->

Python's [`subprocess`](https://docs.python.org/3/library/subprocess.html) module is commonly used to call other programs from within Python.

The [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] mixin provides a simple wrapper for `subprocess.run` which builds up the argument list automatically from a dataclass's fields. This can be useful in at least two ways:

1. Cuts down the boilerplate of handling argument names and string conversions.
2. Can improve security if you add field validation before passing values to `subprocess.run`.

## Usage Example

Define a `SubprocessDataclass` to delegate calls to command-line programs within Python.

```python
from dataclasses import dataclass, field

from fancy_dataclass import SubprocessDataclass


@dataclass
class ListDir(SubprocessDataclass, exec='ls'):  # specify program to run
    """Lists directory contents."""
    # list in long form
    long: bool = field(
        default=False,
        metadata={'option_name': '-l'}
    )
    # list in reverse order
    reverse: bool = field(
        default=False,
        metadata={'option_name': '-r'}
    )
    # sort by time
    time: bool = field(
        default=False,
        metadata={'option_name': '-t'}
    )
    # name of directory to list
    dir_name: str = field(
        default='.',
        metadata={'subprocess_positional': True}
    )
```

Set up a test directory with an example file.

```python
from pathlib import Path

test_dir = Path('test_dir')
test_dir.mkdir()
(test_dir / 'test.txt').touch()
```

Instantiate `ListDir`, inspect its arguments, and call `ls` in a subprocess.

```python
>>> listdir = ListDir(long=True, dir_name='test_dir')
>>> listdir.get_executable()
'ls'
>>> listdir.get_args()
['ls', '-l', 'test_dir']
>>> listdir.run_subprocess()
total 0
-rw-r--r--  1 root  root  0 Apr  5 23:33 test.txt
```

## Details

The [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] mixin provides the following useful methods automatically:

- [`get_executable`][fancy_dataclass.subprocess.SubprocessDataclass.get_executable]: get the name of the executable to run in a subprocess
- [`get_args`][fancy_dataclass.subprocess.SubprocessDataclass.get_args]: get the list of arguments to pass to `subprocess.run` (with the executable as the first argument)
- [`run_subprocess`][fancy_dataclass.subprocess.SubprocessDataclass.run_subprocess]: run the executable with arguments in a subprocess

### Class and Field Settings

You may customize the behavior of a `SubprocessDataclass` subclass by passing keyword arguments upon inheritance (see [mixin class settings](mixin.md#class-settings)). See [`SubprocessDataclassSettings`][fancy_dataclass.subprocess.SubprocessDataclassSettings] for the full list of settings. For field-specific settings, see [`SubprocessDataclassFieldSettings`][fancy_dataclass.subprocess.SubprocessDataclassFieldSettings].

### Executable Name

The [`get_executable`][fancy_dataclass.subprocess.SubprocessDataclass.get_executable] method may be overridden to return the name of the executable, but the default implementation usually suffices. It obtains the name as follows:

1. If the [class settings][fancy_dataclass.subprocess.SubprocessDataclassSettings] specify an `exec` member, uses that.
2. Otherwise, returns the value of the first dataclass field whose `exec` [field setting][fancy_dataclass.subprocess.SubprocessDataclassFieldSettings] is set to `True`.

Case 1 is typically for when the executable name is constant, while Case 2 is for when the name should vary based on the value of a field.

### Arguments

The default implementation of `get_args` will aggregate the results of the [`get_arg`][fancy_dataclass.subprocess.SubprocessDataclass.get_arg] method called on each dataclass field, followed by an additional list of arguments provided by the `extra_args` [class setting][fancy_dataclass.subprocess.SubprocessDataclassSettings].

`get_arg`'s default behavior will use the field name as a CLI option name, prefixed with `-` if it is one character long and `--` otherwise, and replacing underscores in the field name with dashes. The *value* of the option will be a stringified version of the dataclass field's value.

To override the default behavior of `get_arg`, you can:

1. Override `get_arg` itself to provide custom logic.
2. Set the `option_name` field setting to a specific name.

If the type of the field is `bool`, it will be treated as an argument-less *flag* instead of an option, unless the `subprocess_flag` field setting is set to `False`.

If the type of the field is a sequence (like `list` or `tuple`), the sequence values will be listed out sequentially as subprocess arguments. If the `repeat_option` field setting is `True`, the argument name will be repeated for each successive value. For example, if the field is `my_arg: list[int]` and the value is `[1, 2, 3]`, the default command-line arguments will come out as

```text
--my-arg 1 2 3
```

With `repeat_option = True`, they become

```text
--my-arg 1 --my-arg 2 --my-arg 3
```

If the `subprocess_positional` field setting is `True`, the field name will not be used as an option string; instead the field value along will be used as a positional argument.
