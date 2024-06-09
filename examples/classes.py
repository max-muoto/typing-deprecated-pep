import dataclasses
from typing import ClassVar, Final, Optional
import pydantic

from examples.typing_deprecated import Deprecated


class MyClass:
    # All valid
    my_class_var: Deprecated[ClassVar] = 42
    my_class_var_final: Deprecated[Final] = 42
    my_class_var_2: Deprecated[ClassVar[int]] = 42
    my_class_var_final_2: Deprecated[Final[int]] = 42


@dataclasses.dataclass
class DataContainer:
    # All valid
    my_dataclass_var: Deprecated[Optional[int]] = None
    my_dataclass_var_final: Deprecated[Final[Optional[int]]] = None
    my_dataclass_var_2: Deprecated[Optional[int]] = None
    my_dataclass_var_final_2: Deprecated[Final[Optional[int]]] = None


# Pydantic ideas:


# Could have runtime functionality if combined with a library such as Pydantic?
class PydanticModel(pydantic.BaseModel):
    my_pydantic_var: Deprecated[Optional[int]] = None
    my_pydantic_var_final: Deprecated[Final[Optional[int]]] = None
    my_pydantic_var_2: Deprecated[Optional[int]] = None
    my_pydantic_var_final_2: Deprecated[Final[Optional[int]]] = None


# Runtime error could be configured through `pydantic.ConfigDict`


class PydanticModel(pydantic.BaseModel):
    model_config = {"raise_on_deprecated": True}

    my_pydantic_var: Deprecated[Optional[int]] = None
    my_pydantic_var_final: Deprecated[Final[Optional[int]]] = None
    my_pydantic_var_2: Deprecated[Optional[int]] = None
    my_pydantic_var_final_2: Deprecated[Final[Optional[int]]] = None


# Now, if a deprecated field is filled, a runtime error will be raised.
