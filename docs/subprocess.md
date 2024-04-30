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
        metadata={'args': '-l'}
    )
    # list in reverse order
    reverse: bool = field(
        default=False,
        metadata={'args': '-r'}
    )
    # sort by time
    time: bool = field(
        default=False,
        metadata={'args': '-t'}
    )
    # name of directory to list
    dir_name: str = field(
        default='.',
        metadata={'args': ''}
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

🚧 **Under construction** 🚧

<!--
- Specify exactly one executable
- "Secure" example (rmdir?)
-->

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
