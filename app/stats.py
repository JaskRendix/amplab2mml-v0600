from dataclasses import dataclass, field
from typing import Any

from app.models.equipment import Equipment


@dataclass
class ModelStats:
    total_equipment: int = 0
    total_classes: int = 0
    total_properties: int = 0
    max_depth: int = 0
    warnings: list[str] = field(default_factory=list)
    uom_usage: dict[str, int] = field(default_factory=dict)
    uom_raw_usage: dict[str, int] = field(default_factory=dict)
    uom_unknown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_equipment": self.total_equipment,
            "total_classes": self.total_classes,
            "total_properties": self.total_properties,
            "max_depth": self.max_depth,
            "warnings": self.warnings,
            "uom": {
                "canonical": self.uom_usage,
                "raw": self.uom_raw_usage,
                "unknown": self.uom_unknown,
            },
        }

    def to_text(self) -> str:
        lines = [
            f"Equipment nodes : {self.total_equipment}",
            f"Classes         : {self.total_classes}",
            f"Properties      : {self.total_properties}",
            f"Max depth       : {self.max_depth}",
        ]

        lines.append("UoM usage:")
        if self.uom_usage:
            for u, c in sorted(self.uom_usage.items()):
                lines.append(f"  {u:12} : {c}")
        else:
            lines.append("  (none)")

        if self.uom_unknown:
            lines.append("Unknown UoM:")
            for u, c in sorted(self.uom_unknown.items()):
                lines.append(f"  {u:12} : {c}")

        if self.warnings:
            lines.append(f"Warnings        : {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"  ! {w}")
        else:
            lines.append("Warnings        : 0")

        return "\n".join(lines)


def compute_stats(model: dict) -> ModelStats:
    stats = ModelStats()
    stats.warnings = model.get("warnings", [])
    stats.total_classes = len(model["classes"])

    for eq in model["equipment"]:
        _walk(eq, depth=1, stats=stats)

    return stats


def _walk(eq: Equipment, depth: int, stats: ModelStats):
    stats.total_equipment += 1
    stats.total_properties += len(eq.properties)

    if depth > stats.max_depth:
        stats.max_depth = depth

    for p in eq.properties:
        raw = getattr(p, "raw_unit_of_measure", None)
        canon = getattr(p, "normalized_unit_of_measure", None)
        warn = getattr(p, "uom_warning", None)

        if raw:
            stats.uom_raw_usage[raw] = stats.uom_raw_usage.get(raw, 0) + 1

        if canon:
            stats.uom_usage[canon] = stats.uom_usage.get(canon, 0) + 1

        if warn:
            stats.uom_unknown[raw or ""] = stats.uom_unknown.get(raw or "", 0) + 1

    for child in eq.children:
        _walk(child, depth + 1, stats)
