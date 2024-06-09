"""Goes through some cases in which type-checkers should warn of `typing.Deprecated` being used in an incorrect manner."""

from typing import Any, Callable
from typing_deprecated import Deprecated
from typing import TypeVar


T = TypeVar("T", bound=Callable[..., int])
_T_T = TypeVar("_T_T", bound=type[Any])

# Only return types with `__call__` should be annotated with `Deprecated`.


# Invalid examples.
def foo() -> Deprecated: ...


def foo() -> Deprecated[int]:
    return 42


def foo() -> Callable[..., Deprecated[int]]: ...


# Valid.
def foo() -> Deprecated[Callable[..., int]]:
    return lambda: 42


# Line is fine.
func = foo()

# Any usages of `foo` will now raise a static type error, and it can't be passed in as a type argument without a warning.
# After that, all warnings will be lost however.
func()  # Type error.


# Deprecated can be used on type params if they're bound to a callable.
def foo(func: T) -> Deprecated[T]:
    return func


deprectated_func = foo(lambda: 42)


# This is fine.
def foo(klass: _T_T) -> Deprecated[_T_T]:
    return klass
