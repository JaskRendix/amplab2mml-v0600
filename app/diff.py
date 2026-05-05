from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffResult:
    equipment_added: list[str] = field(default_factory=list)
    equipment_removed: list[str] = field(default_factory=list)
    equipment_level_changed: list[dict] = field(default_factory=list)
    equipment_properties_changed: list[dict] = field(default_factory=list)
    classes_added: list[str] = field(default_factory=list)
    classes_removed: list[str] = field(default_factory=list)
    class_properties_changed: list[dict] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            [
                self.equipment_added,
                self.equipment_removed,
                self.equipment_level_changed,
                self.equipment_properties_changed,
                self.classes_added,
                self.classes_removed,
                self.class_properties_changed,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_added": self.equipment_added,
            "equipment_removed": self.equipment_removed,
            "equipment_level_changed": self.equipment_level_changed,
            "equipment_properties_changed": self.equipment_properties_changed,
            "classes_added": self.classes_added,
            "classes_removed": self.classes_removed,
            "class_properties_changed": self.class_properties_changed,
        }

    def to_text(self) -> str:
        lines = []

        for name in self.equipment_added:
            lines.append(f"+ equipment  {name}")
        for name in self.equipment_removed:
            lines.append(f"- equipment  {name}")
        for ch in self.equipment_level_changed:
            lines.append(f"~ equipment  {ch['name']}  level: {ch['old']} → {ch['new']}")

        for ch in self.equipment_properties_changed:
            eq = ch["equipment"]
            for p in ch["added"]:
                lines.append(f"+ property   {eq}.{p['name']} = {p['value']}")
            for p in ch["removed"]:
                lines.append(f"- property   {eq}.{p['name']}")
            for p in ch["changed"]:
                lines.append(f"~ property   {eq}.{p['name']}: {p['old']} → {p['new']}")

        for name in self.classes_added:
            lines.append(f"+ class      {name}")
        for name in self.classes_removed:
            lines.append(f"- class      {name}")
        for ch in self.class_properties_changed:
            cls = ch["class"]
            for p in ch["added"]:
                lines.append(f"+ classprop  {cls}.{p['name']} = {p['value']}")
            for p in ch["removed"]:
                lines.append(f"- classprop  {cls}.{p['name']}")
            for p in ch["changed"]:
                lines.append(f"~ classprop  {cls}.{p['name']}: {p['old']} → {p['new']}")

        return "\n".join(lines) if lines else "No differences found."


def diff_models(model_a: dict, model_b: dict) -> DiffResult:
    result = DiffResult()

    _diff_equipment(model_a, model_b, result)
    _diff_classes(model_a, model_b, result)

    return result


def _flatten_equipment(equipment_list) -> dict:
    """Flatten nested equipment tree into {full_name: equipment} dict."""
    flat = {}
    stack = list(equipment_list)
    while stack:
        eq = stack.pop()
        flat[eq.full_name] = eq
        stack.extend(eq.children)
    return flat


def _diff_equipment(model_a, model_b, result: DiffResult):
    flat_a = _flatten_equipment(model_a["equipment"])
    flat_b = _flatten_equipment(model_b["equipment"])

    names_a = set(flat_a)
    names_b = set(flat_b)

    result.equipment_added = sorted(names_b - names_a)
    result.equipment_removed = sorted(names_a - names_b)

    for name in sorted(names_a & names_b):
        eq_a = flat_a[name]
        eq_b = flat_b[name]

        # Level changes
        if eq_a.level != eq_b.level:
            result.equipment_level_changed.append(
                {"name": name, "old": eq_a.level, "new": eq_b.level}
            )

        # Property changes
        prop_changes = _diff_properties(
            {p.name: p for p in eq_a.properties},
            {p.name: p for p in eq_b.properties},
        )

        if any(prop_changes.values()):
            result.equipment_properties_changed.append(
                {"equipment": name, **prop_changes}
            )


def _diff_classes(model_a, model_b, result: DiffResult):
    cls_a = {cls.name: cls for cls in model_a["classes"]}
    cls_b = {cls.name: cls for cls in model_b["classes"]}

    names_a = set(cls_a)
    names_b = set(cls_b)

    result.classes_added = sorted(names_b - names_a)
    result.classes_removed = sorted(names_a - names_b)

    for name in sorted(names_a & names_b):
        prop_changes = _diff_properties(
            {p.name: p for p in cls_a[name].properties},
            {p.name: p for p in cls_b[name].properties},
        )

        if any(prop_changes.values()):
            result.class_properties_changed.append({"class": name, **prop_changes})


def _diff_properties(props_a: dict, props_b: dict) -> dict:
    names_a = set(props_a)
    names_b = set(props_b)

    added = [{"name": n, "value": props_b[n].value} for n in sorted(names_b - names_a)]

    removed = [{"name": n} for n in sorted(names_a - names_b)]

    changed = []
    for n in sorted(names_a & names_b):
        a = props_a[n]
        b = props_b[n]

        # v0600: compare typed values + UoM
        if a.value != b.value or a.unit_of_measure != b.unit_of_measure:
            changed.append(
                {
                    "name": n,
                    "old": {"value": a.value, "uom": a.unit_of_measure},
                    "new": {"value": b.value, "uom": b.unit_of_measure},
                }
            )

    return {"added": added, "removed": removed, "changed": changed}
