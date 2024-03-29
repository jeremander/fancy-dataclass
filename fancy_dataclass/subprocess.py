from dataclasses import MISSING, fields
import subprocess
from typing import Any, ClassVar, List, Optional, Union

from fancy_dataclass.utils import DataclassMixin, obj_class_name


class SubprocessDataclass(DataclassMixin):
    """Mixin class providing a method for converting dataclass fields to command-line args that can be used to make a subprocess call.

    Other arguments can be passed into the `metadata` argument of a `dataclasses.field`, namely:

    - `exec` (boolean flag indicating that this field should be treated as the name of the executable, rather than an argument)
    - `args` (list of command-line arguments corresponding to the field—only the first will be used, and only if it starts with a hyphen)
    - `subprocess_exclude` (boolean flag indicating that the field should not be included in the args)"""

    def __post_init__(self) -> None:
        exec_field = None
        for fld in fields(self):  # type: ignore[arg-type]
            if fld.metadata.get('exec', False):
                if exec_field is None:
                    exec_field = fld.name
                else:
                    raise TypeError("cannot have more than one field with 'exec' flag set to True")

    def get_arg(self, name: str, suppress_defaults: bool = False) -> List[str]:
        """Given the name of a dataclass field, gets the command-line args for that field.

        Args:
            name: Name of dataclass field
            suppress_defaults: If `True`, suppresses arguments that are equal to the default values

        Returns:
            List of command-line args corresponding to the field"""
        field = self.__dataclass_fields__[name]  # type: ignore[attr-defined]
        if field.metadata.get('subprocess_exclude', False):  # exclude the argument
            return []
        if getattr(field.type, '__origin__', None) is ClassVar:
            # ignore fields associated with the class, rather than the instance
            return []
        val = getattr(self, name, None)
        if val is None:  # optional value is None
            return []
        if isinstance(val, SubprocessDataclass):  # get args via nested SubprocessDataclass
            return val.args(suppress_defaults=suppress_defaults)
        if field.metadata.get('exec', False):  # this field is the executable, so return no arguments
            return []
        if suppress_defaults:  # if value matches the default, suppress the argument
            default = None
            has_default = True
            if field.default == MISSING:
                if field.default_factory == MISSING:
                    has_default = False
                else:
                    default = field.default_factory()
            else:
                default = field.default
            if has_default and (val == default):
                return []
        if field.metadata.get('args'):  # use arg name provided by the metadata
            arg = field.metadata['args'][0]
            if not arg.startswith('-'):
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

        By default, this returns the name of the first dataclass field whose `exec` metadata flag is set to `True`, if one exists, and `None` otherwise.

        Returns:
            Name of the executable to run"""
        for fld in fields(self):  # type: ignore[arg-type]
            if fld.metadata.get('exec', False):
                return getattr(self, fld.name, None)
        return None

    def args(self, suppress_defaults: bool = False) -> List[str]:
        """Converts dataclass fields to a list of command-line arguments for a subprocess call.

        Args:
            suppress_defaults: If `True`, suppresses arguments that are equal to the default values

        Returns:
            List of command-line args corresponding to the dataclass fields"""
        args = []
        for fld in fields(self):  # type: ignore[arg-type]
            args += [arg for arg in self.get_arg(fld.name, suppress_defaults = suppress_defaults) if arg]
        return args

    def run_subprocess(self, **kwargs: Any) -> 'subprocess.CompletedProcess[Union[str, bytes]]':
        """Executes the full subprocess command corresponding to the dataclass parameters.

        Args:
            kwargs: Keyword arguments passed to `subprocess.run`

        Returns:
            `CompletedProcess` object produced by `subprocess.run`

        Raises:
            ValueError: If no executable was found from the `get_executable` method"""
        executable = self.get_executable()
        if not executable:
            raise ValueError(f'No executable identified for use with {obj_class_name(self)!r} instance')
        args = [executable] + self.args()
        return subprocess.run(args, **kwargs)
