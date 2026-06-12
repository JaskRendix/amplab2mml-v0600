from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from lxml import etree

NS = "http://www.mesa.org/xml/B2MML-V0600"
XSI = "http://www.w3.org/2001/XMLSchema-instance"


def _el(tag: str) -> etree._Element:
    return etree.Element(f"{{{NS}}}{tag}")


def _sub(parent: etree._Element, tag: str) -> etree._Element:
    return etree.SubElement(parent, f"{{{NS}}}{tag}")


def build_b2mml_xml(model: dict[str, Any], config: dict[str, Any]) -> str:
    root = etree.Element(
        f"{{{NS}}}ShowEquipmentInformation",
        nsmap={None: NS, "xsi": XSI},
        releaseID="0600",
        versionID="0600",
    )

    aa = _sub(root, "ApplicationArea")

    sender = _sub(aa, "Sender")
    _sub(sender, "LogicalID").text = "AMPLA"
    _sub(sender, "ComponentID").text = "AmplaToB2MML"

    receiver = _sub(aa, "Receiver")
    _sub(receiver, "LogicalID").text = "B2MML"
    _sub(receiver, "ComponentID").text = "Consumer"

    creation = _sub(aa, "CreationDateTime")
    creation.text = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    da = _sub(root, "DataArea")
    _sub(da, "Show")

    info = _sub(da, "EquipmentInformation")

    published = _sub(info, "PublishedDate")
    published.text = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    for eq in model["equipment"]:
        info.append(build_equipment_xml(eq, config))

    for cls in model["classes"]:
        info.append(build_class_xml(cls, config))

    return etree.tostring(root, pretty_print=True, encoding="unicode")


# ======================================================================
# EquipmentClass
# ======================================================================


def build_class_xml(cls: Any, config: dict[str, Any]) -> etree._Element:
    c = _el("EquipmentClass")

    _sub(c, "ID").text = cls.name

    # Description (optional)
    for desc in getattr(cls, "descriptions", []):
        _sub(c, "Description").text = desc

    # EquipmentClassProperty
    for prop in cls.properties:
        c.append(build_property("EquipmentClassProperty", prop, config))

    return c


# ======================================================================
# Equipment
# ======================================================================


def build_equipment_xml(eq: Any, config: dict[str, Any]) -> etree._Element:
    e = _el("Equipment")

    # ID
    _sub(e, "ID").text = eq.full_name

    # Description
    for desc in getattr(eq, "descriptions", []):
        _sub(e, "Description").text = desc

    # HierarchyScope (optional)
    if getattr(eq, "hierarchy", None):
        e.append(build_hierarchy_scope(eq.hierarchy))

    # EquipmentLevel (HierarchyScopeType)
    e.append(build_equipment_level(eq.level))

    # EquipmentAssetMapping
    for mapping in getattr(eq, "asset_mappings", []):
        e.append(build_asset_mapping(mapping))

    # EquipmentProperty
    for prop in eq.properties:
        e.append(build_property("EquipmentProperty", prop, config))

    # Children
    for child in eq.children:
        e.append(build_equipment_xml(child, config))

    # EquipmentClassID
    for cid in eq.class_ids:
        _sub(e, "EquipmentClassID").text = cid

    # EquipmentCapabilityTestSpecificationID
    for tid in getattr(eq, "test_spec_ids", []):
        _sub(e, "EquipmentCapabilityTestSpecificationID").text = tid

    return e


# ======================================================================
# HierarchyScopeType
# ======================================================================


def build_hierarchy_scope(h: Any) -> etree._Element:
    hs = _el("HierarchyScope")

    _sub(hs, "EquipmentID").text = h.equipment_id
    _sub(hs, "EquipmentElementLevel").text = h.level

    # Nested hierarchy (optional)
    if getattr(h, "parent", None):
        hs.append(build_hierarchy_scope(h.parent))

    return hs


# ======================================================================
# EquipmentLevel (HierarchyScopeType)
# ======================================================================


def build_equipment_level(level: str) -> etree._Element:
    el = _el("EquipmentLevel")

    # EquipmentID is required by schema, but Ampla does not provide one.
    # We use a deterministic placeholder.
    _sub(el, "EquipmentID").text = "LEVEL"

    _sub(el, "EquipmentElementLevel").text = level

    return el


# ======================================================================
# EquipmentAssetMapping
# ======================================================================


def build_asset_mapping(m: Any) -> etree._Element:
    am = _el("EquipmentAssetMapping")

    _sub(am, "EquipmentID").text = m.equipment_id
    _sub(am, "PhysicalAssetID").text = m.asset_id

    if m.start_time:
        _sub(am, "StartTime").text = m.start_time

    if m.end_time:
        _sub(am, "EndTime").text = m.end_time

    return am


def build_property(tag: str, prop: Any, config: dict[str, Any]) -> etree._Element:
    p_el = _el(tag)

    _sub(p_el, "ID").text = prop.name

    for desc in getattr(prop, "descriptions", []):
        _sub(p_el, "Description").text = desc

    val = _sub(p_el, "Value")

    type_map = {
        "int": "ValueInt",
        "float": "ValueFloat",
        "boolean": "ValueBoolean",
        "datetime": "ValueDateTime",
        "decimal": "ValueDecimal",
    }
    dtype = (prop.datatype or "").lower()
    v_tag = type_map.get(dtype, "ValueString")

    value_el = _sub(val, v_tag)
    value_el.text = "" if prop.value is None else str(prop.value)

    for k, v in getattr(prop, "attributes", {}).items():
        value_el.set(k, v)

    _sub(val, "DataType").text = (prop.datatype or "string").lower()

    uom = getattr(prop, "normalized_unit_of_measure", None) or prop.unit_of_measure
    if uom:  # ← only emit when non‑empty
        _sub(val, "UnitOfMeasure").text = uom

    for child in getattr(prop, "children", []):
        p_el.append(build_property(tag, child, config))

    return p_el
