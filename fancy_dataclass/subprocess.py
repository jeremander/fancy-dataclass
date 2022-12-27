import dataclasses
from typing import ClassVar, List

from fancy_dataclass.utils import DataclassMixin, issubclass_safe


class SubprocessDataclass(DataclassMixin):
    """Mixin class providing a method for converting dataclass fields to command-line args that can be used to make a subprocess call.
    Other arguments can be passed into the 'metadata' field of a dataclass field, namely:
        exec (boolean flag indicating that this field should be treated as the name of the executable, rather than an argument)
        args (list of command-line arguments corresponding to the field -- only the first will be used)
        exclude (boolean flag indicating that the field should not be included in the args)"""
    def get_arg(self, name: str, suppress_defaults: bool = False) -> List[str]:
        """Given the name of a dataclass field, gets the command-line args for that field.
        If suppress_defaults = True, suppresses arguments that are equal ot the default values."""
        field = self.__dataclass_fields__[name]
        if field.metadata.get('exclude', False):  # exclude the argument
            return []
        if getattr(field.type, '__origin__', None) is ClassVar:
            # ignore fields associated with the class, rather than the instance
            return []
        val = getattr(self, name, None)
        if (val is None):  # optional value is None
            return []
        elif issubclass_safe(field.type, SubprocessDataclass):  # get args via nested SubprocessDataclass
            return val.args(suppress_defaults = suppress_defaults)
        if field.metadata.get('exec', False):  # treat this field as the executable
            return [str(val)]
        if suppress_defaults:  # if value matches the default, suppress the argument
            default = None
            has_default = True
            if (field.default == dataclasses.MISSING):
                if (field.default_factory == dataclasses.MISSING):
                    has_default = False
                else:
                    default = field.default_factory()
            else:
                default = field.default
            if has_default and (val == default):
                return []
        if field.metadata.get('args'):  # use arg name provided by the metadata
            arg = field.metadtaa['args'][0]
        else:  # use the field name (assume a single dash if it is a single letter)
            prefix = '-' if (len(name) == 1) else '--'
            arg = prefix + name.replace('_', '-')
        if isinstance(val, bool):
            if val:  # make it a boolean flag if True
                return [arg]
        elif isinstance(val, list):
            return [arg] + [str(x) for x in val]
        elif (val is not None):  # convert the field value to a string
            return [arg, str(val)]
        return []
    def args(self, suppress_defaults: bool = False) -> List[str]:
        """Converts dataclass fields to a list of command-line arguments for a subprocess call.
        If suppress_defaults = True, suppresses arguments that are equal to the default values."""
        args = []
        for name in self.__dataclass_fields__:
            args += self.get_arg(name, suppress_defaults = suppress_defaults)
        return args
