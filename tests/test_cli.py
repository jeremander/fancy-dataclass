from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, _SubParsersAction
from dataclasses import dataclass, field
import re
import sys
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import pytest

from fancy_dataclass.cli import ArgparseDataclass, CLIDataclass


def _fix_parser(parser):
    """Prevent parser from issuing SystemExit, and instead have it issue ValueError."""
    def _error(msg):
        raise ValueError(msg)
    def _print_help(parser):
        def _raise_help():
            raise ValueError(parser.format_help())
        return _raise_help
    parser.error = _error
    parser.print_help = _print_help(parser)
    for action in getattr(parser._subparsers, '_actions', []):
        if isinstance(action, _SubParsersAction):
            for subparser in action.choices.values():
                _fix_parser(subparser)
    return parser

def check_invalid_args(cls, args, match=None):
    assert match, 'must provide an error pattern'
    parser = _fix_parser(cls.make_parser())
    with pytest.raises(ValueError, match=re.compile(match, re.DOTALL)):
        parser.parse_args(args=args)


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

def test_cli_dataclass_parse_invalid():
    """Tests that a CLIDataclass errors on invalid command-line arguments."""
    # missing required option
    args = ['positional_arg', '-i', 'my_input']
    check_invalid_args(DC1, args, 'required: -o/--output-file')
    # missing required positional argument
    args = ['-i', 'my_input', '-o', 'my_output']
    check_invalid_args(DC1, args, 'required: required_string')
    # can't parse positional argument at the end of argument list
    args = ['-i', 'my_input', '-o', 'my_output', '--extra-items', 'a', 'b', 'positional_arg']
    check_invalid_args(DC1, args, 'required: required_string')
    # invalid type for integer argument
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '-x', 'a']
    check_invalid_args(DC1, args, "invalid int value: 'a'")
    # invalid choice
    args = ['positional_arg', '-i', 'my_input', '-o', 'my_output', '--choice', 'd']
    check_invalid_args(DC1, args, "invalid choice: 'd'")

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
        check_invalid_args(cls, ['--pos', '1'], 'unrecognized arguments: --pos')
    # required option (no default value)
    @dataclass
    class DC4(ArgparseDataclass):
        opt: int = field(metadata={'args': '--opt'})
    @dataclass
    class DC5(ArgparseDataclass):
        opt: int = field(metadata={'args': ['-o', '--opt']})
    for cls in [DC4, DC5]:
        assert cls.from_cli_args(['--opt', '1']).opt == 1
        check_invalid_args(cls, ['--opt'], 'expected one argument')
        check_invalid_args(cls, ['--opt', 'a'], "invalid int value: 'a'")
    for args in [['1'], ['-o', '1'], ['-opt', '1']]:
        check_invalid_args(DC4, args, 'required: --opt')
    check_invalid_args(DC5, ['-opt', '1'], "invalid int value: 'pt'")
    check_invalid_args(DC5, ['1'], 'required: -o/--opt')
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
        check_invalid_args(cls, ['--opt'], 'expected one argument')
        check_invalid_args(cls, ['-o', '1'], 'unrecognized arguments')
        check_invalid_args(cls, ['1'], 'unrecognized arguments')
    @dataclass
    class DC8(ArgparseDataclass):
        opt: int = field(default=42, metadata={'args': '--other'})
    assert DC8.from_cli_args(['--other', '1']).opt == 1
    assert DC8.from_cli_args([]).opt == 42
    check_invalid_args(DC8, ['--opt', '1'], 'unrecognized arguments')
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
    for cls in [DC10, DC11]:
        assert cls.from_cli_args(['--flag']).flag is True
        assert cls.from_cli_args([]).flag is False
    @dataclass
    class DC12(ArgparseDataclass):
        flag: bool = field(default=True, metadata={'action': 'store_false'})
    assert DC12.from_cli_args(['--flag']).flag is False
    assert DC12.from_cli_args([]).flag is True
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
    check_invalid_args(DC14, ['--opt', '1'], 'unrecognized arguments')
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
    check_invalid_args(DC16, ['1', 'a'], "invalid int value: 'a'")
    check_invalid_args(DC16, ['--vals', '1'], 'unrecognized arguments')
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
        check_invalid_args(cls, ['--vals', '1', 'a'], "invalid int value: 'a'")
    assert DC17.from_cli_args(['--vals']).vals == []
    check_invalid_args(DC18, ['--vals'], 'at least one argument')
    # nontrivial union types not permitted
    @dataclass
    class DC19(ArgparseDataclass):
        pos: Union[int, str]
    with pytest.raises(ValueError, match='union type .+ not allowed'):
        _ = DC19.make_parser()
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
        check_invalid_args(cls, [], 'required: choice')
        check_invalid_args(cls, ['a'], "invalid int value: 'a'")
        check_invalid_args(cls, ['0'], 'invalid choice: 0')
    @dataclass
    class DC23(ArgparseDataclass):
        choice: Literal[1, 'a']
    assert DC23.from_cli_args(['1']).choice == 1
    # not flexible enough to handle mixed types
    check_invalid_args(DC23, ['a'], "invalid int value: 'a'")
    # integer nargs
    @dataclass
    class DC24(ArgparseDataclass):
        vals: List[int] = field(metadata={'nargs': 2})
    assert DC24.from_cli_args(['1', '2']).vals == [1, 2]
    check_invalid_args(DC24, [], 'required: vals')
    check_invalid_args(DC24, ['1'], 'required: vals')
    check_invalid_args(DC24, ['1', 'a'], "invalid int value: 'a'")
    check_invalid_args(DC24, ['1', '2', '3'], 'unrecognized arguments: 3')
    # custom type constructor
    @dataclass
    class DC25(ArgparseDataclass):
        x: int = field(metadata={'type': lambda x: int(x) + 1})
    assert DC25.from_cli_args(['1']).x == 2

