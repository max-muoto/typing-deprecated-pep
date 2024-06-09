## Abstract

This PEP adds a `typing.Deprecated` qualifier that's used to mark constants, return-types, and paramaters as being deprecated, and raising static-analysis warnings when they're used and encountered by type-checkers. No runtime behavior is changed.

## Motivation

[PEP 702](https://peps.python.org/pep-0702/) already lays a lot of the underyling context on why library developers might want to deprecate certain parts of their APIs, and the existing mechanisms for doing so. However, the functionality here explicitly left out the abliity to deprecate constants, return-types, and parameters. As it states: 

> For deprecating module-level constants, object attributes, and function parameters, a Deprecated[type, message] type modifier, similar to Annotated could be added. However, this would create a new place in the type system where strings are just strings, not forward references, complicating the implementation of type checkers. In addition, my data show that this feature is not commonly needed.

This PEP will focus on why such a feature is needed, and how it can be implemented in a way that doesn't complicate type-checker implementations.

### Need for custom deprecator decorators

While `warnings.deprecated` is a great solution for simpler use-cases around deprecating functions and methods, where custom arguments or behavior isn't needed, some Python libraries have more complex deprecation needs.

Let's take the example of Polars, a popular DataFrame library.

```python
def deprecate_function(
    message: str, *, version: str
) -> Callable[[Callable[P, T]], Callable[P, T]]:
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
```

In this example, we can see that on top of taking a `message`, as `warnings.deprecated` does, it also takes a `version` argumentl. Additinal, they apply custom logic for determining the stack level:

```python
def issue_deprecation_warning(message: str, *, version: str) -> None:
    warnings.warn(message, DeprecationWarning, stacklevel=find_stacklevel())
```

Whereas with `warnings.deprecated` you have to pass in the `stacklevel` in the decorator itself, instead of it having it be programmatically determined.

### Deprecating parameters

There's not a fully agreed upon way to deprecate parameters in Python. As of writing this, there is an ongoing discussion on Typeshed on how to best handle this, for now the most common way is going to be add a deprecated overload:

```python
from warnings import deprecated
from typing import overload

@overload
def foo(a: int, b: None = None) -> int: ...

@overload
@deprecated("Avoid using b, use a instead")
def foo(a: int, b: int) -> int: ...

def foo(a: int, b: int | None) -> int:
    if b is not None:
        warnings.warn("b is deprecated, use a instead", DeprecationWarning, stacklevel=2)
    return a
```

### Deprecating constants

Another case where `warnings.deprecated` falls short is deprecating constants. There's no way to deprecate a constant in a way that will raise a static-analysis warning when it's used. One use-case here is the standard library in Python, where constants are often deprecated in favor of new ones. Let's take the deprecation of some of the `ssl` constants in [Python 3.10](https://github.com/python/cpython/commit/2875c603b2a7691b55c2046aca54831c91efda8e). The TypeShed stubs have no way of reflecting these deprecations.

```python
OP_ALL: Options
OP_NO_SSLv2: Options
OP_NO_SSLv3: Options
OP_NO_TLSv1: Options
```


## Specification

### `typing.Deprecated`

The `typing.Deprecated` qualifier is used to mark constants, return-types, and parameters as being deprecated. It's a generic type that takes a single type argument, and an optional message argument. The message argument is a string that will be used in the warning message.

For example:

```python
import sys

from typing import Deprecated

if sys.version_info >= (3, 10):
    OP_ALL: Deprecated[Options, "Use OP_NO_TLS instead"]
    OP_NO_SSLv2: Deprecated[Options, "Use OP_NO_TLS instead"]
    OP_NO_SSLv3: Deprecated[Options, "Use OP_NO_TLS instead"]
    OP_NO_TLSv1: Deprecated[Options, "Use OP_NO_TLS instead"]
else:
    OP_ALL: Options
    OP_NO_SSLv2: Options
    OP_NO_SSLv3: Options
    OP_NO_TLSv1: Options
```

With return-types, it can be used to create a custom deprecator decorator:

```python
def deprecate(
    message: str, *, version: str
) -> Callable[Callable[P, R], Deprecated[Callable[P, R]]]:
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
```

Finally, it can be used to deprecate parameters:

```python
from typing import Deprecated

def foo(a: int, b: Deprecated[int | None] = None) -> int:
    if b is not None:
        warnings.warn("b is deprecated, use a instead", DeprecationWarning, stacklevel=2)
    return a
```

