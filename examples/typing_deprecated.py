from typing import Annotated, Any


class Deprecated:
    """Dummy class to demonstrate usage of the `typing.Deprecated` annotation."""

    def __class_getitem__(cls, params: Any):
        return Annotated[params[0], params[1]]
