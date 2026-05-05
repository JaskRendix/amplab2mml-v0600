from typing import Any

from pydantic import BaseModel


class EquipmentProperty(BaseModel):
    name: str
    value: Any | None = None
    datatype: str | None = None
    unit_of_measure: str | None = None


class ClassProperty(BaseModel):
    name: str
    description: str | None = None
    value: Any | None = None
    datatype: str | None = None
    unit_of_measure: str | None = None
