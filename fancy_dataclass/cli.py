from argparse import (
    Action,
    ArgumentParser,
    BooleanOptionalAction,
    HelpFormatter,
    Namespace,
    _ArgumentGroup,
    _MutuallyExclusiveGroup,
)
import builtins
from collections.abc import Callable, Iterable, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import MISSING, dataclass, fields, replace
from enum import IntEnum
from typing import Any, ClassVar, Literal, Optional, TypeGuard, TypeVar, cast, get_args, get_origin

from typing_extensions import Self, override

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import DocFieldSettings, MixinSettings
from fancy_dataclass.utils import (
    _UNION_TYPES,
    AnyVersion,
    camel_case_to_kebab_case,
    check_dataclass,
    eval_type_str,
    get_annotations,
    get_version_string,
    issubclass_safe,
    type_is_optional,
    type_is_union,
)


T = TypeVar('T')
ArgParser = ArgumentParser | _ArgumentGroup


####################
# HELPER FUNCTIONS #
####################

def _get_parser_group_name(settings: 'CLIDataclassFieldSettings', name: str) -> Optional[tuple[str, bool]]:
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
        raise ValueError('nested exclusive groups are not allowed')  # noqa: TRY004
    group = parser.add_mutually_exclusive_group()
    # store the parent parser's set of dests on the group itself
    group._dests = parser._dests  # type: ignore
    # set the title attribute so the group can be retrieved later
    group.title = group_name
    group.required = required
    return group

def _add_group(parser: ArgParser, group_name: str, **group_kwargs: Any) -> _ArgumentGroup:
    if isinstance(parser, _ArgumentGroup):
        raise ValueError('nested argument groups are not allowed')  # noqa: TRY004
    kwargs = {key: val for (key, val) in group_kwargs.items() if (key in ['title', 'description'])}
    group = parser.add_argument_group(group_name, **kwargs)
    # store the parent parser's set of dests on the group itself
    group._dests = parser._dests  # type: ignore[attr-defined]
    return group

def _configure_parser_group(
    parser: ArgParser,
    group_name: str,
    is_exclusive: bool,
    required: bool,
    **group_kwargs: Any,
) -> _ArgumentGroup:
    # add argument to the group instead of the main parser
    group: Optional[_ArgumentGroup | _MutuallyExclusiveGroup]
    if is_exclusive:
        group = _get_parser_exclusive_group(parser, group_name)
    else:
        group = _get_parser_group(parser, group_name)
    if not group:  # group not found, so create it
        if is_exclusive:
            group = _add_exclusive_group(parser, group_name, required)
        else:
            group = _add_group(parser, group_name, **group_kwargs)
    return group

def _update_argument_kwargs_for_bool_action(
    kwargs: dict[str, Any],
    action:  Optional[str | builtins.type[Action]],
    name: str,
    default: Any,
    switch: bool
) -> None:
    if switch:
        action = BooleanOptionalAction
    else:
        action = action or 'store_true'
        if (default is not None) and ((action != 'store_false') == default):
            raise ValueError(
                f'cannot use default value of {default} for action {action!r} with boolean flag field {name!r}'
            )
    if isinstance(action, str) and (action not in ['store_true', 'store_false']):
        raise ValueError(f'invalid action {action!r} for boolean flag field {name!r}')
    kwargs['action'] = action
    for key in ('type', 'required'):
        kwargs.pop(key, None)

def _field_name_to_arg_name(field_name: str) -> str:
    """Gets an argument name from a field name.
    If the field name is one character long, prefixes it with '-', otherwise '--'.
    Also replaces underscores with hyphens."""
    # use a single dash for 1-letter names
    prefix = '-' if (len(field_name) == 1) else '--'
    arg_name = field_name.replace('_', '-')
    return prefix + arg_name

def _deconflict_duplicate_positional_args(parser: ArgParser, positional: bool, arg: str) -> None:
    if not hasattr(parser, '_pos_args'):
        parser._pos_args = set()  # type: ignore[union-attr]
    if positional:
        pos_args = parser._pos_args  # type: ignore[union-attr]
        if arg in pos_args:
            raise ValueError(f'duplicate positional argument {arg!r}')
        pos_args.add(arg)

