from app.models.equipment import Equipment


def validate_model(model: dict) -> list[str]:
    warnings = []
    classes = {cls.name for cls in model["classes"]}

    for eq in model["equipment"]:
        _validate_equipment(eq, classes, warnings)
        _validate_uom(eq, warnings)  # NEW

    _validate_class_inheritance(model["classes"], warnings)
    _validate_class_uom(model["classes"], warnings)  # NEW

    return warnings


def _validate_equipment(eq: Equipment, classes: set, warnings: list):
    for cid in eq.class_ids:
        if cid not in classes:
            warnings.append(
                f"Equipment '{eq.full_name}' references unknown class '{cid}'"
            )

    if not eq.full_name:
        warnings.append(
            f"Equipment id='{eq.id}' has no full name (missing @name in hierarchy)"
        )

    for child in eq.children:
        _validate_equipment(child, classes, warnings)


def _validate_class_inheritance(classes, warnings: list):
    class_names = {cls.name for cls in classes}

    for cls in classes:
        if cls.parent and cls.parent not in class_names:
            warnings.append(
                f"Class '{cls.name}' references unknown parent '{cls.parent}'"
            )

    # detect circular inheritance
    def has_cycle(name, visited):
        if name in visited:
            return True
        lookup = {c.name: c for c in classes}
        current = lookup.get(name)
        if not current or not current.parent:
            return False
        return has_cycle(current.parent, visited | {name})

    for cls in classes:
        if has_cycle(cls.name, set()):
            warnings.append(f"Class '{cls.name}' has circular inheritance")


def _validate_uom(eq: Equipment, warnings: list):
    for prop in eq.properties:
        # Unknown or invalid UoM (normalizer already set uom_warning)
        if getattr(prop, "uom_warning", None):
            warnings.append(
                f"Equipment '{eq.full_name}' property '{prop.name}': {prop.uom_warning}"
            )

        # Missing canonical UoM but raw exists → invalid mapping
        if prop.raw_unit_of_measure and not prop.normalized_unit_of_measure:
            warnings.append(
                f"Equipment '{eq.full_name}' property '{prop.name}' has unresolved UoM '{prop.raw_unit_of_measure}'"
            )

    for child in eq.children:
        _validate_uom(child, warnings)


def _validate_class_uom(classes, warnings: list):
    for cls in classes:
        for prop in cls.properties:
            if getattr(prop, "uom_warning", None):
                warnings.append(
                    f"Class '{cls.name}' property '{prop.name}': {prop.uom_warning}"
                )

            if prop.raw_unit_of_measure and not prop.normalized_unit_of_measure:
                warnings.append(
                    f"Class '{cls.name}' property '{prop.name}' has unresolved UoM '{prop.raw_unit_of_measure}'"
                )
