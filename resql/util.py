from enum import Enum
from typing import Any


def enum_values(enumeration: Enum) -> list[Any]:
    return [elem.value for elem in enumeration]  # type: ignore[attr-defined]
