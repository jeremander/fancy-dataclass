# top-level class exports
from .cli import ArgparseDataclass, CLIDataclass
from .config import ConfigDataclass
from .dict import DictDataclass
from .json import JSONBaseDataclass, JSONDataclass, JSONSerializable
from .sql import SQLDataclass
from .subprocess import SubprocessDataclass
from .utils import DataclassMixin


__version__ = '0.2.0'
