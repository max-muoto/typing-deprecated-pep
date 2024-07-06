from collections.abc import Callable
from typing import Any

from typing_deprecated import Deprecated


def deprecate_func[**P, R](func: Callable[P, R]) -> Deprecated[Callable[P, R]]:
    return func


@deprecate_func
def my_func(a: int, b: int) -> int:
    return a + b


# usages are deprecated
print(my_func(1, 2))  # emits a warning


# this should work with generics
def deprecate_func_2[T: Callable[..., Any]](func: T) -> Deprecated[T]:
    return func


def actual_deprecator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    def decorator(*args: P.args, **kwargs: P.kwargs) -> R:
        print("This function is deprecated.")
        return func(*args, **kwargs)

    return decorator


@actual_deprecator
class MyClass(object): ...


MyClass()
