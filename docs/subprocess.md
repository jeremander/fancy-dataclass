🚧 **Under construction** 🚧

## Usage Example

Define a `SubprocessDataclass` to delegate calls to command-line programs within Python.

```python
from dataclasses import dataclass, field
from typing import ClassVar

from fancy_dataclass.subprocess import SubprocessDataclass


@dataclass
class ListDir(SubprocessDataclass, exec='ls'):
    """Lists directory contents."""
    # list in long form
    long: bool = field(default=False, metadata={'args': '-l'})
    # list in reverse order
    reverse: bool = field(default=False, metadata={'args': '-r'})
    # sort by time
    time: bool = field(default=False, metadata={'args': '-t'})
    # name of directory to list
    dir_name: str = field(default='.', metadata={'args': ''})
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
>>> listdir.args()
['-l', 'test_dir']
>>> listdir.run_subprocess()
total 0
-rw-r--r--  1 root  root  0 Apr  5 23:33 test.txt
```
