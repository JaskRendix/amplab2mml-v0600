from datetime import UTC, datetime

from lxml import etree

NS = "http://www.mesa.org/xml/B2MML-V0600"


def build_b2mml_xml(model, config):
    root = etree.Element(
        "ShowEquipmentInformation",
        nsmap={None: NS, "xsi": "http://www.w3.org/2001/XMLSchema-instance"},
    )

    # ApplicationArea
    aa = etree.SubElement(root, "ApplicationArea")
    creation = etree.SubElement(aa, "CreationDateTime")
    creation.text = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # DataArea
    da = etree.SubElement(root, "DataArea")
    etree.SubElement(da, "Show")

    info = etree.SubElement(da, "EquipmentInformation")
    published = etree.SubElement(info, "PublishedDate")
    published.text = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    # Classes first (B2MML ordering)
    for cls in model["classes"]:
        info.append(build_class_xml(cls, config))

    # Equipment tree
    for eq in model["equipment"]:
        info.append(build_equipment_xml(eq, config))

    return etree.tostring(root, pretty_print=True, encoding="unicode")


def build_class_xml(cls, config):
    c = etree.Element("EquipmentClass")
    etree.SubElement(c, "ID").text = cls.name

    for prop in cls.properties:
        c.append(build_property("EquipmentClassProperty", prop, config))

    return c


def build_equipment_xml(eq, config):
    e = etree.Element("Equipment")

    etree.SubElement(e, "ID").text = eq.full_name
    etree.SubElement(e, "EquipmentElementLevel").text = eq.level

    # Class references
    for cid in eq.class_ids:
        etree.SubElement(e, "EquipmentClassID").text = cid

    # Properties
    for prop in eq.properties:
        e.append(build_property("EquipmentProperty", prop, config))

    # Children
    for child in eq.children:
        e.append(build_equipment_xml(child, config))

    return e


def build_property(tag, prop, config):
    p_el = etree.Element(tag)
    etree.SubElement(p_el, "ID").text = prop.name

    val_wrap = etree.SubElement(p_el, "Value")

    # Typed value tag
    type_map = {
        "int": "ValueInt",
        "float": "ValueFloat",
        "boolean": "ValueBoolean",
        "datetime": "ValueDateTime",
        "decimal": "ValueDecimal",
    }
    v_tag = type_map.get(prop.datatype, "ValueString")
    etree.SubElement(val_wrap, v_tag).text = (
        "" if prop.value is None else str(prop.value)
    )

    # DataType
    etree.SubElement(val_wrap, "DataType").text = prop.datatype or "string"

    # UnitOfMeasure
    uom_map = config.get("uom_map", {})
    uom = uom_map.get(prop.unit_of_measure, prop.unit_of_measure)
    etree.SubElement(val_wrap, "UnitOfMeasure").text = uom or ""

    return p_el
