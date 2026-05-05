import logging
from pathlib import Path
from typing import Any

import tomllib
from lxml import etree

from app.models.classes import EquipmentClass
from app.models.equipment import Equipment
from app.models.properties import ClassProperty, EquipmentProperty

logger = logging.getLogger(__name__)


class TransformationContext:
    def __init__(self, config: dict):
        self.config = config
        self.class_id_lookup: dict[str, str] = {}
        self.warnings: list[str] = []


class AmplaTransformer:
    def __init__(self, config_path: str = "config/mapping.toml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        """Load full v0600 config with safe defaults."""
        defaults = {
            "level_map": {},
            "hierarchy": {},
            "properties": {
                "strip_prefixes": [],
                "exclude": [],
                "rename": {},
                "required": [],
            },
            "datatypes": {"fallback": "string"},
            "uom_map": {},
            "metadata": {
                "version": "V0600",
                "namespace": "http://www.mesa.org/xml/B2MML-V0600",
            },
        }

        if Path(path).exists():
            try:
                with open(path, "rb") as f:
                    cfg = tomllib.load(f)
                    return defaults | cfg  # merge user config over defaults
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        logger.warning("Using default configuration.")
        return defaults

    def transform(self, root: etree._Element) -> dict[str, Any]:
        ctx = TransformationContext(self.config)

        ctx.class_id_lookup = self._build_class_id_lookup(root)

        classes = self._parse_classes(root)
        self._compute_class_inheritance(classes)

        equipment = self._parse_equipment(root, ctx)
        self._compute_full_names(equipment, None)
        self._merge_properties(equipment, classes)

        return {
            "equipment": equipment,
            "classes": classes,
            "warnings": ctx.warnings,
        }

    def _parse_classes(self, root: etree._Element) -> list[EquipmentClass]:
        classes: list[EquipmentClass] = []

        def walk(node: etree._Element, parent: str | None, depth: int):
            name = node.get("name")
            full = f"{parent}.{name}" if parent and name else name

            uom_map = self.config.get("uom_map", {})

            # Rule:
            # depth == 0 → container ONLY if it has children
            # depth == 0 AND no children → real class
            # depth >= 1 → real class
            is_real = (depth > 0) or (len(node.xpath("ClassDefinition")) == 0)

            if is_real and name:
                props = [
                    ClassProperty(
                        name=p.get("name"),
                        description=p.get("description"),
                        value=p.text,
                        datatype=self._translate_datatype(p.get("type")),
                        unit_of_measure=uom_map.get(p.get("uom"), p.get("uom")),
                    )
                    for p in node.xpath("PropertyDefinition")
                ]
                props.sort(key=lambda p: p.name)
                classes.append(
                    EquipmentClass(name=full, parent=parent, properties=props)
                )

            for child in node.xpath("ClassDefinition"):
                walk(child, full if is_real else None, depth + 1)

        for node in root.xpath("//ClassDefinition"):
            if node.getparent().tag != "ClassDefinition":
                walk(node, None, 0)

        return classes

    def _extract_classes(
        self, node: etree._Element, parent: str | None
    ) -> list[EquipmentClass]:
        name = node.get("name")
        full_name = f"{parent}.{name}" if parent else name

        uom_map = self.config.get("uom_map", {})

        props = [
            ClassProperty(
                name=p.get("name"),
                description=p.get("description"),
                value=p.text,
                datatype=self._translate_datatype(p.get("type")),
                unit_of_measure=uom_map.get(p.get("uom"), p.get("uom")),
            )
            for p in node.xpath("PropertyDefinition")
        ]

        cls = EquipmentClass(name=full_name, parent=parent, properties=props)
        result = [cls]

        for child in node.xpath("ClassDefinition"):
            result.extend(self._extract_classes(child, full_name))

        return result

    def _parse_equipment(
        self, root: etree._Element, ctx: TransformationContext
    ) -> list[Equipment]:
        return [
            eq
            for item in root.xpath("/Ampla/Item")
            if (eq := self._convert_item(item, ctx))
        ]

    def _convert_item(self, node, ctx, parent_level=None):
        item_type = node.get("type", "Unknown")
        level_map = self.config.get("level_map", {})
        level = level_map.get(item_type, "Other")

        if item_type not in level_map:
            ctx.warnings.append(
                f"Unmapped Ampla Type: '{item_type}' → defaulting to 'Other'"
            )

        # hierarchy validation unchanged...

        # FIX: warn on unknown classDefinitionId
        class_ids = []
        for a in node.xpath("ItemClassAssociation"):
            cid = a.get("classDefinitionId")
            resolved = ctx.class_id_lookup.get(cid)
            if resolved is None:
                ctx.warnings.append(f"Unknown classDefinitionId '{cid}'")
            else:
                class_ids.append(resolved)

        return Equipment(
            id=node.get("id"),
            name=node.get("name", ""),
            level=level,
            class_ids=class_ids,
            overrides={p.get("name"): p.text for p in node.xpath("Property")},
            children=[
                c
                for n in node.xpath("Item")
                if (c := self._convert_item(n, ctx, level))
            ],
        )

    def _merge_properties(
        self, equipment: list[Equipment], classes: list[EquipmentClass]
    ):
        class_lookup = {cls.name: cls for cls in classes}

        prop_cfg = self.config.get("properties", {})
        prefixes = prop_cfg.get("strip_prefixes", [])
        exclude = prop_cfg.get("exclude", [])
        rename = prop_cfg.get("rename", {})

        def clean_name(name: str) -> str:
            for pre in prefixes:
                if name.startswith(pre):
                    name = name[len(pre) :]
            return rename.get(name, name)

        def process(eq: Equipment):
            merged: dict[str, EquipmentProperty] = {}

            # Inherit class properties
            for class_name in eq.class_ids:
                if cls := class_lookup.get(class_name):
                    for ancestor in cls.inheritance_chain:
                        for p in ancestor.properties:
                            fname = clean_name(p.name)
                            if fname not in exclude:
                                merged[fname] = EquipmentProperty(
                                    name=fname,
                                    value=p.value,
                                    datatype=p.datatype,
                                    unit_of_measure=p.unit_of_measure,
                                )

            # Apply overrides
            for k, v in eq.overrides.items():
                fname = clean_name(k)
                if fname in exclude:
                    continue
                if fname in merged:
                    merged[fname].value = v
                else:
                    merged[fname] = EquipmentProperty(
                        name=fname, value=v, datatype="string"
                    )

            eq.properties = list(merged.values())
            eq.properties.sort(key=lambda p: p.name)

            for child in eq.children:
                process(child)

        for e in equipment:
            process(e)

    def _translate_datatype(self, dt: str | None) -> str:
        mapping = self.config.get("datatypes", {})
        return mapping.get(dt or "", mapping.get("fallback", "string"))

    def _build_class_id_lookup(self, root: etree._Element) -> dict[str, str]:
        lookup: dict[str, str] = {}

        def walk(node: etree._Element, parent: str | None, depth: int):
            name = node.get("name")
            full = f"{parent}.{name}" if parent and name else name

            has_children = bool(node.xpath("ClassDefinition"))
            is_real = (depth > 0) or (not has_children)

            if is_real and node.get("id") and full:
                lookup[node.get("id")] = full

            for child in node.xpath("ClassDefinition"):
                walk(child, full if is_real else None, depth + 1)

        for node in root.xpath("//ClassDefinition"):
            if node.getparent().tag != "ClassDefinition":
                walk(node, None, 0)

        return lookup

    def _compute_class_inheritance(self, classes: list[EquipmentClass]):
        lookup = {cls.name: cls for cls in classes}
        for cls in classes:
            chain = []
            curr = cls
            while curr:
                chain.append(curr)
                curr = lookup.get(curr.parent)
            cls.inheritance_chain = chain[::-1]

    def _compute_full_names(self, eq_list: list[Equipment], parent: str | None):
        for eq in eq_list:
            if eq.name:
                eq.full_name = f"{parent}.{eq.name}" if parent else eq.name
            else:
                # nameless node inherits parent's full_name
                eq.full_name = parent or ""
            self._compute_full_names(eq.children, eq.full_name)
