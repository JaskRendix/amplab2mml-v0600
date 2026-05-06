import csv
from io import StringIO


def _flatten_equipment(equipment_list) -> list:
    flat = []
    stack = list(equipment_list)
    while stack:
        eq = stack.pop(0)
        flat.append(eq)
        stack = list(eq.children) + stack
    return flat


def export_equipment_csv(model: dict) -> str:
    flat = _flatten_equipment(model["equipment"])

    # Collect all property names (stable order)
    prop_names = []
    seen = set()
    for eq in flat:
        for p in eq.properties:
            if p.name not in seen:
                prop_names.append(p.name)
                seen.add(p.name)

    buf = StringIO()
    writer = csv.writer(buf)

    header = ["full_name", "level", "class_ids"]
    for name in prop_names:
        header.append(name)  # value
        header.append(f"{name}_uom")  # unit of measure
    writer.writerow(header)

    for eq in flat:
        prop_map = {p.name: p for p in eq.properties}

        row = [
            eq.full_name or "",
            eq.level or "",
            ", ".join(eq.class_ids),
        ]

        for name in prop_names:
            prop = prop_map.get(name)
            if prop:
                row.append("" if prop.value is None else prop.value)
                uom = (
                    prop.normalized_unit_of_measure
                    if getattr(prop, "normalized_unit_of_measure", None)
                    else prop.unit_of_measure
                )
                row.append(uom or "")
            else:
                row.extend(["", ""])

        writer.writerow(row)

    return buf.getvalue()


def export_classes_csv(model: dict) -> str:
    classes = model["classes"]

    prop_names = []
    seen = set()
    for cls in classes:
        for p in cls.properties:
            if p.name not in seen:
                prop_names.append(p.name)
                seen.add(p.name)

    buf = StringIO()
    writer = csv.writer(buf)

    header = ["name", "parent"]
    for name in prop_names:
        header.append(name)
        header.append(f"{name}_uom")
    writer.writerow(header)

    for cls in classes:
        prop_map = {p.name: p for p in cls.properties}

        row = [cls.name, cls.parent or ""]

        for name in prop_names:
            prop = prop_map.get(name)
            if prop:
                row.append("" if prop.value is None else prop.value)
                uom = (
                    prop.normalized_unit_of_measure
                    if getattr(prop, "normalized_unit_of_measure", None)
                    else prop.unit_of_measure
                )
                row.append(uom or "")
            else:
                row.extend(["", ""])

        writer.writerow(row)

    return buf.getvalue()
