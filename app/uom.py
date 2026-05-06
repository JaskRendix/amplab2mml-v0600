from dataclasses import dataclass


@dataclass(frozen=True)
class UoMConfig:
    alias_to_canonical: dict[str, str]
    allow_unknown: bool = True
    case_insensitive: bool = True
    strip_whitespace: bool = True


def build_uom_config(cfg: dict) -> UoMConfig:
    # expect in mapping.toml:
    # [uom.map]
    # "tonne" = ["t", "ton", "tons"]
    uom_section = cfg.get("uom", {})
    alias_map: dict[str, str] = {}

    for canonical, aliases in uom_section.get("map", {}).items():
        for a in aliases:
            key = a.strip().lower()
            alias_map[key] = canonical

    return UoMConfig(
        alias_to_canonical=alias_map,
        allow_unknown=uom_section.get("options", {}).get("allow_unknown", True),
        case_insensitive=uom_section.get("options", {}).get("case_insensitive", True),
        strip_whitespace=uom_section.get("options", {}).get("strip_whitespace", True),
    )


def normalize_uom(raw: str | None, cfg: UoMConfig) -> tuple[str | None, str | None]:
    if raw is None or raw == "":
        return None, None

    original = raw
    if cfg.strip_whitespace:
        raw = raw.strip()
    key = raw.lower() if cfg.case_insensitive else raw

    if key in cfg.alias_to_canonical:
        return cfg.alias_to_canonical[key], None

    if cfg.allow_unknown:
        return original, f"Unknown UoM '{original}' (kept as‑is)"

    return None, f"Invalid UoM '{original}' (no mapping found)"
