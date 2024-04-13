# top-level class exports
from .cli import ArgparseDataclass, CLIDataclass
from .config import ConfigDataclass
from .dict import DictDataclass
from .json import JSONBaseDataclass, JSONDataclass, JSONSerializable
from .mixin import DataclassMixin
from .sql import SQLDataclass
from .subprocess import SubprocessDataclass


__version__ = '0.3.0'
