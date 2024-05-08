from dataclasses import MISSING, dataclass, fields
import subprocess
from typing import Any, ClassVar, List, Optional, Sequence, Type, Union, get_origin

from typing_extensions import Self

from fancy_dataclass.mixin import DataclassMixin, DataclassMixinSettings, FieldSettings
from fancy_dataclass.utils import get_dataclass_fields, obj_class_name


@dataclass
class SubprocessDataclassSettings(DataclassMixinSettings):
    """Class-level settings for the [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] mixin.

    Subclasses of `SubprocessDataclass` may set the following fields as keyword arguments during inheritance:

    - `exec`: name of command-line executable to call"""
    exec: Optional[str] = None


@dataclass
class SubprocessDataclassFieldSettings(FieldSettings):
    """Settings for [`SubprocessDataclass`][fancy_dataclass.subprocess.SubprocessDataclass] fields.

    Each field may define a `metadata` dict containing any of the following entries:

    - `exec`: if `True`, use this field as the name of the executable, rather than an argument
    - `args`: command-line arguments corresponding to the field
        - If a non-empty list, use the first entry as the argument name if it starts with a dash, and treat it as a positional argument otherwise
        - If `None`, use the field name prefixed by one dash (if single letter) or two dashes, with underscores replaced by dashes
        - If an empty list, exclude this field from the arguments
        - If the field type is `bool`, will provide the argument as a flag if the value is `True`, and omit it otherwise"""
    exec: bool = False
    args: Optional[Union[str, Sequence[str]]] = None


class SubprocessDataclass(DataclassMixin):
    """Mixin class providing a means of converting dataclass fields to command-line arguments that can be used to make a [subprocess](https://docs.python.org/3/library/subprocess.html) call.

    Per-field settings can be passed into the `metadata` argument of each `dataclasses.field`. See [`SubprocessDataclassFieldSettings`][fancy_dataclass.subprocess.SubprocessDataclassFieldSettings] for the full list of settings."""

    __settings_type__ = SubprocessDataclassSettings
    __settings__ = SubprocessDataclassSettings()
    __field_settings_type__ = SubprocessDataclassFieldSettings

    @classmethod
    def __post_dataclass_wrap__(cls, wrapped_cls: Type[Self]) -> None:
        cls_exec_field = wrapped_cls.__settings__.exec
        # make sure there is at most one exec field
        exec_field = None
        for fld in get_dataclass_fields(wrapped_cls, include_classvars=True):
            fld_settings = cls._field_settings(fld).adapt_to(SubprocessDataclassFieldSettings)
            if fld_settings.exec:
                if cls_exec_field is not None:
                    raise TypeError(f"cannot set field's 'exec' flag to True (class already set executable to {cls_exec_field})")
                if exec_field is not None:
                    raise TypeError(f"cannot have more than one field with 'exec' flag set to True (already set executable to {exec_field})")
                exec_field = fld.name

    def get_arg(self, name: str, suppress_defaults: bool = False) -> List[str]:
        """Gets the command-line arguments for the given dataclass field.

        Args:
            name: Name of dataclass field
            suppress_defaults: If `True`, suppresses arguments that are equal to the default values

        Returns:
            List of command-line args corresponding to the field"""
        fld = self.__dataclass_fields__[name]  # type: ignore[attr-defined]
        settings = self._field_settings(fld).adapt_to(SubprocessDataclassFieldSettings)
        args = settings.args
        args = [args] if isinstance(args, str) else args
        if args == []:  # exclude the argument
            return []
        if settings.exec:  # this field is the executable, so return no arguments
            return []
        if get_origin(fld.type) is ClassVar:
            # ignore fields associated with the class, rather than the instance
            return []
        val = getattr(self, name, None)
        if val is None:  # optional value is None
            return []
        if isinstance(val, SubprocessDataclass):  # get args via nested SubprocessDataclass
            return val.get_args(suppress_defaults=suppress_defaults)
        if suppress_defaults:  # if value matches the default, suppress the argument
            default = None
            has_default = True
            if fld.default == MISSING:
                if fld.default_factory == MISSING:
                    has_default = False
                else:
                    default = fld.default_factory()
            else:
                default = fld.default
            if has_default and (val == default):
                return []
        if args:  # use arg name provided by the metadata
            arg: Optional[str] = args[0]
            if not arg.startswith('-'):  # type: ignore[union-attr]
                arg = None
        else:  # use the field name (assume a single dash if it is a single letter)
            prefix = '-' if (len(name) == 1) else '--'
            arg = prefix + name.replace('_', '-')
        if isinstance(val, bool):
            # make it a boolean flag if True, otherwise omit it
            if not val:
                arg = None
            val = []
        elif isinstance(val, (list, tuple)):
            if val:
                val = [str(x) for x in val]
            else:
                arg = None
        elif val is not None:  # convert the field value to a string
            val = str(val)
        args = [arg] if arg else []
        args += val if isinstance(val, list) else [val]
        return args

    def get_executable(self) -> Optional[str]:
        """Gets the name of an executable to run with the appropriate arguments.

        By default, this obtains the name of the executable as follows:

        1. If the class settings specify an `exec` member, uses that.
        2. Otherwise, returns the value of the first dataclass field whose `exec` metadata flag is set to `True`, and `None` otherwise.

        Returns:
            Name of the executable to run

        Raises:
            ValueError: If the executable is not a string"""
        def _check_type(val: Any) -> str:
            if isinstance(val, str):
                return val
            raise ValueError(f'executable is {val} (must be a string)')
        if self.__settings__.exec:
            return _check_type(self.__settings__.exec)
        for fld in get_dataclass_fields(self, include_classvars=True):
            if fld.metadata.get('exec', False):
                return _check_type(getattr(self, fld.name, None))
        return None

    def get_args(self, suppress_defaults: bool = False) -> List[str]:
        """Converts dataclass fields to a list of command-line arguments for a subprocess call.

        This includes the executable name itself as the first argument.

        Args:
            suppress_defaults: If `True`, suppresses arguments that are equal to the default values

        Returns:
            List of command-line args corresponding to the dataclass fields"""
        executable = self.get_executable()
        if not executable:
            raise ValueError(f'no executable identified for use with {obj_class_name(self)} instance')
        args = [executable]
        for fld in fields(self):  # type: ignore[arg-type]
            args += [arg for arg in self.get_arg(fld.name, suppress_defaults=suppress_defaults) if arg]
        return args

    def run_subprocess(self, **kwargs: Any) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
        """Executes the full subprocess command corresponding to the dataclass parameters.

        Args:
            kwargs: Keyword arguments passed to `subprocess.run`

        Returns:
            `CompletedProcess` object produced by `subprocess.run`

        Raises:
            ValueError: If no executable was found from the `get_executable` method"""
        return subprocess.run(self.get_args(), **kwargs)
