from collections.abc import Iterator
from contextlib import contextmanager
import re
from typing import Any

import pytest

from fancy_dataclass.utils import FieldTypeValidationError


@contextmanager
def raises_field_type_err(*args: Any, **kwargs: Any) -> Iterator[None]:
    """Context manager expecting a FieldTypeValidationError to be raised with the given arguments."""
    err = FieldTypeValidationError(*args, **kwargs)
    err_str = re.escape(str(err))
    regex = re.compile(err_str, re.DOTALL)
    with pytest.raises(FieldTypeValidationError, match=regex):
        yield
