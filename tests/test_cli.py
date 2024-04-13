from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from dataclasses import dataclass, field
import sys
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import pytest

from fancy_dataclass.cli import ArgparseDataclass, CLIDataclass


@dataclass
class DC1(CLIDataclass):
    """An example of CLIDataclass."""
    required_string: str = field(metadata={'args': ['required_string'], 'help': 'a required string'})
    input_file: str = field(metadata={'args': ['-i', '--input-file'], 'help': 'input file', 'metavar': 'INFILE', 'group': 'IO arguments'})
    output_file: str = field(metadata={'args': ['-o', '--output-file'], 'help': 'output file', 'metavar': 'OUTFILE', 'group': 'IO arguments'})
    choice: str = field(default='a', metadata={'choices': ['a', 'b', 'c'], 'help': 'one of three choices'})
    optional: str = field(default='default', metadata={'nargs': '?', 'const': 'unspecified', 'help': 'optional argument'})
    flag: bool = field(default=False, metadata={'help': 'activate flag'})
    extra_items: List[str] = field(default_factory=list, metadata={'nargs': '*', 'help': 'list of extra items'})
    x: int = field(default=7, metadata={'help': 'x value', 'group': 'numeric arguments'})
    y: float = field(default=3.14, metadata={'help': 'y value', 'group': 'numeric arguments'})
    pair: Tuple[int, int] = field(default=(0, 0), metadata={'nargs': 2, 'metavar': ('FIRST', 'SECOND'), 'help': 'pair of integers', 'group': 'numeric arguments'})
    ignored_value: str = field(default='ignored', metadata={'args': [], 'parse_exclude': True})

    @classmethod
    def parser_kwargs(cls) -> Dict[str, Any]:
        return {**super().parser_kwargs(), 'formatter_class': ArgumentDefaultsHelpFormatter}

    def run(self) -> None:
        print(self)

def test_argparse_dataclass_help():
    """Tests equivalence of argparse-generated help string between an ArgparseDataclass and building the parser manually."""
    parser = ArgumentParser(description=DC1.__doc__, formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('required_string', help='a required string')
    io_group = parser.add_argument_group('IO arguments')
    io_group.add_argument('-i', '--input-file', required=True, metavar='INFILE', help='input file')
    io_group.add_argument('-o', '--output-file', required=True, metavar='OUTFILE', help='output file')
    parser.add_argument('--choice', default='a', choices=['a', 'b', 'c'], help='one of three choices')
    parser.add_argument('--optional', nargs='?', default='default', const='unspecified', help='optional argument')
    parser.add_argument('--flag', action='store_true', help='activate flag')
    parser.add_argument('--extra-items', nargs='*', default=[], help='list of extra items')
    num_group = parser.add_argument_group('numeric arguments')
    num_group.add_argument('-x', type=int, default=7, help='x value')
    num_group.add_argument('-y', type=float, default=3.14, help='y value')
    num_group.add_argument('--pair', type=int, nargs=2, default=(0, 0), metavar=('FIRST', 'SECOND'), help='pair of integers')
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

def check_invalid_args(cls, args):
    with pytest.raises(SystemExit):
        cls.from_cli_args(args)

def test_cli_dataclass_parse_invalid():
    """Tests that a CLIDataclass errors on invalid command-line arguments."""
    # missing required option
    args = ['positional_arg', '-i', 'my_input']
    check_invalid_args(DC1, args)
    # missing required positional argument
    args = ['-i', 'my_input', '-o', 'my_output']
    check_invalid_args(DC1, args)
    # can't parse positional argument at the end of argument list
    args = ['-i', 'my_input', '-o', 'my_output', '--extra-items', 'a', 'b', 'positional_arg']
    check_invalid_args(DC1, args)
    # invalid type for integer argument
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '-x', 'a']
    check_invalid_args(DC1, args)
    # invalid choice
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '--choice', 'd']
    check_invalid_args(DC1, args)

