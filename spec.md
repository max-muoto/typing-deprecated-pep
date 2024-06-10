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

## Runtime behavior

`typing.Deprecated` will have no effect on runtime behavior, outside of third-party libraries that might choose to use it for custom behavior (e.g. Pydantic), and will for all intensive purposes mimic the behavior of `typing.Annotated` in that regard.

### `get_type_hints()`

`typing.Deprecated` will be stripped from the type hints returned by `get_type_hints()`. This is to ensure that the deprecation information is only used by type-checkers, and not by runtime code.

```python
class MyClass:
    MAGIC_NUMBER: Deprecated[int, "Use MAGIC_STRING instead"] = 42

assert get_type_hints(MyClass) == {"MAGIC_NUMBER": int}
```
### `get_origin()` and `get_args()`

`typing.get_origin()` and `typing.get_args()` will return the origin and arguments of the `Deprecated` type, respectively.

```python
from typing import get_origin, get_args

assert get_origin(Deprecated[int, "Use MAGIC_STRING instead"]) == Deprecated
assert get_args(Deprecated[int, "Use MAGIC_STRING instead"]) == (int, "Use MAGIC_STRING instead")
```

## Survey of existing deprecation mechanisms

Functionality similar to `typing.Deprecated` is already present in other languages and libraries. Let's take a look at some of them:

### Rust

In Rust, you can use the `#[deprecated]` attribute to mark items as deprecated. This will raise a warning when the item is used. You can also pass in a message to the attribute, which will be included in the warning message.

```rust
const OLD_CONSTANT: i32 = 10;

#[deprecated(since = "1.2", note = "Please use NEW_CONSTANT instead.")]
const DEPRECATED_CONSTANT: i32 = 5;

const NEW_CONSTANT: i32 = 15;

fn main() {
    println!("Old constant value: {}", OLD_CONSTANT);
    // Raises a warning on usage.
    println!("Deprecated constant value: {}", DEPRECATED_CONSTANT);
    println!("New constant value: {}", NEW_CONSTANT);
}
```

### Swift

Swift decorators can be used to mark items as deprecated. You can pass in a message to the decorator, which will be included in the warning message.

```swift
let oldConstant: Int = 100

@available(*, deprecated, message: "Use newConstant instead.")
let deprecatedConstant: Int = 50

let newConstant: Int = 150

func useConstants() {
    print("Old constant value: \(oldConstant)")
    print("Deprecated constant value: \(deprecatedConstant)")
    print("New constant value: \(newConstant)")
}
```

This can also be used to deprecate parameters:

```swift
func process(data: String, @available(*, deprecated, message: "Use the newOptions parameter instead.") options: String = "default") {
    print("Data: \(data), Options: \(options)")
}

func process(data: String, newOptions: String) {
    print("Data: \(data), New Options: \(newOptions)")
}
```

### C#

C# similarily gives you the ability to mark items as deprecated using the `Obsolete` attribute. You can pass in a message to the attribute, which will be included in the warning message.

```csharp
using System;

class Constants
{
    [Obsolete("Use NewValue instead.")]
    public const int OldValue = 100;

    public const int NewValue = 200;
}

class Program
{
    static void Main()
    {
        // Using the deprecated constant will trigger a compiler warning.
        int value = Constants.OldValue;
        Console.WriteLine($"Old Value: {value}");

        // Using the new constant as recommended.
        int newValue = Constants.NewValue;
        Console.WriteLine($"New Value: {newValue}");
    }
}
```

Once again, this can also be used to deprecate parameters:

```csharp
using System;

class Program
{
    static void ProcessData(string data, [Obsolete("Use the newOptions parameter instead.")] string options = "default")
    {
        Console.WriteLine($"Data: {data}, Options: {options}");
    }

    static void ProcessData(string data, string newOptions)
    {
        Console.WriteLine($"Data: {data}, New Options: {newOptions}");
    }

    static void Main()
    {
        ProcessData("Hello, World!");
    }
}
```


## Backwards compatibility

`typing.Deprecated` will be a new addition to the `typing` module, and as such will not break any existing code. It will also be supported in older versions of Python via `tyjping_extensions`.

## How to teach this

This functionlaity can introduced as an alternative to the runtime `warnings.deprecated` function for more complex deprecation needs, and as a way to deprecate constants, return-types, and parameters in a way that will raise static-analysis warnings when they're used. By living in the `typing` module, and `deprecated` living in the `warnings` module, it's intended to be clear that one has a runtime effect, and the other a purely static-analysis effect.

