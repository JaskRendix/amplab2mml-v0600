import pytest
from lxml import etree

from app.builders.b2mml_builder import build_b2mml_xml
from app.diff import diff_models
from app.pipeline import run_pipeline_from_file
from app.validators import validate_model

NS = {"b": "http://www.mesa.org/xml/B2MML-V0600"}


def normalise(root):
    """Strip timestamps, whitespace, and comments."""
    for tag in ["CreationDateTime", "PublishedDate"]:
        for el in root.findall(f".//b:{tag}", NS):
            el.text = ""

    for el in root.iter():
        if el.text:
            el.text = el.text.strip()
        if el.tail:
            el.tail = el.tail.strip()

    for comment in root.xpath("//comment()"):
        comment.getparent().remove(comment)


def canonicalise(root):
    """Canonical XML for deterministic comparison."""
    from io import BytesIO

    buf = BytesIO()
    root.getroottree().write_c14n(buf)
    return buf.getvalue()


def test_output_matches_v0600_ground_truth():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")

    actual_xml = build_b2mml_xml(model, config=model["config"])
    actual = etree.fromstring(actual_xml.encode())

    expected = etree.parse("tests/data/sample_b2mml_expected.xml").getroot()

    normalise(actual)
    normalise(expected)

    assert canonicalise(actual) == canonicalise(expected)


def test_application_area_structure():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")
    xml = build_b2mml_xml(model, config=model["config"])
    doc = etree.fromstring(xml.encode())

    sender = doc.find(".//b:ApplicationArea/b:Sender", NS)
    receiver = doc.find(".//b:ApplicationArea/b:Receiver", NS)
    creation = doc.find(".//b:ApplicationArea/b:CreationDateTime", NS)

    assert sender is not None
    assert receiver is not None
    assert creation is not None


def test_equipment_level_is_hierarchy_scope_type():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")
    xml = build_b2mml_xml(model, config=model["config"])
    doc = etree.fromstring(xml.encode())

    el = doc.find(".//b:EquipmentLevel", NS)
    assert el is not None
    assert el.find("b:EquipmentID", NS) is not None
    assert el.find("b:EquipmentElementLevel", NS) is not None


@pytest.mark.parametrize(
    "datatype,value_tag",
    [
        ("int", "ValueInt"),
        ("float", "ValueFloat"),
        ("boolean", "ValueBoolean"),
        ("datetime", "ValueDateTime"),
        ("decimal", "ValueDecimal"),
        ("string", "ValueString"),
        ("unknown", "ValueString"),
    ],
)
def test_property_value_tag(datatype, value_tag, make_property):
    prop = make_property(datatype=datatype, value="42")

    from app.builders.b2mml_builder import build_property

    el = build_property("EquipmentProperty", prop, {})

    assert el.find(f".//b:{value_tag}", NS) is not None


def test_b2mml_output_is_deterministic():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")

    xml1 = build_b2mml_xml(model, config=model["config"])
    xml2 = build_b2mml_xml(model, config=model["config"])

    doc1 = etree.fromstring(xml1.encode())
    doc2 = etree.fromstring(xml2.encode())

    normalise(doc1)
    normalise(doc2)

    assert canonicalise(doc1) == canonicalise(doc2)


def test_nested_properties_supported(make_property):
    parent = make_property(name="Parent", datatype="string", value="A")
    child = make_property(name="Child", datatype="int", value="5")
    parent.children = [child]

    from app.builders.b2mml_builder import build_property

    el = build_property("EquipmentProperty", parent, {})

    assert el.find(".//b:EquipmentProperty/b:ID", NS).text == "Child"


def test_asset_mapping_serialization(make_asset_mapping):
    mapping = make_asset_mapping()

    from app.builders.b2mml_builder import build_asset_mapping

    el = build_asset_mapping(mapping)

    assert el.find("b:EquipmentID", NS) is not None
    assert el.find("b:PhysicalAssetID", NS) is not None


def test_class_inheritance_merging(make_model):
    model = make_model()

    # walk the whole equipment tree
    def _walk(eq_list):
        for e in eq_list:
            yield e
            yield from _walk(e.children)

    eq = next(
        e
        for e in _walk(model["equipment"])
        if any(p.name == "DriveType" for p in e.properties)
    )

    names = [p.name for p in eq.properties]
    assert "DriveType" in names
    assert "Manufacturer" in names


def test_validation_warnings():
    model = run_pipeline_from_file("tests/data/sample_ampla.xml")
    warnings = validate_model(model)

    assert isinstance(warnings, list)
    assert all(isinstance(w, str) for w in warnings)


def _walk(eq_list):
    for e in eq_list:
        yield e
        yield from _walk(e.children)


def test_diff_engine_detects_changes():
    model1 = run_pipeline_from_file("tests/data/sample_ampla.xml")
    model2 = run_pipeline_from_file("tests/data/sample_ampla.xml")

    # find first equipment with at least one property anywhere in the tree
    target = next(e for e in _walk(model2["equipment"]) if e.properties)

    # mutate model2
    target.properties.append(target.properties[0])

    diff = diff_models(model1, model2)
    assert diff  # non‑empty
