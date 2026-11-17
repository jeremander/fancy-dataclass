from collections.abc import Sequence
from dataclasses import dataclass
import subprocess
from typing import Any, ClassVar, Optional, get_origin
import warnings

from typing_extensions import Self

from fancy_dataclass.mixin import DataclassMixin
from fancy_dataclass.settings import FieldSettings, MixinSettings
from fancy_dataclass.utils import get_dataclass_fields, obj_class_name


@dataclass(kw_only=True)
class SubprocessDataclassSettings(MixinSettings):
    """Class-level settings for the [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] mixin.

    Subclasses of `SubprocessDataclass` may set the following fields as keyword arguments during inheritance:

    - `subprocess_exec_name`: name of command-line executable to call
    - `subprocess_extra_args`: list of additional arguments to pass after all of the field-derived arguments"""

    subprocess_exec_name: Optional[str] = None
    subprocess_extra_args: Optional[Sequence[str]] = None
    exec: Optional[str] = None
    extra_args: Optional[Sequence[str]] = None

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__post_init__(*args, **kwargs)
        for (deprecated_attr, attr) in [
            ('exec', 'subprocess_exec_name'),
            ('extra_args', 'subprocess_extra_args'),
        ]:
            if (val := getattr(self, deprecated_attr)) is not None:
                warnings.warn(
                    f'{deprecated_attr} parameter is deprecated, use {attr} instead',
                    DeprecationWarning,
                    stacklevel=2,
                )
                setattr(self, attr, val)


@dataclass(kw_only=True)
class SubprocessDataclassFieldSettings(FieldSettings):
    """Settings for [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `subprocess_exec`: if `True`, use this field as the name of the executable, rather than an argument
    - `subprocess_option_name`: command-line option name for this field
        - If a string, use this as the option name, prepending with one or two dashes if not provided
        - If `None`, use the field name prefixed by one dash (if single letter) or two dashes, with underscores
        replaced by dashes
        - If the field type is `bool`, will provide the argument as a flag if the value is `True`, and omit it otherwise
    - `subprocess_exclude`:
        - If `True`, exclude this field in the subprocess args
        - If `False`, include this field in the subprocess args
        - If `None` (default), exclude this field in the subprocess args if the field is a `ClassVar`
    - `subprocess_positional`: if `True`, make this a positional argument rather than an option
    - `subprocess_flag`: if `False` and the field type is `bool`, treat the field as a regular option rather than a flag
    - `subprocess_repeat`: if `True` and the field type is a list or tuple, repeat the option name for each sequence
        value
        - Examples:
            - If `False` (default), generate `--my-option value1 value2 value3`
            - If `True`, generate `--my-option value1 --my-option value2 --my-option value3`"""

    subprocess_exec: bool = False
    subprocess_option_name: Optional[str] = None
    subprocess_exclude: Optional[bool] = None
    subprocess_positional: bool = False
    subprocess_flag: Optional[bool] = None
    subprocess_repeat: Optional[bool] = None
    exec: Optional[bool] = None
    option_name: Optional[str] = None
    repeat_option_name: Optional[bool] = None

    def __post_init__(self, *args: Any, **kwargs: Any) -> None:
        super().__post_init__(*args, **kwargs)
        for (deprecated_attr, attr) in [
            ('exec', 'subprocess_exec'),
            ('option_name', 'subprocess_option_name'),
            ('repeat_option_name', 'subprocess_repeat'),
        ]:
            if (val := getattr(self, deprecated_attr)) is not None:
                # breakpoint()
                warnings.warn(
                    f'{deprecated_attr} parameter is deprecated, use {attr} instead',
                    DeprecationWarning,
                    stacklevel=2,
                )
                setattr(self, attr, val)


