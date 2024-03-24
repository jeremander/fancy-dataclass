from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass, field
import sys
from typing import Any, Dict, List, Tuple

import pytest

from fancy_dataclass.cli import CLIDataclass


@dataclass
class DC1(CLIDataclass):
    """An example of CLIDataclass."""
    required_string: str = field(metadata = {'args': ['required_string'], 'help': 'a required string'})
    input_file: str = field(metadata = {'args': ['-i', '--input-file'], 'help': 'input file', 'metavar': 'INFILE', 'group': 'IO arguments'})
    output_file: str = field(metadata = {'args': ['-o', '--output-file'], 'help': 'output file', 'metavar': 'OUTFILE', 'group': 'IO arguments'})
    choice: str = field(default = 'a', metadata = {'choices': ['a', 'b', 'c'], 'help': 'one of three choices'})
    optional: str = field(default = 'default', metadata = {'nargs': '?', 'const': 'unspecified', 'help': 'optional argument'})
    flag: bool = field(default = False, metadata = {'help': 'activate flag'})
    extra_items: List[str] = field(default_factory = list, metadata = {'nargs': '*', 'help': 'list of extra items'})
    x: int = field(default = 7, metadata = {'help': 'x value', 'group': 'numeric arguments'})
    y: float = field(default = 3.14, metadata = {'help': 'y value', 'group': 'numeric arguments'})
    pair: Tuple[int, int] = field(default = (0, 0), metadata = {'nargs': 2, 'metavar': ('FIRST', 'SECOND'), 'help': 'pair of integers', 'group': 'numeric arguments'})
    ignored_value: str = field(default = 'ignored', metadata = {'parse_exclude': True, 'subprocess_exclude': True})

    @classmethod
    def parser_kwargs(cls) -> Dict[str, Any]:
        return {**super().parser_kwargs(), 'formatter_class': ArgumentDefaultsHelpFormatter}

    def run(self) -> None:
        print(self)

def test_argparse_dataclass_help():
    """Tests equivalence of argparse-generated help string between an ArgparseDataclass and building the parser manually."""
    parser = ArgumentParser(description = DC1.__doc__, formatter_class = ArgumentDefaultsHelpFormatter)
    parser.add_argument('required_string', help = 'a required string')
    io_group = parser.add_argument_group('IO arguments')
    io_group.add_argument('-i', '--input-file', required = True, metavar = 'INFILE', help = 'input file')
    io_group.add_argument('-o', '--output-file', required = True, metavar = 'OUTFILE', help = 'output file')
    parser.add_argument('--choice', default = 'a', choices = ['a', 'b', 'c'], help = 'one of three choices')
    parser.add_argument('--optional', nargs = '?', default = 'default', const = 'unspecified', help = 'optional argument')
    parser.add_argument('--flag', action = 'store_true', help = 'activate flag')
    parser.add_argument('--extra-items', nargs = '*', default = [], help = 'list of extra items')
    num_group = parser.add_argument_group('numeric arguments')
    num_group.add_argument('-x', type = int, default = 7, help = 'x value')
    num_group.add_argument('-y', type = float, default = 3.14, help = 'y value')
    num_group.add_argument('--pair', type = int, nargs = 2, default = (0, 0), metavar = ('FIRST', 'SECOND'), help = 'pair of integers')
    dc1_parser = DC1.make_parser()
    assert parser.format_help() == dc1_parser.format_help()

def test_cli_dataclass_parse_valid(capsys):
    """Tests that an CLIDataclass properly parses command-line arguments."""
    def _check_equivalent(args, obj):
        # take args directly
        obj1 = DC1.from_cli_args(args)
        assert obj1 == obj
        # implicitly take args from sys.argv
        argv = sys.argv[1:]
        sys.argv[1:] = args
        assert obj1 == obj
        # build parser and parse command-line args from sys.argv
        DC1.main()
        # since 'run' function prints the object, it should match
        captured = capsys.readouterr()
        assert captured.out.rstrip() == str(obj)
        sys.argv[1:] = argv
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output']
    obj = DC1(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='a', optional='default', extra_items=[], x=7, y=3.14, pair=(0,0), ignored_value='ignored')
    _check_equivalent(args, obj)
    args = ['positional_arg', '-x', '100', '-i', 'my_input', '-o', 'my_output', '--choice', 'b', '--flag', '--optional', '--extra-items', '1', '2', '3']
    obj = DC1(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='b', flag=True, optional='unspecified', extra_items=['1', '2', '3'], x=100, y=3.14, pair=(0,0), ignored_value='ignored')
    _check_equivalent(args, obj)
    args = ['positional_arg', '-x', '100', '-i', 'my_input', '-o', 'my_output', '--choice', 'b', '--optional', 'thing', '--extra-items', '1', '2', '3']
    obj = DC1(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='b', optional='thing', extra_items=['1', '2', '3'], x=100, y=3.14, pair=(0,0), ignored_value='ignored')
    _check_equivalent(args, obj)
    args = ['positional_arg', '-x', '100', '-i', 'my_input', '-o', 'my_output', '--optional', '--extra-items', '1', '2', '3', '--pair', '10', '20']
    obj = DC1(required_string='positional_arg', input_file='my_input', output_file='my_output', choice='a', optional='unspecified', extra_items=['1', '2', '3'], x=100, y=3.14, pair=(10,20), ignored_value='ignored')
    _check_equivalent(args, obj)

def test_cli_dataclass_parse_invalid(capsys):
    """Tests that a CLIDataclass errors on invalid command-line arguments."""
    def _check_invalid(args):
        with pytest.raises(SystemExit):
            DC1.from_cli_args(args)
    # missing required option
    args = ['positional_arg', '-i', 'my_input']
    _check_invalid(args)
    # missing required positional argument
    args = ['-i', 'my_input', '-o', 'my_output']
    _check_invalid(args)
    # can't parse positional argument at the end of argument list
    args = ['-i', 'my_input', '-o', 'my_output', '--extra-items', 'a', 'b', 'positional_arg']
    _check_invalid(args)
    # invalid type for integer argument
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '-x', 'a']
    _check_invalid(args)
    # invalid choice
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '--choice', 'd']
    _check_invalid(args)
