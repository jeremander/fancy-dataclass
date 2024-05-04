<!-- markdownlint-disable MD052 -->

`fancy_dataclass` makes it super-easy to create command-line programs.

The [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] mixin lets you automatically generate an [`argparse`](https://docs.python.org/3/library/argparse.html) argument parser from a dataclass. This saves a lot of boilerplate code which would be required to set up the parser manually.

The [`CLIDataclass`][fancy_dataclass.cli.CLIDataclass] mixin extends `ArgparseDataclass` by additionally providing a [`run`][fancy_dataclass.cli.CLIDataclass.run] method which you override to perform arbitrary program logic, given the parsed arguments. You can then call [`main`][fancy_dataclass.cli.CLIDataclass.main] on your custom dataclass to run an entire program end-to-end (parser construction, argument parsing, main program logic).

By default, `ArgparseDataclass` and `CLIDataclass` provide a "help" option so that a help menu is printed out when the user passes in `-h` or `--help` as an argument. The help string for each argument can be provided in the dataclass field metadata.

## Usage Example

Define a `CLIDataclass` instantiating a simple command-line calculator program.

```python
from dataclasses import dataclass, field

from fancy_dataclass import CLIDataclass


@dataclass
class Calculator(CLIDataclass):
    """A simple calculator program."""
    operation: str = field(metadata={
        'choices': ('add', 'sub', 'mul', 'div'),
        'help': 'operation to perform'
    })
    num1: float = field(metadata={
        'help': 'first number'
    })
    num2: float = field(metadata={
        'help': 'second number'
    })
    round: bool = field(metadata={
        'help': 'round result to the nearest whole number'
    })

    def run(self) -> None:
        # implement core program logic
        if self.operation == 'add':
            result = self.num1 + self.num2
        elif self.operation == 'sub':
            result = self.num1 - self.num2
        elif self.operation == 'mul':
            result = self.num1 * self.num2
        elif self.operation == 'div':
            result = self.num1 / self.num2
        else:
            raise ValueError('invalid operation')
        print(round(result) if self.round else result)


if __name__ == '__main__':
    Calculator.main()
```

Saving the code above as `calculator.py`, you can run:

```text
python calculator.py --help
```

This prints out the help menu:

```text
usage: calculator.py [-h] [--round] {add,sub,mul,div} num1 num2

A simple calculator program.

positional arguments:
  {add,sub,mul,div}  operation to perform
  num1               first number
  num2               second number

options:
  -h, --help         show this help message and exit
  --round            round result to the nearest whole number
```

Run the program with a few different options:

```text
python calculator.py add 2 3
5.0

python calculator.py add 3 -4
7.0

python calculator.py div 8 3
2.6666666666666665

python calculator.py div 8 3 --round
3
```

## Details

🚧 **Under construction** 🚧

<!--
- Can modify parser manually, or customize handling a specific arg
-->

<!--

### Groups and Exclusive Groups

- Use `group` or `exclusive_group` metadata to mark them
- Can nest `CLIDataclass` to provide group help string (as docstring by default)
- Cannot doubly nest groups or exclusive groups

### Subparsers

- Single nested field marked with `subcommand=True`
- Field should be a `Union` type, all of whose variants are `ArgparseDataclass` subclasses
- Each variant must have a name
    - By default, this will be the kebab-case version of the class name
    - A `command_name` class setting can override this
- Parsed args get stored in appropriate object type
- `subcommand` property returns the string name of the chosen subcommand
- For `CLIDataclass`, `run` can be created automatically by delegating to the subcommand field, provided each variant is a `CLIDataclass`
-->

<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>