def _deconflict_duplicate_dests(parser: ArgParser, dest: str) -> None:
    if not hasattr(parser, '_dests'):
        parser._dests = set()  # type: ignore[union-attr]
    elif dest in parser._dests:
        raise ValueError(f'duplicate destination field {dest!r}')
    parser._dests.add(dest)  # type: ignore[union-attr]


############
# SETTINGS #
############

@dataclass(frozen=True, kw_only=True)
class CLIDataclassSettings(MixinSettings):
    """Class-level settings for the [`CLIDataclass`][fancy_dataclass.cli.CLIDataclass] mixin.

    Subclasses of `CLIDataclass` may set the following fields as keyword arguments during inheritance:

    - `parser_class`: subclass of
    [`argparse.ArgumentParser`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser) to use for
    argument parsing
    - `formatter_class`: subclass of
    [`argparse.HelpFormatter`](https://docs.python.org/3/library/argparse.html#formatter-class) to use for
    customizing the help output
    - `help_descr`: string to use for the help description, which is displayed when `--help` is passed to the parser
        - If `None`, the class's docstring will be used by default.
    - `help_descr_brief`: string to use for the *brief* help description, which is used when the class is used as a
    *subcommand* entry. This is the text that appears in the menu of subcommands, which is often briefer than the
    main description.
        - If `None`, the class's docstring will be used by default (lowercased).
    - `command_name`: when this class is used to define a subcommand, the name of that subcommand
    - `prog`: name of the program to display when using the `%(prog)` format specifier
    - `version`: if set, expose a `--version` argument displaying the version automatically
    (see [`argparse`](https://docs.python.org/3/library/argparse.html#action) docs)
        - If `prog` is set, displays the program name and the version, otherwise just the version.
    - `default_help`: if set to `True`, includes each field's default value in its help string (this can be overridden
    by the field-level `default_help` flag)"""

    parser_class: type[ArgumentParser] = ArgumentParser
    formatter_class: Optional[type[HelpFormatter]] = None
    help_descr: Optional[str] = None
    help_descr_brief: Optional[str] = None
    command_name: Optional[str] = None
    prog: Optional[str] = None
    version: Optional[AnyVersion] = None
    default_help: bool = False


@dataclass(frozen=True, kw_only=True)
class CLIDataclassFieldSettings(DocFieldSettings):
    """Settings for [`CLIDataclass`][fancy_dataclass.cli.CLIDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `type`: override the dataclass field type with a different type
    - `args`: lists the command-line arguments explicitly
    - `action`: type of action taken when the argument is encountered
    - `nargs`: number of command-line arguments (use `*` for lists, `+` for non-empty lists)
    - `const`: constant value required by some action/nargs combinations
    - `choices`: list of possible inputs allowed
    - `help`: help string
        - Another way to specify the `help` is to use the `Annotated`/`Doc` pattern on the field (see
        [PEP 727](https://peps.python.org/pep-0727/))
    - `dest`: name of destination variable (only needed to avoid field name collisions when nesting `CLIDataclass`)
    - `metavar`: name for the argument in usage messages
    - `required`: whether the option is required
    - `group`: name of the [argument group](https://docs.python.org/3/library/argparse.html#argument-groups) in which
    to put the argument
        - The group will be created if it does not already exist in the parser
    - `exclusive_group`: name of the
    [mutually exclusive](https://docs.python.org/3/library/argparse.html#mutual-exclusion) argument group in which to
    put the argument
        - The group will be created if it does not already exist in the parser
    - `subcommand`: boolean flag marking this field as a
    [subcommand](https://docs.python.org/3/library/argparse.html#sub-commands)
    - `parse_exclude`: boolean flag indicating that the field should not be included in the parser
    - `default_help`: boolean flag indicating the field's default value (if present) should be shown in the help
        - If `None`, falls back on the class-level `default_help` flag
    - `switch`: if `True` and the field type is `bool`, makes the option a "switch" that can be set on or off, instead
    of just a flag

    Note that these line up closely with the usual options that can be passed to
    [`ArgumentParser.add_argument`](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument).

    **Positional arguments vs. options**:

    - If a field explicitly lists arguments in the `args` metadata field, the argument will be an option if the first
    listed argument starts with a dash; otherwise it will be a positional argument.
        - If it is an option but specifies no default value, it will be a required option.
    - If `args` are absent, the field will be:
        - A boolean flag if its type is `bool`
            - Can set `action` in metadata as either `"store_true"` (default) or `"store_false"`
        - An option if it specifies a default value
        - Otherwise, a positional argument
    - If `required` is specified in the metadata, this will take precedence over the default behavior above."""

    type: Optional[builtins.type | Callable[[Any], Any]] = None  # can be used to define custom constructor
    args: Optional[str | Sequence[str]] = None
    action: Optional[str | builtins.type[Action]] = None
    nargs: Optional[str | int] = None
    const: Optional[Any] = None
    choices: Optional[Sequence[Any]] = None
    help: Optional[str] = None
    metavar: Optional[str | Sequence[str]] = None
    required: Optional[bool] = None
    group: Optional[str] = None
    exclusive_group: Optional[str] = None
    subcommand: bool = False
    parse_exclude: bool = False
    default_help: Optional[bool] = None
    switch: bool = False