def test_argparse_options():
    """Tests the behavior of various argparse options."""
    # explicit positional argument
    @dataclass
    class DC2(ArgparseDataclass):
        pos: int = field(metadata={'args': 'pos'})
    # implicit positional argument
    @dataclass
    class DC3(ArgparseDataclass):
        pos: int
    for cls in [DC2, DC3]:
        assert cls.from_cli_args(['1']).pos == 1
        check_invalid_args(cls, ['--pos', '1'])
    # required option (no default value)
    @dataclass
    class DC4(ArgparseDataclass):
        opt: int = field(metadata={'args': '--opt'})
    @dataclass
    class DC5(ArgparseDataclass):
        opt: int = field(metadata={'args': ['-o', '--opt']})
    for cls in [DC4, DC5]:
        assert cls.from_cli_args(['--opt', '1']).opt == 1
        check_invalid_args(cls, ['--opt'])
        check_invalid_args(cls, ['--opt', 'a'])
        check_invalid_args(cls, ['-opt', '1'])
        check_invalid_args(cls, ['1'])
    check_invalid_args(DC4, ['-o', '1'])
    assert DC5.from_cli_args(['-o', '1']).opt == 1
    # optional option
    @dataclass
    class DC6(ArgparseDataclass):
        opt: int = 42
    @dataclass
    class DC7(ArgparseDataclass):
        opt: int = field(default=42)
    for cls in [DC6, DC7]:
        assert cls.from_cli_args(['--opt', '1']).opt == 1
        assert cls.from_cli_args([]).opt == 42
        check_invalid_args(cls, ['--opt'])
        check_invalid_args(cls, ['-o', '1'])
        check_invalid_args(cls, ['1'])
    @dataclass
    class DC8(ArgparseDataclass):
        opt: int = field(default=42, metadata={'args': '--other'})
    assert DC8.from_cli_args(['--other', '1']).opt == 1
    assert DC8.from_cli_args([]).opt == 42
    check_invalid_args(DC8, ['--opt', '1'])
    # optional option (Optional)
    @dataclass
    class DC9(ArgparseDataclass):
        opt: Optional[int]
    assert DC9.from_cli_args(['--opt', '1']).opt == 1
    assert DC9.from_cli_args([]).opt is None
    # boolean flag
    @dataclass
    class DC10(ArgparseDataclass):
        flag: bool
    @dataclass
    class DC11(ArgparseDataclass):
        flag: bool = False
    @dataclass
    class DC12(ArgparseDataclass):
        flag: bool = True
    for cls in [DC10, DC11, DC12]:
        assert cls.from_cli_args(['--flag']).flag is True
        assert cls.from_cli_args([]).flag is (cls is DC12)
    @dataclass
    class DC13(ArgparseDataclass):
        flag: bool = field(metadata={'action': 'store_false'})
    assert DC13.from_cli_args(['--flag']).flag is False
    assert DC13.from_cli_args([]).flag is True
    # store_const
    @dataclass
    class DC14(ArgparseDataclass):
        opt: Optional[int] = field(metadata={'action': 'store_const', 'const': 123})
    assert DC14.from_cli_args(['--opt']).opt == 123
    assert DC14.from_cli_args([]).opt is None
    check_invalid_args(DC14, ['--opt', '1'])
    # nargs='?' with const
    @dataclass
    class DC15(ArgparseDataclass):
        opt: Optional[int] = field(metadata={'nargs': '?', 'const': 123})
    assert DC15.from_cli_args(['--opt', '1']).opt == 1
    assert DC15.from_cli_args(['--opt']).opt == 123
    assert DC15.from_cli_args([]).opt is None
    # positional list
    @dataclass
    class DC16(ArgparseDataclass):
        vals: List[int]
    assert DC16.from_cli_args([]).vals == []
    assert DC16.from_cli_args(['1', '2']).vals == [1, 2]
    check_invalid_args(DC16, ['1', 'a'])
    check_invalid_args(DC16, ['--vals', '1'])
    # optional list
    @dataclass
    class DC17(ArgparseDataclass):
        vals: List[int] = field(default_factory=list)
    @dataclass
    class DC18(ArgparseDataclass):
        vals: List[int] = field(default_factory=list, metadata={'nargs': '+'})
    for cls in [DC17, DC18]:
        assert cls.from_cli_args([]).vals == []
        assert cls.from_cli_args(['--vals', '1']).vals == [1]
        assert cls.from_cli_args(['--vals', '1', '2']).vals == [1, 2]
        check_invalid_args(cls, ['--vals', '1', 'a'])
    assert DC17.from_cli_args(['--vals']).vals == []
    check_invalid_args(DC18, ['--vals'])
    # argparse not flexible enough to handle union types
    @dataclass
    class DC19(ArgparseDataclass):
        pos: Union[int, str]
    assert DC19.from_cli_args(['7']).pos == 7
    check_invalid_args(DC19, ['a'])
    check_invalid_args(DC19, [])
    # append action
    @dataclass
    class DC20(ArgparseDataclass):
        vals: List[int] = field(default_factory=list, metadata={'action': 'append'})
    assert DC20.from_cli_args([]).vals == []
    assert DC20.from_cli_args(['--vals', '1']).vals == [1]
    assert DC20.from_cli_args(['--vals', '1', '--vals', '2']).vals == [1, 2]
    # abbrevation works
    assert DC20.from_cli_args(['--val', '1', '--vals', '2']).vals == [1, 2]
    # choices
    @dataclass
    class DC21(ArgparseDataclass):
        choice: int = field(metadata={'choices': (1, 2)})
    @dataclass
    class DC22(ArgparseDataclass):
        choice: Literal[1, 2]
    for cls in [DC21, DC22]:
        assert cls.from_cli_args(['1']).choice == 1
        check_invalid_args(cls, [])
        check_invalid_args(cls, ['a'])
        check_invalid_args(cls, ['0'])  # invalid choice
    @dataclass
    class DC23(ArgparseDataclass):
        choice: Literal[1, 'a']
    assert DC23.from_cli_args(['1']).choice == 1
    # not flexible enough to handle mixed types
    check_invalid_args(DC23, ['a'])
    # integer nargs
    @dataclass
    class DC24(ArgparseDataclass):
        vals: List[int] = field(metadata={'nargs': 2})
    assert DC24.from_cli_args(['1', '2']).vals == [1, 2]
    check_invalid_args(DC24, [])
    check_invalid_args(DC24, ['1'])
    check_invalid_args(DC24, ['1', 'a'])
    check_invalid_args(DC24, ['1', '2', '3'])