def test_groups():
    """Tests the behavior of groups and nested groups."""
    # basic group
    @dataclass
    class DCGroup1(ArgparseDataclass):
        """Docstring for DCGroup1."""
        x: int = field(metadata={'group': 'xy group'})
        y: int = field(default=2, metadata={'help': 'y value', 'group': 'xy group'})
    help_str = DCGroup1.make_parser().format_help()
    assert DCGroup1.__doc__ in help_str
    assert re.search(r'xy group:\s+x\s+-y Y\s+y value', help_str)
    assert DCGroup1.from_cli_args(['1']) == DCGroup1(1, 2)
    # basic group with nested ArgparseDataclass
    @dataclass
    class DCGroupXY(ArgparseDataclass):
        """Docstring for DCGroupXY."""
        x: int
        y: int = field(default=2, metadata={'help': 'y value'})
    @dataclass
    class DCGroup2(ArgparseDataclass):
        """Docstring for DCGroup2."""
        xy: DCGroupXY = field(metadata={'help': 'group for x and y', 'group': 'xy group'})
    help_str = DCGroup2.make_parser().format_help()
    assert DCGroup2.__doc__ in help_str
    assert re.search(r'xy group:\s+Docstring for DCGroupXY\.\s+x\s+-y Y\s+y value', help_str)
    assert DCGroup2.from_cli_args(['1']).xy == DCGroupXY(1, 2)
    # doubly nested group (not allowed)
    @dataclass
    class DCGroupWXY1(ArgparseDataclass):
        w: str
        xy: DCGroupXY = field(metadata={'group': 'xy group'})
    @dataclass
    class DCGroup3(ArgparseDataclass):
        wxy: DCGroupWXY1 = field(metadata={'group': 'wxy group'})
    with pytest.raises(ValueError, match='nested argument groups are not allowed'):
        _ = DCGroup3.make_parser()
    # group with nested ArgparseDataclass is OK
    @dataclass
    class DCGroupWXY2(ArgparseDataclass):
        w: str = field(metadata={'help': 'w value'})
        xy: DCGroupXY
    @dataclass
    class DCGroup4(ArgparseDataclass):
        wxy: DCGroupWXY2 = field(metadata={'group': 'wxy group'})
    help_str = DCGroup4.make_parser().format_help()
    assert re.search('wxy group', help_str)
    assert re.search(r'w\s+w value\s+x\s+-y Y\s+y value', help_str)

