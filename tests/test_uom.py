import pytest

from app.uom import build_uom_config, normalize_uom


def make_cfg():
    return {
        "uom": {
            "map": {
                "tonne": ["t", "ton", "tons"],
                "metre": ["m", "meter", "metre"],
            },
            "options": {
                "allow_unknown": True,
                "case_insensitive": True,
                "strip_whitespace": True,
            },
        }
    }


def test_build_uom_config_maps_aliases():
    cfg = build_uom_config(make_cfg())
    assert cfg.alias_to_canonical["t"] == "tonne"
    assert cfg.alias_to_canonical["ton"] == "tonne"
    assert cfg.alias_to_canonical["tons"] == "tonne"
    assert cfg.alias_to_canonical["m"] == "metre"
    assert cfg.alias_to_canonical["meter"] == "metre"


def test_normalize_known_uom():
    cfg = build_uom_config(make_cfg())
    canon, warn = normalize_uom("t", cfg)
    assert canon == "tonne"
    assert warn is None


def test_normalize_known_uom_case_insensitive():
    cfg = build_uom_config(make_cfg())
    canon, warn = normalize_uom("  M  ", cfg)
    assert canon == "metre"
    assert warn is None


def test_normalize_unknown_uom_allowed():
    cfg = build_uom_config(make_cfg())
    canon, warn = normalize_uom("foo", cfg)
    assert canon == "foo"
    assert warn == "Unknown UoM 'foo' (kept as‑is)"


def test_normalize_unknown_uom_disallowed():
    cfg_dict = make_cfg()
    cfg_dict["uom"]["options"]["allow_unknown"] = False
    cfg = build_uom_config(cfg_dict)

    canon, warn = normalize_uom("foo", cfg)
    assert canon is None
    assert warn == "Invalid UoM 'foo' (no mapping found)"


def test_normalize_empty_or_none():
    cfg = build_uom_config(make_cfg())
    assert normalize_uom("", cfg) == (None, None)
    assert normalize_uom(None, cfg) == (None, None)
