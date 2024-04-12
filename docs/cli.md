<style>
.md-sidebar--secondary {
    display: none !important;
}

.md-main__inner .md-content {
    max-width: 45rem;
}
</style>

🚧 **Under construction** 🚧

## Usage Example

Define a `CLIDataclass` instantiating a simple command-line calculator program.

```python
from dataclasses import dataclass, field

from fancy_dataclass.cli import CLIDataclass


@dataclass
class Calculator(CLIDataclass):
    """A simple calculator program."""
    operation: str = field(metadata={
        'choices': ('add', 'sub', 'mul', 'div'),
        'help': 'operation to perform'
    })
    num1: float = field(metadata={'help': 'first number'})
    num2: float = field(metadata={'help': 'second number'})
    round: bool = field(metadata={'help': 'round result to the nearest whole number'})

    def run(self) -> None:
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
python3 calculator.py --help
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