class SubprocessDataclass(DataclassMixin):
    """Mixin class providing a means of converting dataclass fields to command-line arguments that can be used to make a
    [subprocess](https://docs.python.org/3/library/subprocess.html) call.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`.
    See [`SubprocessDataclassFieldSettings`][fancy_dataclass.subprocess.SubprocessDataclassFieldSettings] for the
    full list of settings."""

    __settings_type__ = SubprocessDataclassSettings
    __settings__: ClassVar[SubprocessDataclassSettings] = SubprocessDataclassSettings()
    __field_settings_type__ = SubprocessDataclassFieldSettings

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: type[Self]) -> None:
        cls_exec_name = wrapped_cls.__settings__.subprocess_exec_name
        # make sure there is at most one exec field
        exec_field = None
        for fld in get_dataclass_fields(wrapped_cls, include_all=True):
            fld_settings = cls._field_settings(fld).adapt_to(SubprocessDataclassFieldSettings)
            if fld_settings.subprocess_exec:
                if cls_exec_name is not None:
                    raise TypeError(
                        "cannot set field's 'subprocess_exec' flag to True (class already set executable to "
                        f"{cls_exec_name})"
                    )
                if exec_field is not None:
                    raise TypeError(
                        "cannot have more than one field with 'subprocess_exec' flag set to True "
                        f"(already set executable to {exec_field})"
                    )
                exec_field = fld.name
            if fld_settings.subprocess_option_name == '':
                raise ValueError('empty string not allowed for option_name')
            if fld_settings.subprocess_positional:
                if fld_settings.subprocess_option_name:
                    raise ValueError('cannot specify a field option_name when subprocess_positional=True')
                if fld_settings.subprocess_repeat:
                    raise ValueError('cannot repeat option name for positional field (subprocess_positional=True)')
            if fld_settings.subprocess_flag and (fld.type is not bool):
                raise ValueError('cannot use subprocess_flag=True when the field type is not bool')

    def get_arg(self, name: str) -> list[str]:
        """Gets the command-line arguments for the given dataclass field.

        Args:
            name: Name of dataclass field

        Returns:
            List of command-line args corresponding to the field"""
        fld = self.__dataclass_fields__[name]  # type: ignore[attr-defined]
        settings = self._field_settings(fld).adapt_to(SubprocessDataclassFieldSettings)
        if settings.subprocess_exec:  # this field is the executable, so return no arguments
            return []
        if get_origin(fld.type) is ClassVar:
            # by default, exclude fields associated with the class rather than the instance
            exclude = settings.subprocess_exclude is not False
        else:
            exclude = settings.subprocess_exclude is True
        if exclude:  # exclude the argument
            return []
        val = getattr(self, name, None)
        if val is None:  # optional value is None
            return []
        if isinstance(val, SubprocessDataclass):  # get args via nested SubprocessDataclass
            if val.get_executable():  # nested value has an executable, so include it (e.g. a subcommand)
                return val.get_args()
            # otherwise, only include the arguments
            return val._get_args()
        # determine the option name (if any)
        if settings.subprocess_positional:
            assert not settings.subprocess_option_name
            option_name = None
        else:
            # if option_name is unspecified, use the field name with underscore replaced by dash
            if settings.subprocess_option_name is None:
                option_name = name.replace('_', '-')
            else:
                option_name = settings.subprocess_option_name
            if not option_name.startswith('-'):
                # assume a single dash if the name is a single letter, otherwise a double dash
                prefix = '-' if (len(option_name) == 1) else '--'
                option_name = prefix + option_name
        # determine the value
        if isinstance(val, bool):
            if settings.subprocess_flag is False:  # use a literal boolean-valued option
                val = [str(val)]
            else:  # make it a boolean flag if value True, otherwise omit it
                if not val:
                    return []
                val = []
        elif isinstance(val, (list, tuple)):
            if val:
                if settings.subprocess_repeat:  # repeat the argument for each value in the list
                    assert not settings.subprocess_positional
                    assert option_name
                    val = [y for x in val for y in [option_name, str(x)]]
                    option_name = None
                else:
                    val = [str(x) for x in val]
            else:
                return []
        else:
            assert val is not None
            val = str(val)
        args = [option_name] if option_name else []
        args += val if isinstance(val, list) else [val]
        return args

    def get_executable(self) -> Optional[str]:
        """Gets the name of an executable to run with the appropriate arguments.

        By default, this obtains the name of the executable as follows:

        1. If the class settings specify a `subprocess_exec` member, uses that.
        2. Otherwise, returns the value of the first dataclass field whose `subprocess_exec` metadata flag is set to
        `True` (only one is permitted), and `None` otherwise.

        Returns:
            Name of the executable to run

        Raises:
            ValueError: If the executable is not a string"""
        def _check_type(val: Any) -> str:
            if isinstance(val, str):
                return val
            raise ValueError(f'executable is {val} (must be a string)')
        if self.__settings__.subprocess_exec_name:
            return _check_type(self.__settings__.subprocess_exec_name)
        for fld in get_dataclass_fields(self, include_all=True):
            settings = self._field_settings(fld).adapt_to(SubprocessDataclassFieldSettings)
            if settings.subprocess_exec:
                return _check_type(getattr(self, fld.name, None))
        return None

    def _get_args(self) -> list[str]:
        """Converts dataclass fields to a list of command-line arguments for a subprocess call.

        This excludes the executable name itself."""
        args = []
        for fld in get_dataclass_fields(self, include_all=True):
            args += [arg for arg in self.get_arg(fld.name) if arg]
        args += list(self.__settings__.subprocess_extra_args or [])
        return args

    def get_args(self) -> list[str]:
        """Converts dataclass fields to a list of command-line arguments for a subprocess call.

        This includes the executable name itself as the first argument, if there is one.

        Returns:
            List of command-line args corresponding to the dataclass fields"""
        args = self._get_args()
        if (executable := self.get_executable()):
            args = [executable] + args
        return args

    def run_subprocess(self, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """Executes the full subprocess command corresponding to the dataclass parameters.

        Args:
            kwargs: Keyword arguments passed to `subprocess.run`

        Returns:
            `CompletedProcess` object produced by `subprocess.run`

        Raises:
            ValueError: If no executable was found from the `get_executable` method"""
        executable = self.get_executable()
        if not executable:
            raise ValueError(f'no executable identified for use with {obj_class_name(self)} instance')
        return subprocess.run(self.get_args(), **kwargs)  # noqa: PLW1510
