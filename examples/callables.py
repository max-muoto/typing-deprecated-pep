"""
While `warnings.deprecated` works well for most use-cases, some libraries might want to add on specific arguments and other functionality,
to their deprecated decorator, or simply want to use the existing depcrators they have while giving static typing errors.
"""

from __future__ import annotations


import warnings


import inspect
from functools import wraps
from typing import TYPE_CHECKING, Callable, TypeVar, ParamSpec
from typing_deprecated import Deprecated


if TYPE_CHECKING:
    P = ParamSpec("P")
    T = TypeVar("T")


# This an example from Polars, which has a fairly complex deprecation decorator, that already omits a warning on usage,
# but it doesn't come with any static checking errors.


def find_stacklevel() -> int: ...


def _rename_keyword_argument(
    old_name: str,
    new_name: str,
    kwargs: dict[str, object],
    function_name: str,
    version: str,
) -> None: ...


def issue_deprecation_warning(message: str, *, version: str) -> None:
    warnings.warn(message, DeprecationWarning, stacklevel=find_stacklevel())


def deprecate_function(
    message: str, *, version: str
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark a function as deprecated."""

    def decorate(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            issue_deprecation_warning(
                f"`{function.__qualname__}` is deprecated. {message}",
                version=version,
            )
            return function(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(function)  # type: ignore[attr-defined]
        return wrapper

    return decorate


def deprecate_renamed_function(
    new_name: str, *, version: str
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to mark a function as deprecated due to being renamed (or moved)."""
    return deprecate_function(f"It has been renamed to `{new_name}`.", version=version)


def deprecate_function(
    message: str, *, version: str
) -> Callable[[Callable[P, T]], Deprecated[Callable[P, T]]]:
    """Decorator to mark a function as deprecated."""

    def decorate(function: Callable[P, T]) -> Deprecated[Callable[P, T]]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            issue_deprecation_warning(
                f"`{function.__qualname__}` is deprecated. {message}",
                version=version,
            )
            return function(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(function)  # type: ignore[attr-defined]
        return wrapper

    return decorate


@deprecate_function("Use `my_function` instead.", version="0.20.4")
def my_function(a: int, b: int) -> int:
    return a + b


# Any usage of `my_function` will now raise a static type error. Warnings will always be controlled by the impolmented decorator or function.
my_function(1, 2)