def test_exclusive_groups():
    """Tests the behavior of exclusive groups and nested exclusive groups."""
    # basic exclusive group
    @dataclass
    class DCExcGroup1(ArgparseDataclass):
        """Docstring."""
        x: int = field(default=1, metadata={'exclusive_group': 'xy group'})
        y: int = field(default=2, metadata={'help': 'y value', 'exclusive_group': 'xy group'})
    help_str = DCExcGroup1.make_parser().format_help()
    assert DCExcGroup1.__doc__ in help_str
    assert re.search(r'-x X\s+-y Y\s+y value', help_str)
    # exclusive group does not appear as a distinct group in the help
    assert 'xy group' not in help_str
    assert DCExcGroup1.from_cli_args([]) == DCExcGroup1(1, 2)
    assert DCExcGroup1.from_cli_args(['-x', '101']) == DCExcGroup1(101, 2)
    check_invalid_args(DCExcGroup1, ['-x', '101', '-y', '102'], 'not allowed with argument -x')
    # field can't be part of both a group and an exclusive group
    @dataclass
    class DCExcGroup2(ArgparseDataclass):
        x: int = field(default=1, metadata={'group': 'xy group', 'exclusive_group': 'exc'})
        y: int = field(default=2, metadata={'group': 'xy group', 'exclusive_group': 'exc'})
    with pytest.raises(ValueError, match='both group and exclusive_group'):
        _ = DCExcGroup2.make_parser()
    # exclusive group arguments must be optional
    @dataclass
    class DCExcGroup3(ArgparseDataclass):
        x: int = field(metadata={'exclusive_group': 'group'})
    with pytest.raises(ValueError, match='must be optional'):
        _ = DCExcGroup3.make_parser()
    # exclusive group with nested ArgparseDataclass
    @dataclass
    class DCExcGroupXY(ArgparseDataclass):
        x: int = field(default=1)
        y: int = field(default=2, metadata={'help': 'y value'})
    @dataclass
    class DCExcGroup4(ArgparseDataclass):
        """Docstring."""
        xy: DCExcGroupXY = field(metadata={'help': 'group for x and y', 'exclusive_group': 'xy group'})
    assert DCExcGroup4.make_parser().format_help() == DCExcGroup1.make_parser().format_help()
    assert DCExcGroup4.from_cli_args(['-x', '101']).xy == DCExcGroupXY(101, 2)
    check_invalid_args(DCExcGroup4, ['-x', '101', '-y', '102'], 'not allowed with argument -x')
    # doubly nested exclusive group (not allowed)
    @dataclass
    class DCExcGroupWXY1(ArgparseDataclass):
        xy: DCExcGroupXY = field(metadata={'exclusive_group': 'xy group'})
        w: str = field(default='w', metadata={'help': 'w value'})
    @dataclass
    class DCExcGroup5(ArgparseDataclass):
        wxy: DCExcGroupWXY1 = field(metadata={'exclusive_group': 'wxy group'})
    with pytest.raises(ValueError, match='nested exclusive groups are not allowed'):
        _ = DCExcGroup5.make_parser()
    # exclusive group with nested ArgparseDataclass is OK
    @dataclass
    class DCExcGroupWXY2(ArgparseDataclass):
        xy: DCExcGroupXY
        w: str = field(default='w', metadata={'help': 'w value'})
    @dataclass
    class DCExcGroup6(ArgparseDataclass):
        wxy: DCExcGroupWXY2 = field(metadata={'exclusive_group': 'wxy group'})
    help_str = DCExcGroup6.make_parser().format_help()
    assert re.search(r'x X\s+-y Y\s+y value\s+-w W\s+w value', help_str)
    assert 'wxy group' not in help_str
    assert DCExcGroup6.from_cli_args(['-w', '100']).wxy == DCExcGroupWXY2(DCExcGroupXY(1, 2), '100')
    check_invalid_args(DCExcGroup6, ['-x', '101', '-y', '102'], 'not allowed with argument -x')
    check_invalid_args(DCExcGroup6, ['-w', '100', '-x', '101'], 'not allowed with argument -w')
    # exclusive group within a regular group (OK)
    @dataclass
    class DCExcGroup7(ArgparseDataclass):
        wxy: DCExcGroupWXY1 = field(metadata={'group': 'wxy group'})
    help_str = DCExcGroup7.make_parser().format_help()
    assert 'wxy group' in help_str
    assert re.search(r'-x X\s+-y Y\s+y value\s+-w W\s+w value', help_str)
    assert DCExcGroup7.from_cli_args(['-w', '100', '-x', '101']).wxy == DCExcGroupWXY1(DCExcGroupXY(101, 2), '100')
    check_invalid_args(DCExcGroup7, ['-x', '101', '-y', '102'], 'not allowed with argument -x')
    # regular group within an exclusive group (not allowed)
    @dataclass
    class DCGroupWXY(ArgparseDataclass):
        xy: DCExcGroupXY = field(metadata={'group': 'xy group'})
        w: str = field(default='w', metadata={'help': 'w value'})
    @dataclass
    class DCExcGroup8(ArgparseDataclass):
        wxy: DCGroupWXY = field(metadata={'exclusive_group': 'wxy group'})
    # an exclusive group is a group, so cannot have a nested group within it
    with pytest.raises(ValueError, match='nested argument groups are not allowed'):
        _ = DCExcGroup8.make_parser()

