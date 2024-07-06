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

In this example, we can see that on top of taking a `message`, as `warnings.deprecated` does, it also takes a `version` argument. Additionally, they apply runtime logic for determining the stack level:

```python
def issue_deprecation_warning(message: str, *, version: str) -> None:
    warnings.warn(message, DeprecationWarning, stacklevel=find_stacklevel())
```

Whereas with `warnings.deprecated` you have to pass in the `stacklevel` in the decorator itself, instead of it having it be determined at runtime.

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

Type-checkers should produce a diaganostic under the following conditions:
* A deprecated constant, module-level attribute, or class attribute is accessed.
  * This could be, reassigning a variable to the attribute, using the attribute in an expression, passing it as an argument to a function/method, or modifying it in any way.
  * This includes both module/class attribute access, `module.DEPRECATED_CONSTANT` or `module.MyClass().deprecated_attr`, and `from` imports, `from my_module import DEPRECATED_CONSTANT`.
* A deprecated parameter is provided as a postiional or key-word argument in a function/method call.
  * Additionally, type-checkers are required to emit a diagonistic if a deprecated parameter either has no defeault (assuming no overloads exist), or no overload exists that can fulfill the function call. 
  * The same behavior should exist in the case that an argument is deprecated through a typed dictionary with the `Unpack` syntax in [PEP 692](https://peps.python.org/pep-0692/#keyword-collisions).
* For deprecator factories, for returned objects or callables, the semantics should match PEP 702 as it stands today.

### Syntax

`Deprecated`  may be used in two ways:

* With an explicit type. Example:

```python
from typing import Deprecated

MAGIC_NUMBER: Deprecated[int, "Use NEW_CONSTANT instead"] = 42
```

* With no type annotation. Example:
```python
from typing import Deprecated

MAGIC_NUMBER: Deprecated = 42
```

In the case where no type is provided, the type-checker should infer the type of the constant, parameter, or return-type, and use that as the type argument for `Deprecated`. However, **it is not** possible to provide a message without providing a type.

* In stubs and classes, providing the right hand assignment is not required.
* As `self.DEPRECATED_CONSTANT: Deprecated` (again, optionally with a type argument), in `__init__` methods.

In the context of return-types, type-checkers should raise a violation if type argument is not provided.

```python
# Ok
def foo(a: int, b: int) -> Deprecated[int, "Don't use!"]:
    return a + b

# Raises a violation
def foo(a: int, b: int) -> Deprecated:
    return a + b
```


### Interaction with other qualifiers

`Deprecated` can be used in conjunction with other qualifiers, such as `Final`, `Literal`, `Optional`, `Union`, etc, assuming `Deprecated` is the outermost qualifier.

```python
from typing import Deprecated, Final

# Ok
MAGIC_NUMBER: Deprecated[Final[int], "Use NEW_CONSTANT instead"] = 42

# Ok
MAGIC_NUMBER: Deprecated[Final, "Use NEW_CONSTANT instead"] = 42

# Not ok
MAGIC_NUMBER: Final[Deprecated[int, "Use NEW_CONSTANT instead"]] = 42
```

### Semantics

#### Constants

```python
from typing import Deprecated
import operator

DEPRECATED_CONSTANT: Deprecated[int, "Use NEW_CONSTANT instead"] = 42

x = 2 + DEPRECATED_CONSTANT  # Raises a violation
x = operator.add(2, DEPRECATED_CONSTANT)  # Raises a vilation
DEPRECATED_CONSTANT # Calls to the constant itself will raise a violation
DEPRECATED_CONSTANT = 42  # Reassigning the constant will raise a violation (if it isn't already marked `Final`)
```

#### Parameters

```python
from typing import Deprecated

def foo(a: int, b: Deprecated[int, "Don't use!"] = -1) -> int:
    return a + b

foo(1)  # Doesn't raise a violation
foo(1, 2)  # Raises a violation
foo(a=1, b=2)  # Raises a violation
```

Not-assign a default value to a deprecated parameter, should raise a warning:

```python
def foo(a: int, b: Deprecated[int, "Don't use!"]) -> int: # Raises a violation
    return a + b
```

##### Overloads

Deprecated parameters should cause an overlapping overloads to be tie-broken in favor of the non-deprecated overload.

Take this example, this currently genereates errors in Pyright and MyPy due to the ambiguity of the overloads. This should be resolved by the type-checker in favor of the non-deprecated overload:

```python
from typing import overload


@overload
def calculate(arg_1: int, arg_2: Deprecated[int] = ...) -> int: ...


@overload
def calculate(arg_1: int) -> int: ...


def calculate(arg_1: int, arg_2: int = 0) -> int:
    return arg_1 + arg_2


# Second overload should be chosen, no violation.
add(23)

# First overload should be chosen, violation.
add(23, 42)
```

#### Return-types

Similar to the semantics of PEP 702, the return-type any interaction with the return-type should raise a violation.

```python
from typing import Deprecated

def foo(a: int, b: int) -> Deprecated[int, "Don't use!"]:
    return a + b

x = foo(1, 2) # No violation (we're not using the return-type yet!)

foo(1, x)  # Raises a violation
x = 5      # Re-assigning the return-type will raise a violation
x          # Accessing the return-type will raise a violation
x + 5      # Using the return-type in an expression will raise a violation
```
 
The primary use-case of course being the creation of deprecator factories, which can be used to deprecate functions, methods, and classes.

```python
def my_deprecator[**P, R](message: str) ->  Callable[Callable[P, R], Deprecated[Callable[P, R]]]:
    def decorator(func: Callable[P, R]) -> Deprecated[Callable[P, R]]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@my_deprecator("Use something else")
def my_function(a: int, b: int) -> int:
    return a + b

my_function(1, 2)  # Raises a violation
```

!!! note

    It's required that you deprecated the first encounter of the function, method, or class, and not the return of the deprecator factory itself



### Examples

#### Deprecating constants

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

#### Deprecating return-types

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


#### Deprecating parameters

```python
from typing import Deprecated

def foo(a: int, b: Deprecated[int | None] = None) -> int:
    if b is not None:
        warnings.warn("b is deprecated, use a instead", DeprecationWarning, stacklevel=2)
    return a
```


#### Deprecating classes attributes

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age_in_years: Deprecated[int, "Use age_in_months instead"]
    age_in_months: int
```

Or:

```python
class User:
    age_in_years: Deprecated[int, "Use age_in_months instead"]

    def __init__(self, name: str, age_in_years: Deprecated[int, "Use age_in_months instead"], age_in_months: int):
        self.name = name
        self.age_in_years = age_in_years
        self.age_in_months = age_in_months
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

## Type checker behavior

It's recommened that type-checkers re-use the same static-analysis configuration options that exist for `warnings.deprecated`, for `typing.Deprecated`. For example, [`reportDeprecated` in Pyright](https://microsoft.github.io/pyright/#/configuration?id=main-configuration-options) would additionally report violations for `typing.Deprecated`, when implemented.


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

