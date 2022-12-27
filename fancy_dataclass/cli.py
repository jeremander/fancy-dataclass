from abc import abstractmethod
from argparse import ArgumentParser, Namespace
from contextlib import suppress
import dataclasses
from enum import IntEnum
from typing import Any, ClassVar, Dict, List, Optional, Type, TypeVar

from fancy_dataclass.dict import DictDataclass
from fancy_dataclass.utils import check_dataclass, issubclass_safe, obj_class_name

T = TypeVar('T')


class ArgparseDataclass(DictDataclass):
    """Mixin class providing a means of setting up an argparse parser with the dataclass fields, and then converting the namespace of parsed arguments into an instance of the class.
    NOTE: this borrows heavily from the `argparse-dataclass` library.
    The parser's argument names and types will be derived from the dataclass field names and types.
    Other arguments can be passed into the 'metadata' field of a dataclass field, namely:
        type (override the dataclass field type with a different type)
        args (lists the command-line arguments explicitly)
        nargs (number of command-line arguments (use '*' for lists, '+' for non-empty lists)
        const (constant value required by some action/nargs combinations)
        choices (list of possible inputs allowed)
        help (help string)
        metavar (name for the argument in usage messages)
        group (name of the argument group in which to put the argument; the group will be created if it does not already exist in the parser)
        exclude (boolean flag indicating that the field should not be included in the parser)"""
    @classmethod
    def parser_class(cls) -> Type[ArgumentParser]:
        """Gets the type of the top-level argument parser."""
        return ArgumentParser
    @classmethod
    def parser_description(cls) -> Optional[str]:
        """Gets a description string for the top-level argument parser.
        By default, uses the class's docstring."""
        return cls.__doc__
    @classmethod
    def parser_kwargs(cls) -> Dict[str, Any]:
        """Gets keyword arguments that will be passed to the top-level argument parser."""
        return {'description' : cls.parser_description()}
    @classmethod
    def parser_argument_kwarg_names(cls) -> List[str]:
        """Gets keyword argument names that will be passed when adding arguments to a parser."""
        return ['nargs', 'const', 'choices', 'help', 'metavar']
    @classmethod
    def new_parser(cls) -> ArgumentParser:
        """Constructs a new top-level argument parser and returns it."""
        return cls.parser_class()(**cls.parser_kwargs())
    @classmethod
    def configure_argument(cls, parser: ArgumentParser, name: str) -> None:
        """Given an argument parser and field name, configures the parser with an argument of that name.
        Attempts to provide reasonable default behavior based on the dataclass field name, type, default, and metadata.
        Subclasses may override this method to implement custom behavior."""
        kwargs: Dict[str, Any] = {}
        field = cls.__dataclass_fields__[name]
        if field.metadata.get('exclude', False):  # exclude the argument from the parser
            return
        group_name = field.metadata.get('group')
        if (group_name is not None):  # add argument to a group instead of the main parser
            for group in getattr(parser, '_action_groups', []):  # get argument group with the given name
                if (getattr(group, 'title', None) == group_name):
                    break
            else:  # group not found, so create it
                group_kwargs = {}
                if issubclass_safe(field.type, ArgparseDataclass):  # get kwargs from nested ArgparseDataclass
                    group_kwargs = field.type.parser_kwargs()
                group = parser.add_argument_group(group_name, **group_kwargs)
            parser = group
        if issubclass_safe(field.type, ArgparseDataclass):
            # recursively configure a nested ArgparseDataclass field
            field.type.configure_parser(parser)
            return
        # determine the type of the parser argument for the field
        tp = field.metadata.get('type', field.type)
        origin_type = getattr(tp, '__origin__', None)
        if (origin_type is not None):  # compound type
            if (origin_type is ClassVar):  # by default, exclude ClassVars from the parser
                return
            else:
                try:  # extract the first wrapped type (should handle List/Optional/Union)
                    tp = getattr(tp, '__args__', ())[0]
                except IndexError:  # type cannot be inferred
                    raise ValueError(f'cannot infer type of items in field {name!r}')
                if issubclass_safe(origin_type, list):
                    kwargs['nargs'] = '*'  # allow multiple arguments by default
        if issubclass(tp, IntEnum):  # use a bare int type
            tp = int
        kwargs['type'] = tp
        # get the names of the arguments associated with the field
        if ('args' in field.metadata):
            args = field.metadata['args']
        else:
            argname = field.name.replace('_', '-')
            # use a single dash for 1-letter names
            prefix = '-' if (len(field.name) == 1) else '--'
            args = [prefix + argname]
        # arg will be positional if the metadata provides an 'args' field, and the first argument does not start with a dash
        positional = not args[0].startswith('-')
        if field.metadata.get('args') and (not positional):
            # store the argument based on the name of the field, and not whatever flag name was provided
            kwargs['dest'] = field.name
        if (field.default == dataclasses.MISSING):
            if (field.default_factory == dataclasses.MISSING):
                if (not positional):  # no default available, so make the argument required
                    kwargs['required'] = True
            else:
                kwargs['default'] = field.default_factory()
        else:
            kwargs['default'] = field.default
        if (field.type is bool):  # use boolean falg instead of an argument
            kwargs['action'] = 'store_true'
            for key in ('type', 'required'):
                with suppress(KeyError):
                    kwargs.pop(key)
        # extract additional items from metadata
        for key in cls.parser_argument_kwarg_names():
            if (key in field.metadata):
                kwargs[key] = field.metadata[key]
        parser.add_argument(*args, **kwargs)
    @classmethod
    def configure_parser(cls, parser: ArgumentParser) -> None:
        """Given an argument parser, configures it by adding the appropriate arguments.
        By default, this will call `configure_argument` for each dataclass field."""
        check_dataclass(cls)
        for name in cls.__dataclass_fields__:
            cls.configure_argument(parser, name)
    @classmethod
    def make_parser(cls) -> ArgumentParser:
        """Constructs an argument parser, configures it, and returns it."""
        parser = cls.new_parser()
        cls.configure_parser(parser)
        return parser
    @classmethod
    def args_to_dict(cls, args: Namespace) -> Dict[str, Any]:
        """Converts a Namespace object to a dict that can be converted to the dataclass type.
        Override this to enable custom behavior."""
        check_dataclass(cls)
        d = {}
        for field in dataclasses.fields(cls):
            if issubclass_safe(field.type, ArgparseDataclass):
                # recursively gather arguments for nested ArgparseDataclass
                val = field.type.args_to_dict(args)
            elif hasattr(args, field.name):  # extract arg from the namespace
                val = getattr(args, field.name)
            else:  # argument not present
                continue
            d[field.name] = val
        return d
    @classmethod
    def from_args(cls: Type[T], args: Namespace) -> T:
        return cls.from_dict(cls.args_to_dict(args))
    @classmethod
    def process_args(cls, parser: ArgumentParser, args: Namespace) -> None:
        """Processes arguments from an ArgumentParser, after they are parsed."""
        pass
    @classmethod
    def from_cli_args(cls: Type[T], arg_list: Optional[List[str]] = None) -> T:
        """Constructs and configures an argument parser, then parses the given command-line arguments and uses them to construct an instance of the class.
        If no args are provided, uses sys.argv."""
        parser = cls.make_parser()  # create and configure parser
        args = parser.parse_args(args = arg_list)  # parse arguments (uses sys.argv if None)
        cls.process_args(parser, args)  # process arguments
        return cls.from_args(args)

class CLIDataclass(ArgparseDataclass):
    """This subclass of ArgparseDataclass allows the user to run a `main` program based on the parsed arguments.
    Subclasses should override the `run` method to implement custom behavior."""
    @abstractmethod
    def run(self) -> None:
        """Runs the main body of the program.
        Subclasses must implement this to provide custom behavior."""
        raise NotImplementedError(f"no implementation of 'run' for class {obj_class_name(self)!r}")
    @classmethod
    def main(cls, arg_list: Optional[List[str]] = None) -> None:
        """Executes the following procedures in sequence:
            1) Constructs a new argument parser.
            2) Configures the parser with appropriate arguments.
            3) Parses command-line arguments.
            4) Post-processes the arguments.
            5) Constructs a dataclass instance from the parsed arguments.
            6) Runs the main body of the program, using the parsed arguments.
        If command-line args are not provided, uses sys.argv."""
        obj = cls.from_cli_args(arg_list)  # steps 1-5
        obj.run()  # step 6