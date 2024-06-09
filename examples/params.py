"""
Examples around deprecating parameters in functions using `typing.Deprecated`.

Currently, you can do this by adding an additional overload, let's take this example, of a param being deprecated
in Python 3.12: https://github.com/python/cpython/pull/118799/files
"""

import datetime as dt
from typing import overload
from typing_extensions import deprecated
from typing_deprecated import Deprecated


# How TypeShed is currently deprecating parameters/overloads.
@overload
def localtime(dt: dt.datetime, *, isdst: None) -> dt.datetime: ...


@overload
@deprecated("Use `isdst` instead.")
def localtime(dt: dt.datetime, isdst: bool = False) -> dt.datetime: ...


def localtime(dt: dt.datetime, isdst: bool | None = None) -> dt.datetime: ...


# What this would look like with `typing.Deprecated` in Python 3.12.
def localtime(dt: dt.datetime, isdst: Deprecated[bool] = False) -> dt.datetime: ...


# Passing a deprecated parameter will raise a warning.
localtime(dt.datetime.now(), isdst=True)

# Note: It's required that `Deprecated` parameters have a default value.