##########
# MIXINS #
##########

class CLIDataclass(DataclassMixin):
    """Mixin class providing a means of setting up an [`argparse`](https://docs.python.org/3/library/argparse.html)
    parser with the dataclass fields, and then converting the namespace of parsed arguments into an instance of
    the class.

    The parser's argument names and types will be derived from the dataclass's fields.

    Additionally, subclasses may override the `run` method to execute arbitrary program logic using the parsed arguments
    as input.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`.
    See [`CLIDataclassFieldSettings`][fancy_dataclass.cli.CLIDataclassFieldSettings] for the full list
    of settings."""

    __settings_type__ = CLIDataclassSettings
    __settings__ = CLIDataclassSettings()
    __field_settings_type__ = CLIDataclassFieldSettings

    # name of subcommand field, if present
    subcommand_field_name: ClassVar[Optional[str]] = None
    # name of the `argparse.Namespace` attribute associated with the subcommand
    # The convention is for this name to contain both the subcommand name and the class name.
    # This is because nested `CLIDataclass` fields may have the same subcommand name, causing conflicts.
    subcommand_dest_name: ClassVar[str]

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.subcommand_dest_name = f'_subcommand_{cls.__name__}'

    @classmethod
    @override
    def _class_settings(cls, *, base: Optional[type[DataclassMixin]] = None) -> MixinSettings:
        settings = super()._class_settings(base=base)
        if base is CLIDataclass:
            settings = cast(CLIDataclassSettings, settings)
            if settings.command_name is None:
                # if command_name was not specified in the settings, use a default name
                return replace(settings, command_name=camel_case_to_kebab_case(cls.__name__))
        return settings

    @classmethod
    def _cli_dataclass_settings(cls) -> CLIDataclassSettings:
        return cast(CLIDataclassSettings, cls._class_settings(base=CLIDataclass))

    @classmethod
    def _cli_dataclass_field_settings(cls, name: str) -> CLIDataclassFieldSettings:
        return cast(CLIDataclassFieldSettings, cls._field_settings(name, base=CLIDataclass))

    @classmethod
    @override
    def __post_dataclass_wrap__(cls) -> None:
        super().__post_dataclass_wrap__()
        subcommand = None
        names = set()
        for fld in fields(cls):  # type: ignore[arg-type]
            if not fld.metadata.get('subcommand', False):
                continue
            if subcommand is None:
                # check field type is CLIDataclass or Union thereof
                subcommand = fld.name
                tp = cast(type, fld.type)
                if issubclass_safe(tp, CLIDataclass):
                    continue
                err = TypeError(
                    f'invalid subcommand field {fld.name!r}, type must be a CLIDataclass or Union thereof'
                )
                if type_is_union(tp):
                    tp_args = [arg for arg in get_args(tp) if (arg is not type(None))]
                    for arg in tp_args:
                        if not issubclass_safe(arg, CLIDataclass):
                            raise err
                        name = arg._cli_dataclass_settings().command_name
                        if name in names:
                            raise TypeError(f'duplicate command name {name!r} in subcommand field {subcommand!r}')
                        names.add(name)
                    continue
                raise err
            raise TypeError(
                f'multiple fields ({subcommand} and {fld.name}) are registered as subcommands, at most one is allowed'
            )
        # store the name of the subcommand field as a class attribute
        cls.subcommand_field_name = subcommand

    @property
    def subcommand_name(self) -> Optional[str]:
        """Gets the name of the chosen subcommand associated with the type of the object's subcommand field.

        Returns:
            Name of the subcommand, if a subcommand field exists, and `None` otherwise"""
        if self.subcommand_field_name is not None:
            tp: type[CLIDataclass] = type(getattr(self, self.subcommand_field_name))
            return tp._cli_dataclass_settings().command_name
        return None

    @classmethod
    def _parser_description(cls) -> Optional[str]:
        if (descr := cls._cli_dataclass_settings().help_descr) is None:
            return cls.__doc__
        return descr

    @classmethod
    def _parser_description_brief(cls) -> Optional[str]:
        if (brief := cls._cli_dataclass_settings().help_descr_brief) is None:
            brief = cls._parser_description()
            if brief:
                brief = brief[0].lower() + brief[1:]
                brief = brief.removesuffix('.')
        return brief

    @classmethod
    def _parser_kwargs(cls) -> dict[str, Any]:
        """Gets keyword arguments that will be passed to the top-level argument parser.

        Returns:
            Keyword arguments passed upon construction of the `ArgumentParser`"""
        kwargs: dict[str, Any] = {'description': cls._parser_description()}
        settings = cls._cli_dataclass_settings()
        for key in ['formatter_class', 'prog']:
            if (val := getattr(settings, key)) is not None:
                kwargs[key] = val
        return kwargs

    @classmethod
    def _parser_argument_kwarg_names(cls) -> list[str]:
        """Gets keyword argument names that will be passed when adding arguments to the argument parser.

        Returns:
            Keyword argument names passed when adding arguments to the parser"""
        return ['action', 'nargs', 'const', 'choices', 'help', 'metavar']

    @classmethod
    def _new_parser(cls) -> ArgumentParser:
        """Constructs a new top-level argument parser..

        Returns:
            New top-level parser derived from the class's fields"""
        parser = cls._cli_dataclass_settings().parser_class(**cls._parser_kwargs())
        # we disallow duplicate 'dest' variables for the same parser, so track them in a set
        parser._dests = set()  # type: ignore[attr-defined]
        return parser

    @classmethod
    def _configure_argument(cls, parser: ArgParser, name: str) -> None:  # noqa: C901
        """Given an argument parser and a field name, configures the parser with an argument of that name.

        Attempts to provide reasonable default behavior based on the dataclass field name, type, default, and metadata.

        Subclasses may override this method to implement custom behavior.

        Args:
            parser: parser object to update with a new argument
            name: Name of the argument to configure"""
        cls_name = 'CLIDataclass'
        def is_nested(tp: type) -> TypeGuard[CLIDataclass]:
            return issubclass_safe(tp, CLIDataclass)
        kwargs: dict[str, Any] = {}
        fld = cls.__dataclass_fields__[name]  # type: ignore[attr-defined]
        meta = fld.metadata
        settings = cls._cli_dataclass_field_settings(name)
        if settings.parse_exclude:  # exclude the argument from the parser
            return
        # determine the type of the parser argument for the field
        tp: type = settings.type or fld.type  # type: ignore[assignment]
        if isinstance(tp, str):  # resolve type
            tp = get_annotations(cls)[name]
            assert isinstance(tp, str)
            if isinstance(tp, str):
                tp = eval_type_str(tp)
        action = settings.action or 'store'
        origin_type = get_origin(tp)
        if origin_type is not None:  # compound type
            if type_is_optional(tp):
                kwargs['default'] = None
            if origin_type == ClassVar:  # by default, exclude ClassVars from the parser
                return
            tp_args = get_args(tp)
            if issubclass_safe(origin_type, tuple):
                if tp_args:
                    tp = tp_args[0]
                    if (len(tp_args) == 2) and (tp_args[1] is Ellipsis):
                        nargs: str | int = '*'
                    elif any(arg is not tp for arg in tp_args[1:]):
                        raise TypeError(f'arguments to tuple type must all be the same in {cls_name} field')
                    else:
                        nargs = len(tp_args)
                    kwargs['nargs'] = nargs
                else:
                    action = 'store_const'
                    kwargs['const'] = origin_type()
            elif tp_args:  # Union / Optional / list
                if origin_type in _UNION_TYPES:
                    tp_args = tuple(arg for arg in tp_args if (arg is not type(None)))
                    if (len(tp_args) > 1) and (not settings.subcommand):
                        raise TypeError(f'union type {tp} not allowed as {cls_name} field except as subcommand')
                elif issubclass_safe(origin_type, list) or issubclass_safe(origin_type, tuple):
                    for arg in tp_args:
                        if is_nested(arg):
                            if issubclass_safe(origin_type, list):
                                name = f'list of {arg.__name__}'  # type: ignore[attr-defined]
                            else:
                                name = f'tuple with {arg}'
                            raise ValueError(f'{name} not allowed in {cls_name} parser')
                tp = tp_args[0]
                if get_origin(tp) == Literal:  # Optional[Literal[...]]: unwrap to Literal[...]
                    tp_args = get_args(tp)
                    origin_type = Literal
                if origin_type == Literal:  # literal options will become choices
                    arg_types = {type(arg) for arg in tp_args}
                    if len(arg_types) == 1:
                        tp = arg_types.pop()
                    else:
                        tp = None  # type: ignore[assignment]
                    kwargs['choices'] = tp_args
                if issubclass_safe(origin_type, Iterable) and (action == 'store'):
                    kwargs['nargs'] = '*'  # allow multiple arguments by default
            else:  # type cannot be inferred
                raise TypeError(f'cannot infer type of items in field {name!r}')
        if issubclass_safe(tp, IntEnum):
            # use a bare int type
            tp = int
        if issubclass_safe(get_origin(tp), list):
            tp = get_args(tp)[0]
        kwargs['type'] = tp
        if 'action' not in kwargs:
            kwargs['action'] = action
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
            args = [fld.name if positional else _field_name_to_arg_name(fld.name)]
        if args and (not positional):
            if 'dest' in meta:  # user explicitly set 'dest' in metadata
                kwargs['dest'] = meta['dest']
            else:
                # store the argument based on the name of the field, and not whatever flag name was provided
                kwargs['dest'] = fld.name
        if settings.required is not None:
            kwargs['required'] = settings.required
        has_default = 'default' in kwargs
        default = kwargs.get('default')
        if settings.switch:
            # TODO: move this to __post_dataclass_wrap__
            if tp is not bool:
                raise ValueError(f'cannot use switch=True for field {name!r} which is not a bool')
            if len(name) == 1:
                raise ValueError(f'cannot use switch=True for field {name!r} with 1-letter name')
        if tp is bool:  # use boolean flag instead of an argument
            _update_argument_kwargs_for_bool_action(kwargs, settings.action, name, default, settings.switch)
        # extract additional items from metadata
        for key in cls._parser_argument_kwarg_names():
            if key in meta:
                kwargs[key] = meta[key]
        if kwargs.get('action') in ['count', 'store_const']:
            del kwargs['type']
        if ('help' not in kwargs) and settings.doc:
            kwargs['help'] = settings.doc
        # determine if the field show its default in the help string
        if cls._cli_dataclass_settings().default_help:
            # include default if there is one, and the flag is not overridden to False at the field level
            default_help = has_default and (settings.default_help is not False)
        else:
            # include default if the field-level flag is set to True
            default_help = bool(settings.default_help)
        if default_help:
            if not has_default:
                raise ValueError(f'cannot use default_help=True for field {name!r} since it has no default')
            help_str = kwargs.get('help', None)
            # append the default value to the help string
            help_str = ((help_str + ' ') if help_str else '') + f'(default: {default})'
            kwargs['help'] = help_str
        if (result := _get_parser_group_name(settings, fld.name)) is not None:
            # add argument to the group instead of the main parser
            (group_name, is_exclusive) = result
            # get kwargs from nested CLIDataclass
            group_kwargs = tp._parser_kwargs() if is_nested(tp) else {}
            required = kwargs.get('required', False)
            parser = _configure_parser_group(parser, group_name, is_exclusive, required, **group_kwargs)
        if settings.subcommand:
            # create subparsers for each variant
            assert isinstance(parser, ArgumentParser)
            dest = cls.subcommand_dest_name
            required = kwargs.get('required', not has_default)
            if (not required) and (not has_default):
                raise ValueError(f'{name!r} field cannot set required=False with no default value')
            subparsers = parser.add_subparsers(dest=dest, required=required, help=settings.help, metavar='subcommand')
            tp_args = (tp,) if (origin_type is None) else tp_args  # pyrefly: ignore[unbound-name]
            for arg in tp_args:
                assert issubclass_safe(arg, CLIDataclass)
                descr_brief = arg._parser_description_brief()
                subparser_kwargs = arg._parser_kwargs()
                if 'formatter_class' not in subparser_kwargs:
                    # inherit formatter_class from the parent
                    subparser_kwargs['formatter_class'] = parser.formatter_class
                command_name = arg._cli_dataclass_settings().command_name
                subparser = subparsers.add_parser(command_name, help=descr_brief, **subparser_kwargs)
                # a subparser inherits the dest variables of its parents but *not* its siblings, so make a copy
                subparser._dests = set(parser._dests)  # type: ignore[attr-defined]
                arg.configure_parser(subparser)
            return
        if is_nested(tp):  # recursively configure a nested CLIDataclass field
            tp.configure_parser(parser)
            return
        # error if there are duplicate positional args or dest values
        _deconflict_duplicate_positional_args(parser, positional, args[0])
        if (dest := kwargs.get('dest')) is not None:  # type: ignore[assignment]
            _deconflict_duplicate_dests(parser, dest)
        parser.add_argument(*args, **kwargs)

    @classmethod
    def _configure_version_argument(cls, parser: ArgParser) -> None:
        """Configures the special --version argument if a version field is included in the class settings."""
        settings = cls._cli_dataclass_settings()
        if version := settings.version:
            version_str = get_version_string(version)
            if settings.prog:  # display the program name
                version_str = f'%(prog)s {version}'
            parser.add_argument('--version', action='version', version=version_str)

    @classmethod
    def configure_parser(cls, parser: ArgParser) -> None:
        """Configures an argument parser by adding the appropriate arguments.

        By default, this will simply call
        [`_configure_argument`][fancy_dataclass.cli.CLIDataclass._configure_argument] for each dataclass field.

        Args:
            parser: `ArgumentParser` to configure"""
        check_dataclass(cls)
        cls._configure_version_argument(parser)
        subcommand = None
        field_names = []
        for fld in fields(cls):  # type: ignore[arg-type]
            name = fld.name
            if fld.metadata.get('subcommand', False):
                # TODO: check field type is CLIDataclass or Union thereof
                # TODO: move this to __post_dataclass_wrap__?
                if subcommand is None:
                    subcommand = name
                else:
                    raise ValueError(
                        f'multiple fields ({subcommand!r} and {fld.name!r}) registered as subcommands, '
                        'at most one is allowed'
                    )
            else:
                field_names.append(name)
        if subcommand is not None:
            # process subcommand last, since the subparser must inherit the names of all parent 'dest' fields
            field_names.append(subcommand)
        for name in field_names:
            cls._configure_argument(parser, name)

    @classmethod
    def make_parser(cls) -> ArgumentParser:
        """Constructs an argument parser and configures it with arguments corresponding to the dataclass's fields.

        Returns:
            The configured `ArgumentParser`"""
        parser = cls._new_parser()
        cls.configure_parser(parser)
        return parser

    @classmethod
    def args_to_dict(cls, args: Namespace) -> dict[str, Any]:
        """Converts a [`Namespace`](https://docs.python.org/3/library/argparse.html#argparse.Namespace) object to a
        dict that can be converted to the dataclass type.

        Override this to enable custom behavior.

        Args:
            args: `Namespace` object storing parsed arguments

        Returns:
            A dict mapping from field names to values"""
        check_dataclass(cls)
        d = {}
        for fld in fields(cls):  # type: ignore[arg-type]
            is_nested_field = False
            if isinstance(fld.type, str):
                tp = eval_type_str(fld.type)
            else:
                tp = cast(type, fld.type)
            dest = fld.metadata.get('dest', fld.name)
            is_optional = type_is_optional(tp)
            if is_optional:
                tp = get_args(tp)[0]
            if issubclass_safe(tp, CLIDataclass):
                # recursively gather arguments for nested CLIDataclass
                val = tp.args_to_dict(args)  # type: ignore[attr-defined]
                is_nested_field = True
            elif hasattr(args, dest):  # extract arg from the namespace
                val = getattr(args, dest)
                # check that Literal value matches one of the allowed values
                if (not is_optional) and (get_origin(tp) == Literal) and (not any(val == arg for arg in get_args(tp))):
                    raise TypeError(f'invalid value {val!r} for type {tp}')
            else:  # argument not present
                continue
            if is_nested_field:  # merge in nested CLIDataclass
                d.update(val)
            else:
                d[fld.name] = val
        return d

    @classmethod
    def from_args(cls, args: Namespace) -> Self:  # noqa: C901
        """Constructs an [`CLIDataclass`][fancy_dataclass.cli.CLIDataclass] from a `Namespace` object.

        Args:
            args: `Namespace` object storing parsed arguments

        Returns:
            An instance of this class derived from the parsed arguments"""
        d = cls.args_to_dict(args)
        kwargs = {}
        for fld in fields(cls):  # type: ignore[arg-type]
            name = fld.name
            if isinstance(fld.type, str):
                tp = eval_type_str(fld.type)
            else:
                tp = fld.type
            is_subcommand = fld.metadata.get('subcommand', False)
            origin_type = get_origin(tp)
            if origin_type in _UNION_TYPES:
                tp_args = [arg for arg in get_args(tp) if (arg is not type(None))]
                subcommand = getattr(args, cls.subcommand_dest_name, None)
                if is_subcommand and subcommand:
                    tp_args = [
                        arg
                        for arg in tp_args
                        if (arg._class_settings(base=CLIDataclass).command_name == subcommand)
                    ]
                    assert len(tp_args) == 1, f'exactly one type within {tp} should have command name {subcommand}'
                    assert issubclass_safe(tp_args[0], CLIDataclass)
                tp = tp_args[0] if (subcommand or (not is_subcommand)) else None  # type: ignore[assignment]
            if tp and issubclass_safe(tp, CLIDataclass):
                # handle nested CLIDataclass
                kwargs[name] = tp.from_args(args)  # type: ignore[attr-defined]
            elif name in d:
                val = d[name]
                if isinstance(val, list) :
                    if issubclass_safe(origin_type, AbstractSet):
                        val = set(val)
                    elif issubclass_safe(origin_type, tuple):
                        val = tuple(val)
                kwargs[name] = val
            elif (
                type_is_optional(cast(type, fld.type))
                and (fld.default == MISSING)
                and (fld.default_factory == MISSING)
            ):
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

    @classmethod
    def from_cli_args(cls, arg_list: Optional[list[str]] = None) -> Self:
        """Constructs and configures an argument parser, then parses the given command-line arguments and uses them to
        construct an instance of the class.

        Args:
            arg_list: List of arguments as strings (if `None`, uses `sys.argv`)

        Returns:
            An instance of this class derived from the parsed arguments"""
        parser = cls.make_parser()  # create and configure parser
        args = parser.parse_args(args=arg_list)  # parse arguments (uses sys.argv if None)
        cls.process_args(parser, args)  # process arguments
        return cls.from_args(args)

    def run(self) -> None:
        """Runs the main body of the program.

        Subclasses should implement this to provide custom behavior.

        If the class has a subcommand defined, and it is an instance of `CLIDataclass`, the default implementation of
        `run` will be to call the subcommand's own implementation."""
        # delegate to the subcommand's `run` method, if it exists
        if self.subcommand_field_name:
            val = getattr(self, self.subcommand_field_name)
            if isinstance(val, CLIDataclass):
                return val.run()
        raise NotImplementedError

    @classmethod
    def main(cls, arg_list: Optional[list[str]] = None) -> None:
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


# aliases for backward compatibility (to be deprecated)

ArgparseDataclass = CLIDataclass
ArgparseDataclassSettings = CLIDataclassSettings
ArgparseDataclassFieldSettings = CLIDataclassFieldSettings
