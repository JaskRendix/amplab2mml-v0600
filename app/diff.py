from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffResult:
    equipment_added: list[str] = field(default_factory=list)
    equipment_removed: list[str] = field(default_factory=list)
    equipment_level_changed: list[dict] = field(default_factory=list)
    equipment_properties_changed: list[dict] = field(default_factory=list)
    equipment_hierarchy_changed: list[dict] = field(default_factory=list)

    classes_added: list[str] = field(default_factory=list)
    classes_removed: list[str] = field(default_factory=list)
    class_properties_changed: list[dict] = field(default_factory=list)
    class_inheritance_changed: list[dict] = field(default_factory=list)
    class_metadata_changed: list[dict] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not any(
            [
                self.equipment_added,
                self.equipment_removed,
                self.equipment_level_changed,
                self.equipment_properties_changed,
                self.equipment_hierarchy_changed,
                self.classes_added,
                self.classes_removed,
                self.class_properties_changed,
                self.class_inheritance_changed,
                self.class_metadata_changed,
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipment_added": self.equipment_added,
            "equipment_removed": self.equipment_removed,
            "equipment_level_changed": self.equipment_level_changed,
            "equipment_properties_changed": self.equipment_properties_changed,
            "equipment_hierarchy_changed": self.equipment_hierarchy_changed,
            "classes_added": self.classes_added,
            "classes_removed": self.classes_removed,
            "class_properties_changed": self.class_properties_changed,
            "class_inheritance_changed": self.class_inheritance_changed,
            "class_metadata_changed": self.class_metadata_changed,
        }

    def to_text(self) -> str:
        lines = []

        for name in self.equipment_added:
            lines.append(f"+ equipment  {name}")
        for name in self.equipment_removed:
            lines.append(f"- equipment  {name}")
        for ch in self.equipment_level_changed:
            lines.append(f"~ equipment  {ch['name']}  level: {ch['old']} → {ch['new']}")
        for ch in self.equipment_hierarchy_changed:
            lines.append(f"~ hierarchy  {ch['name']}: parent {ch['old']} → {ch['new']}")

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

        for ch in self.class_inheritance_changed:
            lines.append(f"~ inheritance {ch['class']}: {ch['old']} → {ch['new']}")

        for ch in self.class_metadata_changed:
            lines.append(f"~ classmeta  {ch['class']}: {ch['old']} → {ch['new']}")

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
    flat = {}
    stack = list(equipment_list)
    while stack:
        eq = stack.pop()
        flat[eq.full_name] = eq
        stack.extend(eq.children)
    return flat


def _parent_name(full_name: str) -> str | None:
    if "." not in full_name:
        return None
    return full_name.rsplit(".", 1)[0]


def _full_class_name(cls) -> str:
    return cls.name


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

        if eq_a.level != eq_b.level:
            result.equipment_level_changed.append(
                {"name": name, "old": eq_a.level, "new": eq_b.level}
            )

        parent_a = _parent_name(eq_a.full_name)
        parent_b = _parent_name(eq_b.full_name)
        if parent_a != parent_b:
            result.equipment_hierarchy_changed.append(
                {"name": name, "old": parent_a, "new": parent_b}
            )

        prop_changes = _diff_properties(
            {p.name: p for p in eq_a.properties},
            {p.name: p for p in eq_b.properties},
        )
        if any(prop_changes.values()):
            result.equipment_properties_changed.append(
                {"equipment": name, **prop_changes}
            )


def _diff_classes(model_a, model_b, result: DiffResult):
    cls_a = {_full_class_name(cls): cls for cls in model_a["classes"]}
    cls_b = {_full_class_name(cls): cls for cls in model_b["classes"]}

    names_a = set(cls_a)
    names_b = set(cls_b)

    result.classes_added = sorted(names_b - names_a)
    result.classes_removed = sorted(names_a - names_b)

    for name in sorted(names_a & names_b):
        a = cls_a[name]
        b = cls_b[name]

        chain_a = [c.name for c in a.inheritance_chain]
        chain_b = [c.name for c in b.inheritance_chain]
        if chain_a != chain_b:
            result.class_inheritance_changed.append(
                {"class": name, "old": chain_a, "new": chain_b}
            )

        if a.parent != b.parent:
            result.class_metadata_changed.append(
                {"class": name, "old": a.parent, "new": b.parent}
            )

        prop_changes = _diff_properties(
            {p.name: p for p in a.properties},
            {p.name: p for p in b.properties},
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

        if (
            a.value != b.value
            or a.unit_of_measure != b.unit_of_measure
            or getattr(a, "normalized_unit_of_measure", None)
            != getattr(b, "normalized_unit_of_measure", None)
            or getattr(a, "raw_unit_of_measure", None)
            != getattr(b, "raw_unit_of_measure", None)
            or getattr(a, "datatype", None) != getattr(b, "datatype", None)
            or getattr(a, "source", None) != getattr(b, "source", None)
        ):
            changed.append(
                {
                    "name": n,
                    "old": {
                        "value": a.value,
                        "uom": a.unit_of_measure,
                        "normalized_uom": getattr(
                            a, "normalized_unit_of_measure", None
                        ),
                        "raw_uom": getattr(a, "raw_unit_of_measure", None),
                        "datatype": getattr(a, "datatype", None),
                        "source": getattr(a, "source", None),
                    },
                    "new": {
                        "value": b.value,
                        "uom": b.unit_of_measure,
                        "normalized_uom": getattr(
                            b, "normalized_unit_of_measure", None
                        ),
                        "raw_uom": getattr(b, "raw_unit_of_measure", None),
                        "datatype": getattr(b, "datatype", None),
                        "source": getattr(b, "source", None),
                    },
                }
            )

    return {"added": added, "removed": removed, "changed": changed}
