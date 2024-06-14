from argparse import ArgumentParser, HelpFormatter, Namespace, _ArgumentGroup, _MutuallyExclusiveGroup
from contextlib import suppress
from dataclasses import MISSING, dataclass, fields
from enum import IntEnum
from typing import Any, Callable, ClassVar, Dict, List, Literal, Optional, Sequence, Tuple, Type, TypeVar, Union, get_args, get_origin

from typing_extensions import Self, TypeGuard

from fancy_dataclass.mixin import DataclassMixin, DataclassMixinSettings, FieldSettings
from fancy_dataclass.utils import camel_case_to_kebab_case, check_dataclass, issubclass_safe, type_is_optional


T = TypeVar('T')
ArgParser = Union[ArgumentParser, _ArgumentGroup]


####################
# HELPER FUNCTIONS #
####################

def _get_parser_group_name(settings: 'ArgparseDataclassFieldSettings', name: str) -> Optional[Tuple[str, bool]]:
    if settings.group:
        if settings.exclusive_group:
            raise ValueError(f'{name!r} specifies both group and exclusive_group: must choose only one')
        return (settings.group, False)
    if settings.exclusive_group:
        return (settings.exclusive_group, True)
    return None

def _get_parser_group(parser: ArgParser, name: str) -> Optional[_ArgumentGroup]:
    for group in getattr(parser, '_action_groups', []):
        if getattr(group, 'title', None) == name:
            assert isinstance(group, _ArgumentGroup)
            return group
    return None

def _get_parser_exclusive_group(parser: ArgParser, name: str) -> Optional[_MutuallyExclusiveGroup]:
    for group in getattr(parser, '_mutually_exclusive_groups', []):
        if getattr(group, 'title', None) == name:
            assert isinstance(group, _MutuallyExclusiveGroup)
            return group
    return None

def _add_exclusive_group(parser: ArgParser, group_name: str, required: bool) -> _MutuallyExclusiveGroup:
    if isinstance(parser, _MutuallyExclusiveGroup):
        raise ValueError('nested exclusive groups are not allowed')
    group = parser.add_mutually_exclusive_group()
    # set the title attribute so the group can be retrieved later
    group.title = group_name
    group.required = required
    return group

def _add_group(parser: ArgParser, group_name: str, **group_kwargs: Any) -> _ArgumentGroup:
    if isinstance(parser, _ArgumentGroup):
        raise ValueError('nested argument groups are not allowed')
    kwargs = {key: val for (key, val) in group_kwargs.items() if (key in ['title', 'description'])}
    return parser.add_argument_group(group_name, **kwargs)


##########
# MIXINS #
##########