def test_nested():
    """Tests the behavior of nested ArgparseDataclasses."""
    @dataclass
    class X(ArgparseDataclass):
        x: int
    @dataclass
    class A(ArgparseDataclass):
        vals: List[X]
    # list of nested ArgparseDataclass not allowed
    with pytest.raises(ValueError, match='list of X not allowed'):
        _ = A.make_parser()
    @dataclass
    class XY(ArgparseDataclass):
        x: int
        y: int
    @dataclass
    class B(ArgparseDataclass):
        val: XY
    # nested fields get added to parser
    assert B.from_cli_args(['1', '2']) == B(XY(1, 2))
    @dataclass
    class C(ArgparseDataclass):
        vals: List[XY]
    with pytest.raises(ValueError, match='list of XY not allowed'):
        _ = C.make_parser()
    # optional type OK
    @dataclass
    class D(ArgparseDataclass):
        val: Optional[X]
    help_str = D.make_parser().format_help()
    # x is a positional arg even though it is optional, because the inner class makes it positional
    # TODO: should this be changed?
    assert re.search(r'positional arguments:\s+x\s+', help_str)
    assert D.from_cli_args(['1']) == D(X(1))
    check_invalid_args(D, [], 'arguments are required: x')
    @dataclass
    class E(ArgparseDataclass):
        val: Union[None, X]
    help_str = E.make_parser().format_help()
    assert re.search(r'positional arguments:\s+x\s+', help_str)
    assert E.from_cli_args(['1']) == E(X(1))
    check_invalid_args(E, [], 'arguments are required: x')
    # duplicate positional args
    @dataclass
    class F(ArgparseDataclass):
        val1: Optional[X]
        val2: Union[None, X]
    with pytest.raises(ValueError, match="duplicate positional argument 'x'"):
        _ = F.make_parser()
    # nontrivial union not permitted
    @dataclass
    class G(ArgparseDataclass):
        val: Union[str, X]
    with pytest.raises(ValueError, match='union type .+ not allowed'):
        _ = G.make_parser()
    @dataclass
    class H(ArgparseDataclass):
        val: Union[X, XY]
    with pytest.raises(ValueError, match='union type .+ not allowed'):
        _ = H.make_parser()

