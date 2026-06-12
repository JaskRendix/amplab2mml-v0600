from typing import Any

from pydantic import BaseModel


class EquipmentProperty(BaseModel):
    name: str
    value: Any | None = None
    datatype: str | None = None
    unit_of_measure: str | None = ""
    source: str | None = None
    raw_unit_of_measure: str | None = None
    normalized_unit_of_measure: str | None = None
    uom_warning: str | None = None
    children: list["EquipmentProperty"] = []
    attributes: dict[str, str] = {}


class ClassProperty(BaseModel):
    name: str
    description: str | None = None
    value: Any | None = None
    datatype: str | None = None
    unit_of_measure: str | None = None
    raw_unit_of_measure: str | None = None
    normalized_unit_of_measure: str | None = None
    uom_warning: str | None = None