@dataclass
class ArgparseDataclassSettings(DataclassMixinSettings):
    """Class-level settings for the [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] mixin.

    Subclasses of `ArgparseDataclass` may set the following fields as keyword arguments during inheritance:

    - `parser_class`: subclass of [`argparse.ArgumentParser`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser) to use for argument parsing
    - `formatter_class`: subclass of [`argparse.HelpFormatter`](https://docs.python.org/3/library/argparse.html#formatter-class) to use for customizing the help output
    - `help_descr`: string to use for the help description, which is displayed when `--help` is passed to the parser
        - If `None`, the class's docstring will be used by default.
    - `help_descr_brief`: string to use for the *brief* help description, which is used when the class is used as a *subcommand* entry. This is the text that appears in the menu of subcommands, which is often briefer than the main description.
        - If `None`, the class's docstring will be used by default (lowercased).
    - `command_name`: when this class is used to define a subcommand, the name of that subcommand
    - `version`: if set to a string, expose a `--version` argument displaying the version automatically (see [`argparse`](https://docs.python.org/3/library/argparse.html#action) docs)"""
    parser_class: Type[ArgumentParser] = ArgumentParser
    formatter_class: Optional[Type[HelpFormatter]] = None
    help_descr: Optional[str] = None
    help_descr_brief: Optional[str] = None
    command_name: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ArgparseDataclassFieldSettings(FieldSettings):
    """Settings for [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `type`: override the dataclass field type with a different type
    - `args`: lists the command-line arguments explicitly
    - `action`: type of action taken when the argument is encountered
    - `nargs`: number of command-line arguments (use `*` for lists, `+` for non-empty lists)
    - `const`: constant value required by some action/nargs combinations
    - `choices`: list of possible inputs allowed
    - `help`: help string
    - `metavar`: name for the argument in usage messages
    - `required`: whether the option is required
    - `group`: name of the [argument group](https://docs.python.org/3/library/argparse.html#argument-groups) in which to put the argument; the group will be created if it does not already exist in the parser
    - `exclusive_group`: name of the [mutually exclusive](https://docs.python.org/3/library/argparse.html#mutual-exclusion) argument group in which to put the argument; the group will be created if it does not already exist in the parser
    - `subcommand`: boolean flag marking this field as a [subcommand](https://docs.python.org/3/library/argparse.html#sub-commands)
    - `parse_exclude`: boolean flag indicating that the field should not be included in the parser

    Note that these line up closely with the usual options that can be passed to [`ArgumentParser.add_argument`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument).

    **Positional arguments vs. options**:

    - If a field explicitly lists arguments in the `args` metadata field, the argument will be an option if the first listed argument starts with a dash; otherwise it will be a positional argument.
        - If it is an option but specifies no default value, it will be a required option.
    - If `args` are absent, the field will be:
        - A boolean flag if its type is `bool`
            - Can set `action` in metadata as either `"store_true"` (default) or `"store_false"`
        - An option if it specifies a default value
        - Otherwise, a positional argument
    - If `required` is specified in the metadata, this will take precedence over the default behavior above."""
    type: Optional[Union[type, Callable[[Any], Any]]] = None  # can be used to define custom constructor
    args: Optional[Union[str, Sequence[str]]] = None
    action: Optional[str] = None
    nargs: Optional[Union[str, int]] = None
    const: Optional[Any] = None
    choices: Optional[Sequence[Any]] = None
    help: Optional[str] = None
    metavar: Optional[Union[str, Sequence[str]]] = None
    required: Optional[bool] = None
    version: Optional[str] = None
    group: Optional[str] = None
    exclusive_group: Optional[str] = None
    subcommand: bool = False
    parse_exclude: bool = False