def test_subcommand(capsys):
    """Tests the behavior of subcommands."""
    @dataclass
    class Sub1(CLIDataclass):
        """First subcommand"""
        x1: int
        y1: int
        def run(self) -> None:
            print(self.__class__.__name__)
    assert Sub1.__settings__.command_name == 'sub1'
    assert Sub1._subcommand_field_name is None
    assert Sub1(1, 2).subcommand is None
    @dataclass
    class Sub2(ArgparseDataclass, command_name='my-subcommand'):
        """Second subcommand"""
        x2: int
        y2: str = 'abc'
    assert Sub2.__settings__.command_name == 'my-subcommand'
    assert Sub2._subcommand_field_name is None
    assert Sub2(1, 2).subcommand is None
    # multiple subcommands not allowed
    with pytest.raises(TypeError, match='multiple fields .* registered as subcommands'):
        @dataclass
        class DCSub1(ArgparseDataclass):
            sub1: Sub1 = field(metadata={'subcommand': True})
            sub2: Sub2 = field(metadata={'subcommand': True})
    # subcommand must be ArgparseDataclass or union thereof
    with pytest.raises(TypeError, match='type must be an ArgparseDataclass or Union thereof'):
        @dataclass
        class DCSub2(ArgparseDataclass):
            x: int = field(metadata={'subcommand': True})
    with pytest.raises(TypeError, match='type must be an ArgparseDataclass or Union thereof'):
        @dataclass
        class DCSub3(ArgparseDataclass):
            x: Union[Sub1, int] = field(metadata={'subcommand': True})
    # simple subcommand
    @dataclass
    class DCSub4(ArgparseDataclass):
        sub1: Sub1 = field(metadata={'subcommand': True})
        x: int = field(metadata={'help': 'x value'})  # positional arg in addition to subparser is allowed, though it's weird
        y: int = 2
    assert DCSub4.__settings__.command_name == 'dc-sub4'
    assert DCSub4._subcommand_field_name == 'sub1'
    assert DCSub4(Sub1(1, 2), 1).subcommand == 'sub1'
    help_str = DCSub4.make_parser().format_help()
    assert re.search(r'positional arguments:.+sub1\s+First subcommand\s+x\s+x value\s+option.+-y Y', help_str, re.DOTALL)
    check_invalid_args(DCSub4, [], 'the following arguments are required: subcommand, x')
    check_invalid_args(DCSub4, ['5'], "invalid choice: '5'")
    for args in [['sub1'], ['sub1', '1']]:
        check_invalid_args(DCSub4, args, 'the following arguments are required: x1, y1')
    check_invalid_args(DCSub4, ['sub1', '1', '2'], 'the following arguments are required: y1')
    check_invalid_args(DCSub4, ['sub1', '1', '2', 'a'], "argument x: invalid int value: 'a'")
    assert DCSub4.from_cli_args(['sub1', '1', '2', '5']) == DCSub4(Sub1(1, 2), 5)
    # union subcommand
    @dataclass
    class DCSub5(CLIDataclass):
        sub: Union[Sub1, Sub2] = field(metadata={'subcommand': True, 'help': 'choose a subcommand'})
        x: int = 1
    assert DCSub5.__settings__.command_name == 'dc-sub5'
    assert DCSub5._subcommand_field_name == 'sub'
    assert DCSub5(Sub1(1, 2)).subcommand == 'sub1'
    assert DCSub5(Sub2(1, 2)).subcommand == 'my-subcommand'
    help_str = DCSub5.make_parser().format_help()
    assert re.search(r'positional arguments:.+choose a subcommand\s+sub1\s+First subcommand\s+my-subcommand\s+Second subcommand.+-x X', help_str, re.DOTALL)
    for args in [[], ['-x', '5']]:
        check_invalid_args(DCSub5, args, 'the following arguments are required: subcommand')
    check_invalid_args(DCSub5, ['sub1'], 'required: x1, y1')
    check_invalid_args(DCSub5, ['sub1', '1'], 'required: y1')
    check_invalid_args(DCSub5, ['sub1', '1', '2', '3'], 'unrecognized arguments: 3')
    check_invalid_args(DCSub5, ['sub2'], "invalid choice: 'sub2'")
    check_invalid_args(DCSub5, ['my-subcommand'], 'required: x2')
    assert DCSub5.from_cli_args(['sub1', '1', '2']) == DCSub5(Sub1(1, 2))
    # parent parser's options must come before subparser invocation
    assert DCSub5.from_cli_args(['-x', '5', 'sub1', '1', '2']) == DCSub5(Sub1(1, 2), 5)
    check_invalid_args(DCSub5, ['sub1', '1', '2', '-x', '5'], 'unrecognized arguments: -x 5')
    assert DCSub5.from_cli_args(['my-subcommand', '1']) == DCSub5(Sub2(1, 'abc'))
    assert DCSub5.from_cli_args(['-x', '5', 'my-subcommand', '1', '--y2', 'def']) == DCSub5(Sub2(1, 'def'), 5)
    # default implementation of `CLIDataclass.run`
    DCSub5.main(['sub1', '1', '2'])
    assert capsys.readouterr().out == 'Sub1\n'
    with pytest.raises(NotImplementedError):
        DCSub5.main(['my-subcommand', '1'])
    # duplicate subcommand name
    @dataclass
    class Sub3(ArgparseDataclass, command_name='sub1'):
        ...
    with pytest.raises(TypeError, match="duplicate command name 'sub1' in subcommand field 'sub'"):
        @dataclass
        class DCSub6(ArgparseDataclass):
            sub: Union[Sub1, Sub3] = field(metadata={'subcommand': True})
    # empty argument set is OK
    @dataclass
    class DCSub7(ArgparseDataclass):
        sub: Sub3 = field(metadata={'subcommand': True})
    check_invalid_args(DCSub7, [], 'the following arguments are required: subcommand')
    check_invalid_args(DCSub7, ['sub'], 'invalid choice')
    assert DCSub7.from_cli_args(['sub1']) == DCSub7(Sub3())
    # subparser with group
    @dataclass
    class Sub4(ArgparseDataclass):
        """Fourth subcommand"""
        x: int = field(metadata={'group': 'number group'})
        y: int = field(metadata={'group': 'number group'})
    @dataclass
    class DCSub8(ArgparseDataclass):
        sub: Sub4 = field(metadata={'subcommand': True})
    # check the subparser's help string
    check_invalid_args(DCSub8, ['sub4', '-h'], r'-h, --help.*number group:\s+x\s+y')

