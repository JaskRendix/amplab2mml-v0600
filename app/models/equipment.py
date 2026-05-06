from pydantic import BaseModel

from .properties import EquipmentProperty


class OverrideValue(BaseModel):
    value: str | None = None
    uom: str | None = None
    datatype: str | None = None


class Equipment(BaseModel):
    id: str
    name: str | None = None
    level: str
    full_name: str | None = None

    class_ids: list[str] = []
    properties: list[EquipmentProperty] = []
    children: list["Equipment"] = []

    overrides: dict[str, OverrideValue] = {}
