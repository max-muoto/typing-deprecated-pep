"""
Examples around deprecating constants using `typing.Deprecated`.
"""

from typing import Final, reveal_type
from examples.typing_deprecated import Deprecated


MAGIC_NUMBER: Deprecated[int] = 42

# This can be combined with `typing.Final`, `Deprecated` must always be the outermost type however.

MAGIC_NUMBER_FINAL: Deprecated[Final[int]] = 42

# It operates as a qualifier, so a type will be inferred as `int` in this case if no inner type is provided.
MAGIC_NUMBER_NO_INNER: Deprecated = 42

reveal_type(MAGIC_NUMBER)  # Revealed type is 'int'`