def test_boolean_flag():
    """Tests the behavior of boolean fields in an ArgparseDataclass."""
    @dataclass
    class DCFlagDefaultFalse(ArgparseDataclass):
        flag: bool = False
    @dataclass
    class DCFlagNoDefault(ArgparseDataclass):
        flag: bool
    # required=True is ignored for boolean flag
    @dataclass
    class DCFlagRequired(ArgparseDataclass):
        flag: bool = field(default=False, metadata={'required': True})
    for cls in [DCFlagDefaultFalse, DCFlagNoDefault, DCFlagRequired]:
        assert cls.from_cli_args([]).flag is False
        assert cls.from_cli_args(['--flag']).flag is True
    # default of True not permitted with action='store_true' (the default)
    @dataclass
    class DCFlagDefaultTrue(ArgparseDataclass):
        flag: bool = True
    with pytest.raises(ValueError, match='cannot use default value of True'):
        _ = DCFlagDefaultTrue.make_parser()
    @dataclass
    class DCFlagDefaultTrueActionFalse(ArgparseDataclass):
        flag: bool = field(default=True, metadata={'action': 'store_false'})
    assert DCFlagDefaultTrueActionFalse.from_cli_args([]).flag is True
    assert DCFlagDefaultTrueActionFalse.from_cli_args(['--flag']).flag is False
    # default of False not permitted with action='store_false'
    @dataclass
    class DCFlagDefaultFalseActionFalse(ArgparseDataclass):
        flag: bool = field(default=False, metadata={'action': 'store_false'})
    with pytest.raises(ValueError, match='cannot use default value of False'):
        _ = DCFlagDefaultFalseActionFalse.make_parser()
    # action must be 'store_true' or 'store_false'
    @dataclass
    class DCFlagActionStore(ArgparseDataclass):
        flag: bool = field(default=False, metadata={'action': 'store'})
    with pytest.raises(ValueError, match="invalid action 'store'"):
        _ = DCFlagActionStore.make_parser()