class ArgparseDataclass(DataclassMixin):
    """Mixin class providing a means of setting up an [`argparse`](https://docs.python.org/3/library/argparse.html) parser with the dataclass fields, and then converting the namespace of parsed arguments into an instance of the class.

    The parser's argument names and types will be derived from the dataclass's fields.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`. See [`ArgparseDataclassFieldSettings`][fancy_dataclass.cli.ArgparseDataclassFieldSettings] for the full list of settings."""

    __settings_type__ = ArgparseDataclassSettings
    __settings__ = ArgparseDataclassSettings()
    __field_settings_type__ = ArgparseDataclassFieldSettings

    # name of subcommand field, if present
    subcommand_field_name: ClassVar[Optional[str]] = None
    # name of the `argparse.Namespace` attribute associated with the subcommand
    # The convention is for this name to contain both the subcommand name and the class name.
    # This is because nested `ArgparseDataclass` fields may have the same subcommand name, causing conflicts.
    subcommand_dest_name: ClassVar[str]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.subcommand_dest_name = f'_subcommand_{cls.__name__}'
        # if command_name was not specified in the settings, use a default name
        if cls.__settings__.command_name is None:
            cls.__settings__.command_name = camel_case_to_kebab_case(cls.__name__)

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: Type[Self]) -> None:
        subcommand = None
        names = set()
        for fld in fields(wrapped_cls):  # type: ignore[arg-type]
            if not fld.metadata.get('subcommand', False):
                continue
            if subcommand is None:
                # check field type is ArgparseDataclass or Union thereof
                subcommand = fld.name
                tp = fld.type
                if issubclass_safe(tp, ArgparseDataclass):
                    continue
                err = TypeError(f'invalid subcommand field {fld.name!r}, type must be an ArgparseDataclass or Union thereof')
                if get_origin(tp) == Union:
                    tp_args = [arg for arg in get_args(tp) if (arg is not type(None))]
                    for arg in tp_args:
                        if not issubclass_safe(arg, ArgparseDataclass):
                            raise err
                        name = arg.__settings__.command_name
                        if name in names:
                            raise TypeError(f'duplicate command name {name!r} in subcommand field {subcommand!r}')
                        names.add(name)
                    continue
                raise err
            raise TypeError(f'multiple fields ({subcommand} and {fld.name}) are registered as subcommands, at most one is allowed')
        # store the name of the subcommand field as a class attribute
        cls.subcommand_field_name = subcommand

    @property
    def subcommand_name(self) -> Optional[str]:
        """Gets the name of the chosen subcommand associated with the type of the object's subcommand field.

        Returns:
            Name of the subcommand, if a subcommand field exists, and `None` otherwise"""
        if self.subcommand_field_name is not None:
            tp: Type[ArgparseDataclass] = type(getattr(self, self.subcommand_field_name))
            return tp.__settings__.command_name
        return None

    @classmethod
    def _parser_description(cls) -> Optional[str]:
        if (descr := cls.__settings__.help_descr) is None:
            return cls.__doc__
        return descr

    @classmethod
    def _parser_description_brief(cls) -> Optional[str]:
        if (brief := cls.__settings__.help_descr_brief) is None:
            brief = cls._parser_description()
            if brief:
                brief = brief[0].lower() + brief[1:]
                if brief.endswith('.'):
                    brief = brief[:-1]
        return brief

    @classmethod
    def parser_kwargs(cls) -> Dict[str, Any]:
        """Gets keyword arguments that will be passed to the top-level argument parser.

        Returns:
            Keyword arguments passed upon construction of the `ArgumentParser`"""
        kwargs: Dict[str, Any] = {'description': cls._parser_description()}
        if (fmt_cls := cls.__settings__.formatter_class) is not None:
            kwargs['formatter_class'] = fmt_cls
        return kwargs

    @classmethod
    def _parser_argument_kwarg_names(cls) -> List[str]:
        """Gets keyword argument names that will be passed when adding arguments to the argument parser.

        Returns:
            Keyword argument names passed when adding arguments to the parser"""
        return ['action', 'nargs', 'const', 'choices', 'help', 'metavar']

    @classmethod
    def new_parser(cls) -> ArgumentParser:
        """Constructs a new top-level argument parser..

        Returns:
            New top-level parser derived from the class's fields"""
        return cls.__settings__.parser_class(**cls.parser_kwargs())

    @classmethod
    def configure_argument(cls, parser: ArgParser, name: str) -> None:
        """Given an argument parser and a field name, configures the parser with an argument of that name.

        Attempts to provide reasonable default behavior based on the dataclass field name, type, default, and metadata.

        Subclasses may override this method to implement custom behavior.

        Args:
            parser: parser object to update with a new argument
            name: Name of the argument to configure"""
        def is_nested(tp: type) -> TypeGuard[ArgparseDataclass]:
            return issubclass_safe(tp, ArgparseDataclass)
        kwargs: Dict[str, Any] = {}
        fld = cls.__dataclass_fields__[name]  # type: ignore[attr-defined]
        settings = cls._field_settings(fld).adapt_to(ArgparseDataclassFieldSettings)
        if settings.parse_exclude:  # exclude the argument from the parser
            return
        # determine the type of the parser argument for the field
        tp: type = settings.type or fld.type  # type: ignore[assignment]
        action = settings.action or 'store'
        origin_type = get_origin(tp)
        if origin_type is not None:  # compound type
            if type_is_optional(tp):
                kwargs['default'] = None
            if origin_type == ClassVar:  # by default, exclude ClassVars from the parser
                return
            tp_args = get_args(tp)
            if tp_args:  # Union/List/Optional
                if origin_type == Union:
                    tp_args = tuple(arg for arg in tp_args if (arg is not type(None)))
                    if (len(tp_args) > 1) and (not settings.subcommand):
                        raise ValueError(f'union type {tp} not allowed as ArgparseDataclass field except as subcommand')
                elif issubclass_safe(origin_type, list) or issubclass_safe(origin_type, tuple):
                    for arg in tp_args:
                        if is_nested(arg):
                            name = f'list of {arg.__name__}' if issubclass_safe(origin_type, list) else f'tuple with {arg}'  # type: ignore[attr-defined]
                            raise ValueError(f'{name} not allowed in ArgparseDataclass parser')
                tp = tp_args[0]
                if origin_type == Literal:  # literal options will become choices
                    tp = type(tp)
                    kwargs['choices'] = tp_args
            else:  # type cannot be inferred
                raise ValueError(f'cannot infer type of items in field {name!r}')
            if issubclass_safe(origin_type, list) and (action == 'store'):
                kwargs['nargs'] = '*'  # allow multiple arguments by default
        if issubclass_safe(tp, IntEnum):
            # use a bare int type
            tp = int
        kwargs['type'] = tp
        # determine the default value
        if fld.default == MISSING:
            if fld.default_factory != MISSING:
                kwargs['default'] = fld.default_factory()
        else:
            kwargs['default'] = fld.default
        # get the names of the arguments associated with the field
        args = settings.args
        if args is not None:
            if isinstance(args, str):
                args = [args]
            # argument is positional if it is explicitly given without a leading dash
            positional = not args[0].startswith('-')
            if (not positional) and ('default' not in kwargs):
                # no default available, so make the field a required option
                kwargs['required'] = True
        else:
            positional = (tp is not bool) and ('default' not in kwargs)
            if positional:
                args = [fld.name]
            else:
                # use a single dash for 1-letter names
                prefix = '-' if (len(fld.name) == 1) else '--'
                argname = fld.name.replace('_', '-')
                args = [prefix + argname]
        if args and (not positional):
            # store the argument based on the name of the field, and not whatever flag name was provided
            kwargs['dest'] = fld.name
        if settings.required is not None:
            kwargs['required'] = settings.required
        if fld.type is bool:  # use boolean flag instead of an argument
            action = settings.action or 'store_true'
            kwargs['action'] = action
            if action not in ['store_true', 'store_false']:
                raise ValueError(f'invalid action {action!r} for boolean flag field {name!r}')
            if (default := kwargs.get('default')) is not None:
                if (action == 'store_true') == default:
                    raise ValueError(f'cannot use default value of {default} for action {action!r} with boolean flag field {name!r}')
            for key in ('type', 'required'):
                with suppress(KeyError):
                    kwargs.pop(key)
        # extract additional items from metadata
        for key in cls._parser_argument_kwarg_names():
            if key in fld.metadata:
                kwargs[key] = fld.metadata[key]
        if kwargs.get('action') == 'store_const':
            del kwargs['type']
        if (result := _get_parser_group_name(settings, fld.name)) is not None:
            # add argument to the group instead of the main parser
            (group_name, is_exclusive) = result
            if is_exclusive:
                group: Optional[Union[_ArgumentGroup, _MutuallyExclusiveGroup]] = _get_parser_exclusive_group(parser, group_name)
            else:
                group = _get_parser_group(parser, group_name)
            if not group:  # group not found, so create it
                if is_exclusive:
                    group = _add_exclusive_group(parser, group_name, kwargs.get('required', False))
                else:
                    # get kwargs from nested ArgparseDataclass
                    group_kwargs = tp.parser_kwargs() if is_nested(tp) else {}
                    group = _add_group(parser, group_name, **group_kwargs)
            parser = group
        if settings.subcommand:
            # create subparsers for each variant
            assert isinstance(parser, ArgumentParser)
            dest = cls.subcommand_dest_name
            has_default = 'default' in kwargs
            required = kwargs.get('required', not has_default)
            if (not required) and (not has_default):
                raise ValueError(f'{name!r} field cannot set required=False with no default value')
            subparsers = parser.add_subparsers(dest=dest, required=required, help=settings.help, metavar='subcommand')
            tp_args = (tp,) if (origin_type is None) else tp_args
            for arg in tp_args:
                assert issubclass_safe(arg, ArgparseDataclass)
                descr_brief = arg._parser_description_brief()
                subparser_kwargs = arg.parser_kwargs()
                if 'formatter_class' not in subparser_kwargs:
                    # inherit formatter_class from the parent
                    subparser_kwargs['formatter_class'] = parser.formatter_class
                subparser = subparsers.add_parser(arg.__settings__.command_name, help=descr_brief, **subparser_kwargs)
                arg.configure_parser(subparser)
            return
        if is_nested(tp):  # recursively configure a nested ArgparseDataclass field
            tp.configure_parser(parser)
        else:
            # prevent duplicate positional args
            if not hasattr(parser, '_pos_args'):
                parser._pos_args = set()  # type: ignore[union-attr]
            if positional:
                pos_args = parser._pos_args
                if args[0] in pos_args:
                    raise ValueError(f'duplicate positional argument {args[0]!r}')
                pos_args.add(args[0])
            parser.add_argument(*args, **kwargs)

    @classmethod
    def configure_parser(cls, parser: Union[ArgumentParser, _ArgumentGroup]) -> None:
        """Configures an argument parser by adding the appropriate arguments.

        By default, this will simply call [`configure_argument`][fancy_dataclass.cli.ArgparseDataclass.configure_argument] for each dataclass field.

        Args:
            parser: `ArgumentParser` to configure"""
        check_dataclass(cls)
        if (version := cls.__settings__.version):
            parser.add_argument('--version', action='version', version=version)
        subcommand = None
        for fld in fields(cls):  # type: ignore[arg-type]
            if fld.metadata.get('subcommand', False):
                # TODO: check field type is ArgparseDataclass or Union thereof
                # TODO: move this to __init_dataclass__
                if subcommand is None:
                    subcommand = fld.name
                else:
                    raise ValueError(f'multiple fields ({subcommand!r} and {fld.name!r}) registered as subcommands, at most one is allowed')
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
        """Converts a [`Namespace`](https://docs.python.org/3/library/argparse.html#argparse.Namespace) object to a dict that can be converted to the dataclass type.

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
        d = cls.args_to_dict(args)
        kwargs = {}
        for fld in fields(cls):  # type: ignore[arg-type]
            name = fld.name
            tp: Optional[type] = fld.type
            is_subcommand = fld.metadata.get('subcommand', False)
            origin_type = get_origin(tp)
            if origin_type == Union:
                tp_args = [arg for arg in get_args(tp) if (arg is not type(None))]
                subcommand = getattr(args, cls.subcommand_dest_name, None)
                if is_subcommand and subcommand:
                    tp_args = [arg for arg in tp_args if (arg.__settings__.command_name == subcommand)]
                    assert len(tp_args) == 1, f'exactly one type within {tp} should have command name {subcommand}'
                    assert issubclass_safe(tp_args[0], ArgparseDataclass)
                tp = tp_args[0] if (subcommand or (not is_subcommand)) else None
            if tp and issubclass_safe(tp, ArgparseDataclass):
                # handle nested ArgparseDataclass
                kwargs[name] = tp.from_args(args)  # type: ignore[attr-defined]
            elif name in d:
                if (origin_type is tuple) and isinstance(d.get(name), list):
                    kwargs[name] = tuple(d[name])
                else:
                    kwargs[name] = d[name]
            elif type_is_optional(fld.type) and (fld.default == MISSING) and (fld.default_factory == MISSING):
                # positional optional argument with no default: fill in None
                kwargs[name] = None
        return cls(**kwargs)

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
        args = parser.parse_args(args=arg_list)  # parse arguments (uses sys.argv if None)
        cls.process_args(parser, args)  # process arguments
        return cls.from_args(args)


class CLIDataclass(ArgparseDataclass):
    """This subclass of [`ArgparseDataclass`][fancy_dataclass.cli.ArgparseDataclass] allows the user to execute arbitrary program logic using the parsed arguments as input.

    Subclasses should override the `run` method to implement custom behavior."""

    def run(self) -> None:
        """Runs the main body of the program.

        Subclasses should implement this to provide custom behavior.

        If the class has a subcommand defined, and it is an instance of `CLIDataclass`, the default implementation of `run` will be to call the subcommand's own implementation."""
        # delegate to the subcommand's `run` method, if it exists
        if self.subcommand_field_name:
            val = getattr(self, self.subcommand_field_name)
            if isinstance(val, CLIDataclass):
                return val.run()
        raise NotImplementedError

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
