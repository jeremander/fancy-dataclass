from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from contextlib import suppress
from dataclasses import MISSING, dataclass, fields
from enum import IntEnum
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Type, TypeVar, Union, get_args, get_origin

from typing_extensions import Self

from fancy_dataclass.mixin import DataclassMixin, FieldSettings
from fancy_dataclass.utils import check_dataclass, issubclass_safe


T = TypeVar('T')


@dataclass
class ArgparseDataclassFieldSettings(FieldSettings):
    """Settings for [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] fields."""
    # TODO: is this ever necessary?
    type: Optional[type] = None
    args: Optional[List[str]] = None
    nargs: Optional[Union[str, int]] = None
    const: Optional[Any] = None
    choices: Optional[Sequence[Any]] = None
    help: Optional[str] = None
    metavar: Optional[Union[str, Sequence[str]]] = None
    group: Optional[str] = None
    parse_exclude: bool = False


class ArgparseDataclass(DataclassMixin):
    """Mixin class providing a means of setting up an [`argparse`](https://docs.python.org/3/library/argparse.html) parser with the dataclass fields, and then converting the namespace of parsed arguments into an instance of the class.

    (NOTE: this borrows heavily from the [`argparse-dataclass`](https://github.com/mivade/argparse_dataclass) library.)

    The parser's argument names and types will be derived from the dataclass field names and types.

    Per-field arguments can be passed into the `metadata` argument of a `dataclasses.field`:

    - `type` (override the dataclass field type with a different type)
    - `args` (lists the command-line arguments explicitly)
    - `nargs` (number of command-line arguments (use `*` for lists, `+` for non-empty lists)
    - `const` (constant value required by some action/nargs combinations)
    - `choices` (list of possible inputs allowed)
    - `help` (help string)
    - `metavar` (name for the argument in usage messages)
    - `group` (name of the argument group in which to put the argument; the group will be created if it does not already exist in the parser)
    - `parse_exclude` (boolean flag indicating that the field should not be included in the parser)"""

    __field_settings_type__ = ArgparseDataclassFieldSettings

    @classmethod
    def parser_class(cls) -> Type[ArgumentParser]:
        """Gets the type of the top-level argument parser.

        Returns:
            Type (subclass of `argparse.ArgumentParser`) to be constructed by this class"""
        return ArgumentParser

    @classmethod
    def parser_description(cls) -> Optional[str]:
        """Gets a description string for the top-level argument parser, which will be displayed by default when `--help` is passed to the parser.

        By default, uses the class's own docstring.

        Returns:
            String to be used as the program's description"""
        return cls.__doc__

    @classmethod
    def parser_kwargs(cls) -> Dict[str, Any]:
        """Gets keyword arguments that will be passed to the top-level argument parser.

        Returns:
            Keyword arguments passed upon construction of the `ArgumentParser`"""
        return {'description' : cls.parser_description()}

    @classmethod
    def parser_argument_kwarg_names(cls) -> List[str]:
        """Gets keyword argument names that will be passed when adding arguments to the argument parser.

        Returns:
            Keyword argument names passed when adding arguments to the `ArgumentParser`"""
        return ['nargs', 'const', 'choices', 'help', 'metavar']

    @classmethod
    def new_parser(cls) -> ArgumentParser:
        """Constructs a new top-level argument parser..

        Returns:
            New top-level `ArgumentParser` derived from the class's fields"""
        return cls.parser_class()(**cls.parser_kwargs())

    @classmethod
    def configure_argument(cls, parser: ArgumentParser, name: str) -> None:
        """Given an argument parser and a field name, configures the parser with an argument of that name.

        Attempts to provide reasonable default behavior based on the dataclass field name, type, default, and metadata.

        Subclasses may override this method to implement custom behavior.

        Args:
            parser: `ArgumentParser` object to update with a new argument
            name: Name of the argument to configure"""
        kwargs: Dict[str, Any] = {}
        field = cls.__dataclass_fields__[name]  # type: ignore[attr-defined]
        if field.metadata.get('parse_exclude', False):  # exclude the argument from the parser
            return
        group_name = field.metadata.get('group')
        if group_name is not None:  # add argument to a group instead of the main parser
            for group in getattr(parser, '_action_groups', []):  # get argument group with the given name
                if getattr(group, 'title', None) == group_name:
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
        origin_type = get_origin(tp)
        if origin_type is not None:  # compound type
            if origin_type is ClassVar:  # by default, exclude ClassVars from the parser
                return
            tp_args = get_args(tp)
            if tp_args:  # extract the first wrapped type (should handle List/Optional/Union)
                tp = tp_args[0]
            else:  # type cannot be inferred
                raise ValueError(f'cannot infer type of items in field {name!r}')
            if issubclass_safe(origin_type, list):
                kwargs['nargs'] = '*'  # allow multiple arguments by default
        if issubclass(tp, IntEnum):  # use a bare int type
            tp = int
        kwargs['type'] = tp
        # get the names of the arguments associated with the field
        if 'args' in field.metadata:
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
        if field.default == MISSING:
            if field.default_factory == MISSING:
                if not positional:  # no default available, so make the argument required
                    kwargs['required'] = True
            else:
                kwargs['default'] = field.default_factory()
        else:
            kwargs['default'] = field.default
        if field.type is bool:  # use boolean flag instead of an argument
            kwargs['action'] = 'store_true'
            for key in ('type', 'required'):
                with suppress(KeyError):
                    kwargs.pop(key)
        # extract additional items from metadata
        for key in cls.parser_argument_kwarg_names():
            if key in field.metadata:
                kwargs[key] = field.metadata[key]
        parser.add_argument(*args, **kwargs)

    @classmethod
    def configure_parser(cls, parser: ArgumentParser) -> None:
        """Configures an argument parser by adding the appropriate arguments.

        By default, this will simply call [`configure_argument`][fancy_dataclass.cli.ArgparseDataclass.configure_argument] for each dataclass field.

        Args:
            parser: `ArgumentParser` to configure"""
        check_dataclass(cls)
        for fld in fields(cls):  # type: ignore[arg-type]
            cls.configure_argument(parser, fld.name)

    @classmethod
    def make_parser(cls) -> ArgumentParser:
        """Constructs an argument parser and configures it with arguments corresponding to the dataclass's fields.

        Returns:
            The configured `ArgumentParser`"""
        parser = cls.new_parser()
        cls.configure_parser(parser)
        return parser

    @classmethod
    def args_to_dict(cls, args: Namespace) -> Dict[str, Any]:
        """Converts a `Namespace` object to a dict that can be converted to the dataclass type.

        Override this to enable custom behavior.

        Args:
            args: `Namespace` object storing parsed arguments

        Returns:
            A dict mapping from field names to values"""
        check_dataclass(cls)
        d = {}
        for field in fields(cls):  # type: ignore[arg-type]
            nested_field = False
            if issubclass_safe(field.type, ArgparseDataclass):
                # recursively gather arguments for nested ArgparseDataclass
                val = field.type.args_to_dict(args)
                nested_field = True
            elif hasattr(args, field.name):  # extract arg from the namespace
                val = getattr(args, field.name)
            else:  # argument not present
                continue
            if nested_field:  # merge in nested ArgparseDataclass
                d.update(val)
            else:
                d[field.name] = val
        return d

    @classmethod
    def from_args(cls, args: Namespace) -> Self:
        """Constructs an [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] from a `Namespace` object.

        Args:
            args: `Namespace` object storing parsed arguments

        Returns:
            An instance of this class derived from the parsed arguments"""
        # do some basic type coercion if necessary
        d = cls.args_to_dict(args)
        for fld in fields(cls):  # type: ignore[arg-type]
            origin = get_origin(fld.type)
            if (origin is tuple) and isinstance(d.get(fld.name), list):
                d[fld.name] = tuple(d[fld.name])
        return cls(**d)

    @classmethod
    def process_args(cls, parser: ArgumentParser, args: Namespace) -> None:
        """Processes arguments from an ArgumentParser, after they are parsed.

        Override this to enable custom behavior.

        Args:
            parser: `ArgumentParser` used to parse arguments
            args: `Namespace` containing parsed arguments"""
        pass

    @classmethod
    def from_cli_args(cls, arg_list: Optional[List[str]] = None) -> Self:
        """Constructs and configures an argument parser, then parses the given command-line arguments and uses them to construct an instance of the class.

        Args:
            arg_list: List of arguments as strings (if `None`, uses `sys.argv`)

        Returns:
            An instance of this class derived from the parsed arguments"""
        parser = cls.make_parser()  # create and configure parser
        args = parser.parse_args(args = arg_list)  # parse arguments (uses sys.argv if None)
        cls.process_args(parser, args)  # process arguments
        return cls.from_args(args)


class CLIDataclass(ABC, ArgparseDataclass):
    """This subclass of [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] allows the user to run a `main` program based on the parsed arguments.

    Subclasses must override the `run` method to implement custom behavior."""

    @abstractmethod
    def run(self) -> None:
        """Runs the main body of the program.

        Subclasses must implement this to provide custom behavior."""

    @classmethod
    def main(cls, arg_list: Optional[List[str]] = None) -> None:
        """Executes the following procedures in sequence:

            1. Constructs a new argument parser.
            2. Configures the parser with appropriate arguments.
            3. Parses command-line arguments.
            4. Post-processes the arguments.
            5. Constructs a dataclass instance from the parsed arguments.
            6. Runs the main body of the program, using the parsed arguments.

        Args:
            arg_list: List of arguments as strings (if `None`, uses `sys.argv`)"""
        obj = cls.from_cli_args(arg_list)  # steps 1-5
        obj.run()  # step 6
